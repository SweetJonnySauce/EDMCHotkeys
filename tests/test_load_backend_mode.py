from __future__ import annotations

from types import SimpleNamespace

import load as plugin_load


def test_resolve_backend_mode_prefers_env(monkeypatch) -> None:
    monkeypatch.setenv("EDMC_HOTKEYS_BACKEND_MODE", "wayland_gnome_bridge")
    monkeypatch.setitem(plugin_load.sys.modules, "config", SimpleNamespace(get_str=lambda _key: "x11"))

    assert plugin_load._resolve_backend_mode() == "wayland_gnome_bridge"


def test_resolve_backend_mode_invalid_env_falls_back_to_auto(monkeypatch) -> None:
    monkeypatch.setenv("EDMC_HOTKEYS_BACKEND_MODE", "invalid")

    assert plugin_load._resolve_backend_mode() == "auto"


def test_resolve_backend_mode_reads_config_when_env_unset(monkeypatch) -> None:
    monkeypatch.delenv("EDMC_HOTKEYS_BACKEND_MODE", raising=False)
    monkeypatch.setitem(
        plugin_load.sys.modules,
        "config",
        SimpleNamespace(get_str=lambda _key: "wayland_portal"),
    )

    assert plugin_load._resolve_backend_mode() == "wayland_portal"


def test_resolve_backend_mode_invalid_config_falls_back_to_auto(monkeypatch) -> None:
    monkeypatch.delenv("EDMC_HOTKEYS_BACKEND_MODE", raising=False)
    monkeypatch.setitem(plugin_load.sys.modules, "config", SimpleNamespace(get_str=lambda _key: "bad-mode"))

    assert plugin_load._resolve_backend_mode() == "auto"
