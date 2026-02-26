from __future__ import annotations

import logging

from edmc_hotkeys.backends.base import NullHotkeyBackend, backend_contract_issues
from edmc_hotkeys.backends.wayland import WaylandPortalBackend
from edmc_hotkeys.backends.windows import WindowsHotkeyBackend
from edmc_hotkeys.backends.x11 import X11HotkeyBackend


class _BadBackend:
    name = ""

    def availability(self):
        return None


class _FakeFallback:
    def availability(self):
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


def test_contract_issues_report_missing_members() -> None:
    issues = backend_contract_issues(_BadBackend())
    assert issues
    assert "Backend must expose a non-empty 'name' string" in issues
    assert any("capabilities" in issue for issue in issues)


def test_contract_issues_accept_supported_backends() -> None:
    backends = [
        NullHotkeyBackend(reason="disabled"),
        WaylandPortalBackend(logger=logging.getLogger("test.contract"), platform_name="linux"),
        X11HotkeyBackend(logger=logging.getLogger("test.contract"), platform_name="linux"),
        WindowsHotkeyBackend(
            logger=logging.getLogger("test.contract"),
            platform_name="win32",
            fallback=_FakeFallback(),
        ),
    ]
    for backend in backends:
        assert backend_contract_issues(backend) == []
