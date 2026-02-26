from __future__ import annotations

import logging
from pathlib import Path
import threading
import time

from edmc_hotkeys.backends.base import BackendAvailability, BackendCapabilities
from edmc_hotkeys.plugin import Binding, HotkeyPlugin
from edmc_hotkeys.registry import Action, InlineDispatchExecutor


class _FakeBackend:
    def __init__(self, *, register_ok: bool = True, supports_side_specific: bool = True) -> None:
        self.started = False
        self.registered: list[tuple[str, str]] = []
        self.unregistered: list[str] = []
        self.callback = None
        self.register_ok = register_ok
        self.supports_side_specific = supports_side_specific

    @property
    def name(self) -> str:
        return "fake-backend"

    def availability(self) -> BackendAvailability:
        return BackendAvailability(name=self.name, available=True)

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_side_specific_modifiers=self.supports_side_specific)

    def start(self, on_hotkey):
        self.callback = on_hotkey
        self.started = True
        return True

    def stop(self) -> None:
        self.started = False

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        self.registered.append((binding_id, hotkey))
        return self.register_ok

    def unregister_hotkey(self, binding_id: str) -> bool:
        self.unregistered.append(binding_id)
        return True


def test_invoke_binding_forwards_to_registry() -> None:
    received = []
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
        dispatch_executor=InlineDispatchExecutor(),
    )
    assert plugin.register_action(
        Action(
            id="overlay.toggle",
            label="Toggle Overlay",
            plugin="overlay",
            callback=lambda **kwargs: received.append(kwargs),
        )
    )
    binding = Binding(
        id="b1",
        hotkey="Ctrl+Shift+O",
        action_id="overlay.toggle",
        payload={"visible": False},
        enabled=True,
    )

    result = plugin.invoke_binding(binding, source="hotkey-test")

    assert result is True
    assert received == [
        {"payload": {"visible": False}, "source": "hotkey-test", "hotkey": "Ctrl+Shift+O"}
    ]


def test_invoke_binding_skips_disabled_binding() -> None:
    received = []
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
        dispatch_executor=InlineDispatchExecutor(),
    )
    assert plugin.register_action(
        Action(
            id="profile.switch",
            label="Switch Profile",
            plugin="hotkeys",
            callback=lambda **kwargs: received.append(kwargs),
        )
    )
    binding = Binding(
        id="b2",
        hotkey="Ctrl+Shift+P",
        action_id="profile.switch",
        enabled=False,
    )

    result = plugin.invoke_binding(binding)

    assert result is False
    assert received == []


def test_invoke_action_missing_action_returns_false(caplog) -> None:
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
        dispatch_executor=InlineDispatchExecutor(),
    )

    with caplog.at_level(logging.WARNING):
        result = plugin.invoke_action("overlay.toggle")

    assert result is False
    assert "was not found" in caplog.text


def test_plugin_pump_processes_background_main_dispatch() -> None:
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
    )
    received = []
    assert plugin.register_action(
        Action(
            id="overlay.toggle",
            label="Toggle Overlay",
            plugin="overlay",
            callback=lambda **kwargs: received.append(kwargs),
        )
    )

    result_holder = {}

    def run_on_worker() -> None:
        result_holder["result"] = plugin.invoke_action(
            "overlay.toggle",
            payload={"visible": True},
            source="worker-thread",
        )

    worker = threading.Thread(target=run_on_worker)
    worker.start()

    deadline = time.time() + 1.0
    while worker.is_alive() and time.time() < deadline:
        plugin.pump_main_thread_dispatch()
        time.sleep(0.01)
    worker.join(timeout=1.0)

    assert worker.is_alive() is False
    assert result_holder["result"] is True
    assert received == [{"payload": {"visible": True}, "source": "worker-thread"}]


def test_backend_hotkey_callback_invokes_registered_binding_action() -> None:
    backend = _FakeBackend()
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
        dispatch_executor=InlineDispatchExecutor(),
        hotkey_backend=backend,
    )
    received = []
    assert plugin.register_action(
        Action(
            id="overlay.toggle",
            label="Toggle Overlay",
            plugin="overlay",
            callback=lambda **kwargs: received.append(kwargs),
        )
    )
    binding = Binding(
        id="binding-1",
        hotkey="Ctrl+Shift+O",
        action_id="overlay.toggle",
        payload={"visible": False},
        enabled=True,
    )
    plugin.start()
    assert plugin.register_binding(binding) is True
    assert backend.registered == [("binding-1", "Ctrl+Shift+O")]

    assert backend.callback is not None
    backend.callback("binding-1")

    assert received == [
        {
            "payload": {"visible": False},
            "source": "backend:fake-backend",
            "hotkey": "Ctrl+Shift+O",
        }
    ]
    plugin.stop()


def test_replace_bindings_reconciles_backend_registrations() -> None:
    backend = _FakeBackend()
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
        dispatch_executor=InlineDispatchExecutor(),
        hotkey_backend=backend,
    )
    plugin.start()

    first = Binding(id="b1", hotkey="Ctrl+Shift+O", action_id="overlay.toggle", enabled=True)
    second = Binding(id="b2", hotkey="Ctrl+Shift+P", action_id="profile.switch", enabled=True)
    assert plugin.replace_bindings([first, second]) is True
    assert backend.registered[-2:] == [("b1", "Ctrl+Shift+O"), ("b2", "Ctrl+Shift+P")]

    updated = Binding(id="b2", hotkey="Ctrl+Alt+P", action_id="profile.switch", enabled=True)
    assert plugin.replace_bindings([updated]) is True
    assert "b1" in backend.unregistered
    assert "b2" in backend.unregistered
    assert backend.registered[-1] == ("b2", "Ctrl+Alt+P")
    plugin.stop()


def test_replace_bindings_skips_backend_unregistration_for_disabled_bindings() -> None:
    class _StrictBackend(_FakeBackend):
        def unregister_hotkey(self, binding_id: str) -> bool:
            return binding_id in {registered_id for registered_id, _hotkey in self.registered}

    backend = _StrictBackend()
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
        dispatch_executor=InlineDispatchExecutor(),
        hotkey_backend=backend,
    )
    plugin.start()

    disabled = Binding(id="disabled", hotkey="Ctrl+Shift+O", action_id="overlay.toggle", enabled=False)
    assert plugin.replace_bindings([disabled]) is True
    assert plugin.replace_bindings([]) is True
    plugin.stop()


def test_start_logs_selected_backend_with_capabilities(caplog) -> None:
    backend = _FakeBackend(supports_side_specific=False)
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
        dispatch_executor=InlineDispatchExecutor(),
        hotkey_backend=backend,
    )

    with caplog.at_level(logging.INFO):
        plugin.start()

    assert "Hotkey backend selected: name=fake-backend available=True supports_side_specific_modifiers=False" in caplog.text
    plugin.stop()


def test_register_binding_failure_log_includes_backend_name(caplog) -> None:
    backend = _FakeBackend(register_ok=False)
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.hotkeys"),
        dispatch_executor=InlineDispatchExecutor(),
        hotkey_backend=backend,
    )
    plugin.start()
    binding = Binding(id="b1", hotkey="Ctrl+Shift+O", action_id="overlay.toggle", enabled=True)

    with caplog.at_level(logging.WARNING):
        result = plugin.register_binding(binding)

    assert result is False
    assert "backend=fake-backend" in caplog.text
    plugin.stop()
