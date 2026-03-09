from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "virustotal_scan_source.py"
    spec = importlib.util.spec_from_file_location("virustotal_scan_source", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_analysis_id() -> None:
    module = _load_module()
    payload = {"data": {"id": "u-abc123"}}
    assert module._extract_analysis_id(payload) == "u-abc123"


def test_extract_status() -> None:
    module = _load_module()
    payload = {"data": {"attributes": {"status": "completed"}}}
    assert module._extract_status(payload) == "completed"


def test_extract_sha256_prefers_meta_file_info() -> None:
    module = _load_module()
    sha = "a" * 64
    payload = {"meta": {"file_info": {"sha256": sha}}}
    assert module._extract_sha256(payload) == sha


def test_write_output_contains_analysis_and_file_urls(tmp_path: Path) -> None:
    module = _load_module()
    out = tmp_path / "vtscan.txt"
    module._write_output(out, analysis_id="u-abc123", sha256="b" * 64)
    text = out.read_text(encoding="utf-8")
    assert "file-analysis/u-abc123" in text
    assert f"file/{'b' * 64}/detection" in text


def test_main_fails_without_api_key(monkeypatch, capsys) -> None:
    module = _load_module()
    monkeypatch.delenv("VT_API_KEY", raising=False)
    code = module.main(["--version", "v0.5.0-alpha-2", "--output", "dist/vtscan.txt"])
    captured = capsys.readouterr()
    assert code == 2
    assert "VirusTotal API key missing" in captured.err


def test_extract_analysis_id_requires_payload_shape() -> None:
    module = _load_module()
    with pytest.raises(module.VTScanError):
        module._extract_analysis_id({"data": {}})
