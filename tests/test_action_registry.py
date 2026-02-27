from __future__ import annotations

import logging
import threading
import time

from edmc_hotkeys.registry import (
    ACTION_CARDINALITY_MULTI,
    ACTION_CARDINALITY_SINGLE,
    Action,
    ActionRegistry,
    QueuedMainThreadDispatchExecutor,
)


class RecordingDispatchExecutor:
    def __init__(self) -> None:
        self.main_calls = 0
        self.worker_calls = 0

    def run_main(self, callback):
        self.main_calls += 1
        return callback()

    def run_worker(self, callback):
        self.worker_calls += 1
        return callback()


def test_register_action_rejects_duplicate_id() -> None:
    registry = ActionRegistry()
    action = Action(
        id="plugin.toggle",
        label="Toggle",
        plugin="plugin",
        callback=lambda **_: None,
    )

    assert registry.register_action(action) is True
    assert registry.register_action(action) is False
    assert len(registry.list_actions()) == 1


def test_register_action_rejects_invalid_thread_policy() -> None:
    registry = ActionRegistry()
    action = Action(
        id="plugin.bad",
        label="Bad",
        plugin="plugin",
        callback=lambda **_: None,
        thread_policy="unsupported",
    )

    assert registry.register_action(action) is False
    assert registry.list_actions() == []


def test_register_action_defaults_cardinality_to_single() -> None:
    registry = ActionRegistry()
    action = Action(
        id="plugin.default-cardinality",
        label="DefaultCardinality",
        plugin="plugin",
        callback=lambda **_: None,
    )

    assert registry.register_action(action) is True
    assert registry.list_actions()[0].cardinality == ACTION_CARDINALITY_SINGLE


def test_register_action_normalizes_invalid_cardinality_with_warning(caplog) -> None:
    registry = ActionRegistry()
    action = Action(
        id="plugin.invalid-cardinality",
        label="InvalidCardinality",
        plugin="plugin",
        callback=lambda **_: None,
        cardinality="not-a-real-mode",
    )

    with caplog.at_level(logging.WARNING):
        result = registry.register_action(action)

    assert result is True
    assert registry.list_actions()[0].cardinality == ACTION_CARDINALITY_SINGLE
    assert "Invalid cardinality" in caplog.text


def test_register_action_normalizes_mixed_case_multi_cardinality() -> None:
    registry = ActionRegistry()
    action = Action(
        id="plugin.mixed-case-multi",
        label="MixedCaseMulti",
        plugin="plugin",
        callback=lambda **_: None,
        cardinality="MuLtI",
    )

    assert registry.register_action(action) is True
    assert registry.list_actions()[0].cardinality == ACTION_CARDINALITY_MULTI


def test_invoke_action_missing_id_returns_false(caplog) -> None:
    registry = ActionRegistry()

    with caplog.at_level(logging.WARNING):
        result = registry.invoke_action("missing.action")

    assert result is False
    assert "was not found" in caplog.text


def test_invoke_action_defaults_to_main_dispatch() -> None:
    dispatch = RecordingDispatchExecutor()
    received = []
    registry = ActionRegistry(dispatch_executor=dispatch)
    assert registry.register_action(
        Action(
            id="plugin.main",
            label="Main",
            plugin="plugin",
            callback=lambda **kwargs: received.append(kwargs),
        )
    )

    assert registry.invoke_action("plugin.main", payload={"k": "v"}) is True
    assert dispatch.main_calls == 1
    assert dispatch.worker_calls == 0
    assert received == [{"payload": {"k": "v"}, "source": "hotkey"}]


def test_invoke_action_uses_worker_dispatch_when_configured() -> None:
    dispatch = RecordingDispatchExecutor()
    received = []
    registry = ActionRegistry(dispatch_executor=dispatch)
    assert registry.register_action(
        Action(
            id="plugin.worker",
            label="Worker",
            plugin="plugin",
            callback=lambda **kwargs: received.append(kwargs),
            thread_policy="worker",
        )
    )

    assert registry.invoke_action("plugin.worker", payload={"n": 1}, source="test") is True
    assert dispatch.main_calls == 0
    assert dispatch.worker_calls == 1
    assert received == [{"payload": {"n": 1}, "source": "test"}]


def test_invoke_action_passes_hotkey_when_callback_accepts_kwarg() -> None:
    received = []
    registry = ActionRegistry()

    def _with_hotkey(*, payload=None, source="hotkey", hotkey=None):
        received.append({"payload": payload, "source": source, "hotkey": hotkey})

    assert registry.register_action(
        Action(
            id="plugin.hotkey",
            label="Hotkey",
            plugin="plugin",
            callback=_with_hotkey,
        )
    )

    assert registry.invoke_action(
        "plugin.hotkey",
        payload={"k": "v"},
        source="test",
        hotkey="Ctrl+Shift+O",
    )
    assert received == [{"payload": {"k": "v"}, "source": "test", "hotkey": "Ctrl+Shift+O"}]


def test_invoke_action_omits_hotkey_when_callback_disallows_kwarg() -> None:
    received = []
    registry = ActionRegistry()

    def _no_hotkey(*, payload=None, source="hotkey"):
        received.append({"payload": payload, "source": source})

    assert registry.register_action(
        Action(
            id="plugin.nohotkey",
            label="NoHotkey",
            plugin="plugin",
            callback=_no_hotkey,
        )
    )

    assert registry.invoke_action(
        "plugin.nohotkey",
        payload={"k": "v"},
        source="test",
        hotkey="Ctrl+Shift+O",
    )
    assert received == [{"payload": {"k": "v"}, "source": "test"}]


def test_invoke_action_callback_exception_is_caught(caplog) -> None:
    dispatch = RecordingDispatchExecutor()

    def _boom(**_kwargs):
        raise RuntimeError("boom")

    registry = ActionRegistry(dispatch_executor=dispatch)
    assert registry.register_action(
        Action(
            id="plugin.boom",
            label="Boom",
            plugin="plugin",
            callback=_boom,
        )
    )

    with caplog.at_level(logging.ERROR):
        result = registry.invoke_action("plugin.boom")

    assert result is False
    assert "raised an exception" in caplog.text


def test_invoke_action_disabled_action_noops(caplog) -> None:
    registry = ActionRegistry()
    assert registry.register_action(
        Action(
            id="plugin.disabled",
            label="Disabled",
            plugin="plugin",
            callback=lambda **_: None,
            enabled=False,
        )
    )

    with caplog.at_level(logging.WARNING):
        result = registry.invoke_action("plugin.disabled")

    assert result is False
    assert "is disabled" in caplog.text


def test_queued_main_dispatch_runs_callback_on_main_thread() -> None:
    main_thread_id = threading.get_ident()
    executor = QueuedMainThreadDispatchExecutor(main_thread_id=main_thread_id, timeout_seconds=0.5)
    callback_thread_ids = []
    result_holder = {}

    def run_on_worker():
        result_holder["result"] = executor.run_main(
            lambda: callback_thread_ids.append(threading.get_ident()) or True
        )

    worker = threading.Thread(target=run_on_worker)
    worker.start()

    deadline = time.time() + 1.0
    while worker.is_alive() and time.time() < deadline:
        executor.pump()
        time.sleep(0.01)
    worker.join(timeout=1.0)

    assert worker.is_alive() is False
    assert result_holder["result"] is True
    assert callback_thread_ids == [main_thread_id]


def test_queued_main_dispatch_times_out_when_not_pumped() -> None:
    main_thread_id = threading.get_ident()
    executor = QueuedMainThreadDispatchExecutor(main_thread_id=main_thread_id, timeout_seconds=0.01)
    result_holder = {}

    def run_on_worker():
        result_holder["result"] = executor.run_main(lambda: True)

    worker = threading.Thread(target=run_on_worker)
    worker.start()
    worker.join(timeout=1.0)

    assert worker.is_alive() is False
    assert result_holder["result"] is False
