from __future__ import annotations

import logging
from pathlib import Path
import tempfile

from edmc_hotkeys.backends.base import (
    NullHotkeyBackend,
    as_batch_binding_backend,
    as_runtime_status_backend,
    backend_contract_issues,
)
from edmc_hotkeys.backends.gnome_bridge import GnomeWaylandBridgeBackend
from edmc_hotkeys.backends.wayland_keyd import WaylandKeydBackend
from edmc_hotkeys.backends.wayland import WaylandPortalBackend
from edmc_hotkeys.backends.windows import WindowsHotkeyBackend
from edmc_hotkeys.backends.x11 import X11HotkeyBackend


class _BadBackend:
    name = ""

    def availability(self):
        return None


class _FakeWindowsClient:
    def start(self, on_hotkey):
        del on_hotkey
        return True

    def stop(self) -> None:
        return None

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        del binding_id, hotkey
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        del binding_id
        return True


class _OptionalExtensionsBackend:
    name = "optional-extensions"

    def availability(self):
        return None

    def capabilities(self):
        return None

    def start(self, on_hotkey):
        del on_hotkey
        return True

    def stop(self) -> None:
        return None

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        del binding_id, hotkey
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        del binding_id
        return True

    def begin_binding_batch(self) -> None:
        return None

    def end_binding_batch(self) -> None:
        return None

    def runtime_status(self):
        return {"state": "ok"}


def test_contract_issues_report_missing_members() -> None:
    issues = backend_contract_issues(_BadBackend())
    assert issues
    assert "Backend must expose a non-empty 'name' string" in issues
    assert any("capabilities" in issue for issue in issues)


def test_contract_issues_accept_supported_backends() -> None:
    socket_path = tempfile.NamedTemporaryFile(prefix="edmc_hotkeys_contract_", delete=True).name
    plugin_dir = tempfile.TemporaryDirectory(prefix="edmc_hotkeys_contract_keyd_")
    backends = [
        NullHotkeyBackend(reason="disabled"),
        WaylandPortalBackend(logger=logging.getLogger("test.contract"), platform_name="linux"),
        WaylandKeydBackend(
            logger=logging.getLogger("test.contract"),
            platform_name="linux",
            environ={"WAYLAND_DISPLAY": "wayland-0"},
            plugin_dir=Path(plugin_dir.name),
            socket_path=socket_path + ".keyd.sock",
            token_file_path=socket_path + ".keyd.token",
        ),
        GnomeWaylandBridgeBackend(
            logger=logging.getLogger("test.contract"),
            platform_name="linux",
            environ={"WAYLAND_DISPLAY": "wayland-0", "EDMC_HOTKEYS_GNOME_BRIDGE": "1"},
            socket_path=socket_path,
        ),
        X11HotkeyBackend(logger=logging.getLogger("test.contract"), platform_name="linux"),
        WindowsHotkeyBackend(
            logger=logging.getLogger("test.contract"),
            platform_name="win32",
            client=_FakeWindowsClient(),
        ),
    ]
    for backend in backends:
        assert backend_contract_issues(backend) == []
    plugin_dir.cleanup()


def test_optional_backend_interfaces_are_discoverable() -> None:
    backend = _OptionalExtensionsBackend()
    batch_backend = as_batch_binding_backend(backend)
    status_backend = as_runtime_status_backend(backend)

    assert batch_backend is not None
    assert status_backend is not None
    assert status_backend.runtime_status()["state"] == "ok"


def test_optional_backend_interfaces_return_none_when_absent() -> None:
    backend = NullHotkeyBackend(reason="disabled")

    assert as_batch_binding_backend(backend) is None
    assert as_runtime_status_backend(backend) is None
