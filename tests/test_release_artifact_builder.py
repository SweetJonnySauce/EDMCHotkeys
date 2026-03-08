from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


def _load_builder_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "scripts" / "build_release_artifact.py"
    spec = importlib.util.spec_from_file_location("build_release_artifact", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _seed_base_plugin_tree(root: Path) -> None:
    (root / "load.py").write_text("# plugin entrypoint\n", encoding="utf-8")
    (root / "config.defaults.ini").write_text("[backend]\nmode = auto\n", encoding="utf-8")
    package_dir = root / "edmc_hotkeys"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")


def test_validate_version_patterns() -> None:
    module = _load_builder_module()

    assert module.validate_version("v0.1.0")
    assert module.validate_version("v2.3.4-rc.1")
    assert not module.validate_version("0.1.0")
    assert not module.validate_version("v1.0")
    assert not module.validate_version("v1.2.3-beta.1")


def test_variant_matrix_uses_new_wayland_artifact_names() -> None:
    module = _load_builder_module()
    assert set(module.VARIANT_SPECS.keys()) == {"linux-x11", "linux-wayland", "windows"}


def test_verify_tree_rejects_forbidden_path_for_wayland(tmp_path: Path) -> None:
    module = _load_builder_module()
    spec = module.VARIANT_SPECS["linux-wayland"]
    root = tmp_path / "EDMCHotkeys"
    root.mkdir(parents=True, exist_ok=True)
    _seed_base_plugin_tree(root)
    scripts_dir = root / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "keyd_send.py").write_text("", encoding="utf-8")
    (scripts_dir / "export_keyd_bindings.py").write_text("", encoding="utf-8")
    (scripts_dir / "install_keyd_integration.sh").write_text("", encoding="utf-8")
    (scripts_dir / "verify_keyd_integration.sh").write_text("", encoding="utf-8")
    (scripts_dir / "uninstall_keyd_integration.sh").write_text("", encoding="utf-8")
    (root / "dbus_next").mkdir()

    with pytest.raises(module.ReleaseArtifactError):
        module.verify_tree(root, spec)


def test_verify_tree_rejects_global_excluded_paths(tmp_path: Path) -> None:
    module = _load_builder_module()
    spec = module.VARIANT_SPECS["linux-x11"]
    root = tmp_path / "EDMCHotkeys"
    root.mkdir(parents=True, exist_ok=True)
    _seed_base_plugin_tree(root)
    (root / "Xlib").mkdir()
    (root / "six.py").write_text("", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "RELEASE_NOTES.md").write_text("notes", encoding="utf-8")

    with pytest.raises(module.ReleaseArtifactError):
        module.verify_tree(root, spec)


def test_verify_tree_rejects_forbidden_path_for_windows(tmp_path: Path) -> None:
    module = _load_builder_module()
    spec = module.VARIANT_SPECS["windows"]
    root = tmp_path / "EDMCHotkeys"
    root.mkdir(parents=True, exist_ok=True)
    _seed_base_plugin_tree(root)
    (root / "Xlib").mkdir()

    with pytest.raises(module.ReleaseArtifactError):
        module.verify_tree(root, spec)


def test_verify_tree_requires_keyd_scripts_for_linux_wayland(tmp_path: Path) -> None:
    module = _load_builder_module()
    spec = module.VARIANT_SPECS["linux-wayland"]
    root = tmp_path / "EDMCHotkeys"
    root.mkdir(parents=True, exist_ok=True)
    _seed_base_plugin_tree(root)
    (root / "dbus_next").mkdir()

    scripts_dir = root / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "keyd_send.py").write_text("", encoding="utf-8")
    (scripts_dir / "export_keyd_bindings.py").write_text("", encoding="utf-8")

    with pytest.raises(module.ReleaseArtifactError):
        module.verify_tree(root, spec)


def test_generate_variant_config_defaults_filters_keyd_section(tmp_path: Path) -> None:
    module = _load_builder_module()
    root = tmp_path / "EDMCHotkeys"
    root.mkdir(parents=True, exist_ok=True)
    (root / "config_template.ini").write_text(
        "[backend]\nmode = auto\n\n[keyd]\ngenerated_path = keyd/runtime/keyd.generated.conf\n",
        encoding="utf-8",
    )
    module._generate_variant_config_defaults(root, module.VARIANT_SPECS["windows"])
    text = (root / "config.defaults.ini").read_text(encoding="utf-8")
    assert "mode = auto" in text
    assert "[keyd]" not in text
