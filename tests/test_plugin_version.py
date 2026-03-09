from __future__ import annotations

from pathlib import Path

from edmc_hotkeys import PLUGIN_TAG_VERSION, PLUGIN_VERSION, __version__
from edmc_hotkeys.semver import parse_semver


def test_plugin_runtime_version_is_semver() -> None:
    parsed = parse_semver(PLUGIN_VERSION, allow_v_prefix=False)
    assert parsed.to_string(v_prefix=False) == PLUGIN_VERSION
    assert __version__ == PLUGIN_VERSION
    assert PLUGIN_TAG_VERSION == f"v{PLUGIN_VERSION}"


def test_version_file_exists_and_matches_runtime_version() -> None:
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    assert version_file.exists()
    assert version_file.read_text(encoding="utf-8").strip() == PLUGIN_VERSION
