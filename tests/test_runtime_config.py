from __future__ import annotations

from pathlib import Path

from edmc_hotkeys.runtime_config import USER_CONFIG_PATH, load_runtime_config


def _write_defaults(path: Path, *, mode: str = "auto") -> None:
    path.write_text(
        "[backend]\n"
        f"mode = {mode}\n"
        "\n"
        "[keyd]\n"
        "generated_path = keyd/runtime/keyd.generated.conf\n"
        "state_path = keyd/runtime/export_state.json\n"
        "socket_path = keyd/runtime/keyd.sock\n"
        "token_file = keyd/runtime/sender.token\n"
        "apply_target_path = /etc/keyd/edmchotkeys.conf\n"
        "command_template = python3 {plugin_dir}/scripts/keyd_send.py --socket {socket_path} --binding-id {binding_id} --token-file {token_file}\n",
        encoding="utf-8",
    )


def test_load_runtime_config_creates_user_config_from_defaults(tmp_path: Path) -> None:
    defaults = tmp_path / "config.defaults.ini"
    _write_defaults(defaults, mode="wayland_portal")
    config, sources = load_runtime_config(plugin_dir=tmp_path, environ={})
    assert config.backend_mode == "wayland_portal"
    assert (tmp_path / USER_CONFIG_PATH).exists()
    assert sources["backend_mode"] in {"config.ini", "config.defaults.ini"}


def test_load_runtime_config_precedence_env_over_user_and_defaults(tmp_path: Path) -> None:
    _write_defaults(tmp_path / "config.defaults.ini", mode="wayland_portal")
    (tmp_path / "config.ini").write_text("[backend]\nmode = wayland_gnome_bridge\n", encoding="utf-8")
    config, sources = load_runtime_config(
        plugin_dir=tmp_path,
        environ={"EDMC_HOTKEYS_BACKEND_MODE": "wayland_keyd"},
    )
    assert config.backend_mode == "wayland_keyd"
    assert sources["backend_mode"] == "env"
