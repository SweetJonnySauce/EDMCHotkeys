from __future__ import annotations

from types import SimpleNamespace

from edmc_hotkeys.runtime_config import RuntimeConfig
import load as plugin_load


def test_resolve_backend_mode_prefers_env(monkeypatch) -> None:
    monkeypatch.setenv("EDMC_HOTKEYS_BACKEND_MODE", "wayland_keyd")
    monkeypatch.setitem(plugin_load.sys.modules, "config", SimpleNamespace(get_str=lambda _key: "x11"))

    assert plugin_load._resolve_backend_mode() == "wayland_keyd"


def test_resolve_backend_mode_invalid_env_falls_back_to_auto(monkeypatch) -> None:
    monkeypatch.setenv("EDMC_HOTKEYS_BACKEND_MODE", "invalid")

    assert plugin_load._resolve_backend_mode() == "auto"


def test_resolve_backend_mode_removed_env_mode_falls_back_to_auto(monkeypatch, caplog) -> None:
    monkeypatch.setenv("EDMC_HOTKEYS_BACKEND_MODE", "wayland_" + "portal")

    with caplog.at_level("WARNING"):
        assert plugin_load._resolve_backend_mode() == "auto"

    assert "falling back to auto" in caplog.text


def test_resolve_backend_mode_reads_config_when_env_unset(monkeypatch) -> None:
    monkeypatch.delenv("EDMC_HOTKEYS_BACKEND_MODE", raising=False)
    monkeypatch.setitem(
        plugin_load.sys.modules,
        "config",
        SimpleNamespace(get_str=lambda _key: "x11"),
    )

    assert plugin_load._resolve_backend_mode() == "x11"


def test_resolve_backend_mode_accepts_wayland_keyd_from_config(monkeypatch) -> None:
    monkeypatch.delenv("EDMC_HOTKEYS_BACKEND_MODE", raising=False)
    monkeypatch.setitem(
        plugin_load.sys.modules,
        "config",
        SimpleNamespace(get_str=lambda _key: "wayland_keyd"),
    )
    assert plugin_load._resolve_backend_mode() == "wayland_keyd"


def test_resolve_backend_mode_invalid_config_falls_back_to_auto(monkeypatch) -> None:
    monkeypatch.delenv("EDMC_HOTKEYS_BACKEND_MODE", raising=False)
    monkeypatch.setitem(plugin_load.sys.modules, "config", SimpleNamespace(get_str=lambda _key: "bad-mode"))

    assert plugin_load._resolve_backend_mode() == "auto"


def test_resolve_backend_mode_removed_config_mode_falls_back_to_auto(monkeypatch, caplog) -> None:
    monkeypatch.delenv("EDMC_HOTKEYS_BACKEND_MODE", raising=False)
    monkeypatch.setitem(
        plugin_load.sys.modules,
        "config",
        SimpleNamespace(get_str=lambda _key: "wayland_" + "gnome_bridge"),
    )

    with caplog.at_level("WARNING"):
        assert plugin_load._resolve_backend_mode() == "auto"

    assert "falling back to auto" in caplog.text


def test_apply_runtime_keyd_environment_sets_backend_paths(monkeypatch) -> None:
    monkeypatch.delenv("EDMC_HOTKEYS_KEYD_SOCKET_PATH", raising=False)
    monkeypatch.delenv("EDMC_HOTKEYS_KEYD_TOKEN_FILE", raising=False)
    config = RuntimeConfig(
        keyd_socket_path="/tmp/edmchotkeys/keyd.sock",
        keyd_token_file="/tmp/edmchotkeys/sender.token",
    )

    plugin_load._apply_runtime_keyd_environment(config)

    assert plugin_load.os.environ["EDMC_HOTKEYS_KEYD_SOCKET_PATH"] == "/tmp/edmchotkeys/keyd.sock"
    assert plugin_load.os.environ["EDMC_HOTKEYS_KEYD_TOKEN_FILE"] == "/tmp/edmchotkeys/sender.token"
