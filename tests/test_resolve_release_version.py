from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "resolve_release_version.py"
    spec = importlib.util.spec_from_file_location("resolve_release_version", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_main_outputs_expected_fields_for_prerelease(capsys) -> None:
    module = _load_module()
    code = module.main(["--version", "v0.5.0-alpha-1"])
    captured = capsys.readouterr()

    assert code == 0
    assert "version=v0.5.0-alpha-1" in captured.out
    assert "runtime_version=0.5.0-alpha-1" in captured.out
    assert "base_version=v0.5.0" in captured.out
    assert "prerelease=true" in captured.out


def test_main_rejects_stable_when_prerelease_is_required(capsys) -> None:
    module = _load_module()
    code = module.main(["--version", "v0.5.0", "--require-prerelease"])
    captured = capsys.readouterr()

    assert code == 1
    assert "version must be a prerelease" in captured.err
