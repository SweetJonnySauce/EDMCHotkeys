from __future__ import annotations

import logging
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import load as plugin_load
from edmc_hotkeys.backends.base import BackendAvailability, BackendCapabilities
from edmc_hotkeys.plugin import Binding, HotkeyPlugin
from edmc_hotkeys.registry import Action, ThreadedWorkerDispatchExecutor
from edmc_hotkeys.settings_state import ValidationIssue


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

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_side_specific_modifiers=True)

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


class _FakeBindingsLookupPlugin:
    def list_actions(self) -> list[Action]:
        return [
            Action(
                id="test.on",
                label="On",
                plugin="EDMC-Hotkeys-Test",
                callback=lambda **_kwargs: None,
            ),
            Action(
                id="test.off",
                label="Off",
                plugin="EDMC-Hotkeys-Test",
                callback=lambda **_kwargs: None,
            ),
            Action(
                id="other.action",
                label="Other",
                plugin="OtherPlugin",
                callback=lambda **_kwargs: None,
            ),
        ]

    def list_bindings(self) -> list[Binding]:
        return [
            Binding(id="b-on", hotkey="Ctrl+Shift+F1", action_id="test.on", enabled=True, plugin="EDMC-Hotkeys-Test"),
            Binding(id="b-off", hotkey="Ctrl+Shift+F2", action_id="test.off", enabled=True, plugin="EDMC-Hotkeys-Test"),
            Binding(id="b-other", hotkey="Ctrl+Shift+F3", action_id="other.action", enabled=True, plugin="OtherPlugin"),
        ]


class _FakeAfterWidget:
    def __init__(self) -> None:
        self.after_calls: list[tuple[int, object]] = []
        self.cancelled_ids: list[str] = []

    def after(self, delay_ms: int, callback) -> str:
        after_id = f"after-{len(self.after_calls) + 1}"
        self.after_calls.append((delay_ms, callback))
        return after_id

    def after_cancel(self, after_id: str) -> None:
        self.cancelled_ids.append(after_id)


class _FakePanel:
    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []

    def get_rows(self):
        return []

    def set_validation_issues(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues


class _FakePrefsDialog:
    def __init__(self) -> None:
        self.apply_calls = 0

    def apply(self, *_args, **_kwargs):
        self.apply_calls += 1
        return "applied"


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


def test_list_bindings_filters_by_plugin_name(monkeypatch) -> None:
    fake_plugin = _FakeBindingsLookupPlugin()
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)

    bindings = plugin_load.list_bindings("EDMC-Hotkeys-Test")

    assert [binding.id for binding in bindings] == ["b-on", "b-off"]


def test_list_bindings_is_case_insensitive_and_requires_name(monkeypatch) -> None:
    fake_plugin = _FakeBindingsLookupPlugin()
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)

    matched = plugin_load.list_bindings("edmc-hotkeys-test")
    missing = plugin_load.list_bindings("")

    assert [binding.id for binding in matched] == ["b-on", "b-off"]
    assert missing == []


def test_dispatch_pump_scheduler_runs_and_can_be_stopped(monkeypatch) -> None:
    fake_plugin = _FakePumpPlugin()
    fake_widget = _FakeAfterWidget()
    monkeypatch.setattr(plugin_load, "_plugin", fake_plugin)
    monkeypatch.setattr(plugin_load, "_dispatch_pump_owner", None)
    monkeypatch.setattr(plugin_load, "_dispatch_pump_after_id", None)

    plugin_load._ensure_dispatch_pump_running(fake_widget)
    assert fake_widget.after_calls
    delay_ms, callback = fake_widget.after_calls[0]
    assert delay_ms == plugin_load._DISPATCH_PUMP_INTERVAL_MS

    callback()
    assert fake_plugin.pump_calls == 1
    assert len(fake_widget.after_calls) == 2

    plugin_load._stop_dispatch_pump()
    assert fake_widget.cancelled_ids == ["after-2"]


def test_dispatch_pump_scheduler_is_idempotent_while_scheduled(monkeypatch) -> None:
    fake_widget = _FakeAfterWidget()
    monkeypatch.setattr(plugin_load, "_dispatch_pump_owner", None)
    monkeypatch.setattr(plugin_load, "_dispatch_pump_after_id", None)

    plugin_load._ensure_dispatch_pump_running(fake_widget)
    plugin_load._ensure_dispatch_pump_running(fake_widget)

    assert len(fake_widget.after_calls) == 1
    plugin_load._stop_dispatch_pump()


def test_dispatch_pump_stop_without_scheduled_after_is_safe(monkeypatch) -> None:
    fake_widget = _FakeAfterWidget()
    monkeypatch.setattr(plugin_load, "_dispatch_pump_owner", fake_widget)
    monkeypatch.setattr(plugin_load, "_dispatch_pump_after_id", None)

    plugin_load._stop_dispatch_pump()

    assert fake_widget.cancelled_ids == []


def test_prefs_apply_guard_blocks_apply_when_validation_has_errors(monkeypatch) -> None:
    fake_dialog = _FakePrefsDialog()
    fake_prefs_module = SimpleNamespace(PreferencesDialog=_FakePrefsDialog)
    fake_panel = _FakePanel()
    error_issues = [ValidationIssue(level="error", row_id="row1", field="hotkey", message="invalid hotkey")]
    shown: list[list[ValidationIssue]] = []

    monkeypatch.setattr(plugin_load, "_plugin", object())
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_bindings_document", None)
    monkeypatch.setattr(plugin_load, "_prefs_apply_guard_installed", False)
    monkeypatch.setitem(sys.modules, "prefs", fake_prefs_module)
    monkeypatch.setattr(plugin_load, "_require_started", lambda: object())
    monkeypatch.setattr(plugin_load, "_settings_state_from_panel", lambda **_kwargs: SimpleNamespace(validate=lambda: error_issues))
    monkeypatch.setattr(plugin_load, "_show_validation_error_dialog", lambda issues: shown.append(list(issues)))

    plugin_load._install_prefs_apply_guard()
    result = fake_dialog.apply()

    assert getattr(fake_prefs_module.PreferencesDialog.apply, "_edmc_hotkeys_guard", False) is True
    assert result is None
    assert fake_dialog.apply_calls == 0
    assert fake_panel.issues == error_issues
    assert shown == [error_issues]


def test_prefs_apply_guard_allows_apply_when_validation_passes(monkeypatch) -> None:
    fake_dialog = _FakePrefsDialog()
    fake_prefs_module = SimpleNamespace(PreferencesDialog=_FakePrefsDialog)
    fake_panel = _FakePanel()

    monkeypatch.setattr(plugin_load, "_plugin", object())
    monkeypatch.setattr(plugin_load, "_settings_panel", fake_panel)
    monkeypatch.setattr(plugin_load, "_bindings_document", None)
    monkeypatch.setattr(plugin_load, "_prefs_apply_guard_installed", False)
    monkeypatch.setitem(sys.modules, "prefs", fake_prefs_module)
    monkeypatch.setattr(plugin_load, "_require_started", lambda: object())
    monkeypatch.setattr(plugin_load, "_settings_state_from_panel", lambda **_kwargs: SimpleNamespace(validate=lambda: []))

    plugin_load._install_prefs_apply_guard()
    result = fake_dialog.apply()

    assert result == "applied"
    assert fake_dialog.apply_calls == 1
    assert fake_panel.issues == []
