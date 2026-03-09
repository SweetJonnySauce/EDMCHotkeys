from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "extract_release_notes.py"
    spec = importlib.util.spec_from_file_location("extract_release_notes", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_version_section_rewrites_header_to_tag() -> None:
    module = _load_module()
    text = """# EDMCHotkeys Release Notes

## v0.5.0-alpha-1 - Relaxed tagging requirements
- Added support for broader prerelease tags.

## v0.4.9
- Previous release.
"""
    result = module.extract_version_section(text, "v0.5.0-alpha-1")
    assert result.startswith("## v0.5.0-alpha-1\n")
    assert "- Added support for broader prerelease tags." in result
    assert "v0.4.9" not in result


def test_extract_version_section_supports_plain_header() -> None:
    module = _load_module()
    text = """## v0.5.0-beta-1
- Beta release notes.

## v0.5.0-alpha-1
- Alpha release notes.
"""
    result = module.extract_version_section(text, "v0.5.0-beta-1")
    assert result == "## v0.5.0-beta-1\n- Beta release notes.\n"


def test_extract_version_section_matches_base_header_for_prerelease_tag() -> None:
    module = _load_module()
    text = """## v0.5.0 - Consolidated backends
- Removed legacy Wayland variants.

## v0.4.9
- Previous release.
"""
    result = module.extract_version_section(text, "v0.5.0-alpha-1")
    assert result == "## v0.5.0-alpha-1\n- Removed legacy Wayland variants.\n"


def test_extract_version_section_raises_when_missing() -> None:
    module = _load_module()
    with pytest.raises(module.ReleaseNotesError):
        module.extract_version_section("## v0.5.0\n- Notes\n", "v0.5.1")
