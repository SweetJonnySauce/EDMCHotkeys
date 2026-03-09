#!/usr/bin/env python3
"""Extract one version section from RELEASE_NOTES.md."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edmc_hotkeys.semver import SemVerError, parse_semver


LEVEL2_HEADER = re.compile(r"^##\s+(?P<title>.+?)\s*$")


class ReleaseNotesError(RuntimeError):
    """Raised when a release-notes section cannot be extracted."""


def _base_version(version: str) -> str:
    try:
        semver = parse_semver(version, allow_v_prefix=True, require_v_prefix=True)
    except SemVerError:
        raise ReleaseNotesError(f"invalid version format: {version}")
    return semver.to_string(v_prefix=True, include_build=False).split("-", 1)[0]


def _is_full_version_header(title: str, version: str) -> bool:
    if title == version:
        return True
    return title.startswith(f"{version} - ")


def _is_base_version_header(title: str, base_version: str) -> bool:
    if title == base_version:
        return True
    return title.startswith(f"{base_version} - ")


def extract_version_section(text: str, version: str) -> str:
    lines = text.splitlines()
    base_version = _base_version(version)
    start: int | None = None
    end: int | None = None
    fallback_start: int | None = None

    for i, line in enumerate(lines):
        match = LEVEL2_HEADER.match(line)
        if not match:
            continue
        title = match.group("title")
        if start is None and _is_full_version_header(title, version):
            start = i
            continue
        if start is None and fallback_start is None and _is_base_version_header(title, base_version):
            fallback_start = i
            continue
        if start is not None:
            end = i
            break

    if start is None:
        start = fallback_start
        if start is not None:
            for i in range(start + 1, len(lines)):
                if LEVEL2_HEADER.match(lines[i]):
                    end = i
                    break

    if start is None:
        raise ReleaseNotesError(f"no release notes section found for {version}")
    if end is None:
        end = len(lines)

    section_lines = lines[start:end]
    section_lines[0] = f"## {version}"
    while section_lines and not section_lines[-1].strip():
        section_lines.pop()

    if not section_lines:
        raise ReleaseNotesError(f"empty release notes section for {version}")
    return "\n".join(section_lines) + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to RELEASE_NOTES.md")
    parser.add_argument("--version", required=True, help="Version tag, e.g. v0.5.0-alpha-1")
    parser.add_argument("--output", required=True, help="Output markdown file path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    input_path = Path(args.input)
    output_path = Path(args.output)

    try:
        text = input_path.read_text(encoding="utf-8")
        section = extract_version_section(text, args.version.strip())
    except (OSError, ReleaseNotesError) as exc:
        print(f"release notes extraction failed: {exc}", file=sys.stderr)
        return 1

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(section, encoding="utf-8")
    except OSError as exc:
        print(f"release notes write failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
