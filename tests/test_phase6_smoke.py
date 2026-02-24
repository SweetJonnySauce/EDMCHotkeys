from __future__ import annotations

import logging
from pathlib import Path
import threading

import load as plugin_load
from edmc_hotkeys.backends.base import BackendAvailability
from edmc_hotkeys.plugin import Binding, HotkeyPlugin
from edmc_hotkeys.registry import Action, ThreadedWorkerDispatchExecutor


class _FakeBackend:
    def __init__(self) -> None:
        self.started = False
        self.callback = None
        self.registered: list[tuple[str, str]] = []

    @property
    def name(self) -> str:
        return "fake-backend"

    def availability(self) -> BackendAvailability:
        return BackendAvailability(name=self.name, available=True)

    def start(self, on_hotkey):
        self.callback = on_hotkey
        self.started = True
        return True

    def stop(self) -> None:
        self.started = False

    def register_hotkey(self, binding_id: str, hotkey: str) -> bool:
        self.registered.append((binding_id, hotkey))
        return True

    def unregister_hotkey(self, binding_id: str) -> bool:
        del binding_id
        return True


class _FakePumpPlugin:
    def __init__(self) -> None:
        self.pump_calls = 0

    def pump_main_thread_dispatch(self, max_items=None) -> int:
        del max_items
        self.pump_calls += 1
        return 1


def test_worker_dispatch_smoke_runs_callback_off_main_thread() -> None:
    main_thread_id = threading.get_ident()
    callback_thread_ids: list[int] = []
    done = threading.Event()

    def _worker_action(**_kwargs) -> None:
        callback_thread_ids.append(threading.get_ident())
        done.set()

    plugin = plugin_load.HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.phase6.dispatch"),
        dispatch_executor=ThreadedWorkerDispatchExecutor(),
        hotkey_backend=_FakeBackend(),
    )
    assert plugin.register_action(
        Action(
            id="phase6.worker",
            label="Phase 6 Worker",
            plugin="edmc_hotkeys",
            thread_policy="worker",
            callback=_worker_action,
        )
    )

    assert plugin.invoke_action("phase6.worker", payload={"ok": True}, source="phase6") is True
    assert done.wait(timeout=1.0) is True
    assert callback_thread_ids
    assert callback_thread_ids[0] != main_thread_id


def test_backend_smoke_start_replays_existing_enabled_bindings() -> None:
    backend = _FakeBackend()
    plugin = HotkeyPlugin(
        plugin_dir=Path("/tmp/edmc_hotkeys"),
        logger=logging.getLogger("test.phase6.backends"),
        hotkey_backend=backend,
    )
    assert plugin.register_binding(
        Binding(id="enabled", hotkey="Ctrl+Shift+O", action_id="overlay.toggle", enabled=True)
    )
    assert plugin.register_binding(
        Binding(id="disabled", hotkey="Ctrl+Shift+P", action_id="profile.switch", enabled=False)
    )

    plugin.start()

    assert backend.started is True
    assert backend.registered == [("enabled", "Ctrl+Shift+O")]
    plugin.stop()


def test_hook_smoke_journal_and_dashboard_pump_dispatch_queue(monkeypatch) -> None:
    fake_plugin = _FakePumpPlugin()
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)

    result = plugin_load.journal_entry(
        cmdr="cmdr",
        is_beta=False,
        system="Sol",
        station="Galileo",
        entry={},
        state={},
    )
    plugin_load.dashboard_entry(cmdr="cmdr", is_beta=False, entry={})

    assert result is None
    assert fake_plugin.pump_calls == 2
