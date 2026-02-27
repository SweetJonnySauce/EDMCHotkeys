from __future__ import annotations

import json
from pathlib import Path


def test_companion_extension_layout_has_required_files() -> None:
    root = Path(__file__).resolve().parents[1]
    ext_dir = root / "companion" / "gnome-extension" / "edmc-hotkeys@edcd"

    assert (ext_dir / "metadata.json").exists()
    assert (ext_dir / "extension.js").exists()
    assert (ext_dir / "helper_bridge.js").exists()
    assert (ext_dir / "bindings.sample.json").exists()


def test_companion_metadata_has_uuid_and_shell_versions() -> None:
    root = Path(__file__).resolve().parents[1]
    metadata_path = root / "companion" / "gnome-extension" / "edmc-hotkeys@edcd" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["uuid"] == "edmc-hotkeys@edcd"
    assert isinstance(metadata.get("shell-version"), list)
    assert metadata["shell-version"]


def test_companion_install_scripts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    scripts_dir = root / "scripts"

    assert (scripts_dir / "install_gnome_bridge_companion.sh").exists()
    assert (scripts_dir / "uninstall_gnome_bridge_companion.sh").exists()
    assert (scripts_dir / "verify_gnome_bridge_companion.sh").exists()
    assert (scripts_dir / "package_gnome_bridge_companion.sh").exists()
    assert (scripts_dir / "export_companion_bindings.py").exists()
