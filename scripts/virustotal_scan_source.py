#!/usr/bin/env python3
"""Submit source archive to VirusTotal and write scan URLs to a text file."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


API_BASE = "https://www.virustotal.com/api/v3"
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_POLL_INTERVAL_SECONDS = 10
SMALL_FILE_LIMIT_BYTES = 32 * 1024 * 1024


class VTScanError(RuntimeError):
    """Raised when VirusTotal scanning fails."""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release version/tag (used in source archive filename).")
    parser.add_argument("--output", required=True, help="Path for vtscan output text file.")
    parser.add_argument("--api-key-env", default="VT_API_KEY", help="Environment variable holding VirusTotal API key.")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--poll-interval-seconds", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS)
    return parser.parse_args(argv)


def _run_json_command(cmd: list[str]) -> dict[str, object]:
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise VTScanError(
            "Command failed: "
            + " ".join(cmd)
            + f"\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise VTScanError(f"Invalid JSON response from command {' '.join(cmd)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise VTScanError(f"Unexpected JSON payload type from command {' '.join(cmd)}")
    return payload


def _extract_analysis_id(payload: dict[str, object]) -> str:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise VTScanError("VirusTotal response missing 'data' object")
    analysis_id = data.get("id")
    if not isinstance(analysis_id, str) or not analysis_id.strip():
        raise VTScanError("VirusTotal response missing analysis id")
    return analysis_id.strip()


def _extract_upload_url(payload: dict[str, object]) -> str:
    data = payload.get("data")
    if not isinstance(data, str) or not data.strip():
        raise VTScanError("VirusTotal upload URL response missing data URL")
    return data.strip()


def _extract_status(payload: dict[str, object]) -> str:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise VTScanError("VirusTotal analysis response missing data object")
    attrs = data.get("attributes")
    if not isinstance(attrs, dict):
        raise VTScanError("VirusTotal analysis response missing attributes object")
    status = attrs.get("status")
    if not isinstance(status, str) or not status.strip():
        raise VTScanError("VirusTotal analysis response missing status")
    return status.strip()


def _extract_sha256(payload: dict[str, object]) -> str | None:
    meta = payload.get("meta")
    if isinstance(meta, dict):
        file_info = meta.get("file_info")
        if isinstance(file_info, dict):
            sha256 = file_info.get("sha256")
            if isinstance(sha256, str) and sha256.strip():
                return sha256.strip()
    return None


def _build_source_archive(version: str) -> Path:
    fd, tmp_path = tempfile.mkstemp(prefix=f"EDMCHotkeys-source-{version}-", suffix=".tar.gz")
    os.close(fd)
    archive_path = Path(tmp_path)
    cmd = ["git", "archive", "--format=tar.gz", "--output", str(archive_path), "HEAD"]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise VTScanError(
            "Failed to create source archive with git archive"
            + f"\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return archive_path


def _request_upload_url(api_key: str) -> str:
    payload = _run_json_command(
        [
            "curl",
            "--silent",
            "--show-error",
            "--fail",
            "--request",
            "GET",
            "--header",
            f"x-apikey: {api_key}",
            f"{API_BASE}/files/upload_url",
        ]
    )
    return _extract_upload_url(payload)


def _submit_file(api_key: str, archive_path: Path) -> str:
    upload_endpoint = f"{API_BASE}/files"
    if archive_path.stat().st_size > SMALL_FILE_LIMIT_BYTES:
        upload_endpoint = _request_upload_url(api_key)

    payload = _run_json_command(
        [
            "curl",
            "--silent",
            "--show-error",
            "--fail",
            "--request",
            "POST",
            "--header",
            f"x-apikey: {api_key}",
            "--form",
            f"file=@{archive_path}",
            upload_endpoint,
        ]
    )
    return _extract_analysis_id(payload)


def _wait_for_completion(api_key: str, analysis_id: str, timeout_seconds: int, poll_interval_seconds: int) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        payload = _run_json_command(
            [
                "curl",
                "--silent",
                "--show-error",
                "--fail",
                "--request",
                "GET",
                "--header",
                f"x-apikey: {api_key}",
                f"{API_BASE}/analyses/{analysis_id}",
            ]
        )
        status = _extract_status(payload)
        if status == "completed":
            return payload
        if status not in {"queued", "in-progress"}:
            raise VTScanError(f"VirusTotal analysis entered unexpected status '{status}'")
        if time.monotonic() >= deadline:
            raise VTScanError("Timed out waiting for VirusTotal analysis completion")
        time.sleep(poll_interval_seconds)


def _write_output(output_path: Path, *, analysis_id: str, sha256: str | None) -> None:
    analysis_url = f"https://www.virustotal.com/gui/file-analysis/{analysis_id}"
    file_url = f"https://www.virustotal.com/gui/file/{sha256}/detection" if sha256 else ""
    lines = [f"VirusTotal analysis URL: {analysis_url}"]
    if file_url:
        lines.append(f"VirusTotal file report URL: {file_url}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        print(f"VirusTotal API key missing. Set env var {args.api_key_env}.", file=sys.stderr)
        return 2

    archive_path: Path | None = None
    try:
        archive_path = _build_source_archive(args.version)
        analysis_id = _submit_file(api_key, archive_path)
        result_payload = _wait_for_completion(
            api_key=api_key,
            analysis_id=analysis_id,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
        )
        sha256 = _extract_sha256(result_payload)
        _write_output(Path(args.output), analysis_id=analysis_id, sha256=sha256)
    except VTScanError as exc:
        print(f"VirusTotal source scan failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if archive_path is not None:
            try:
                archive_path.unlink(missing_ok=True)
            except OSError:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
