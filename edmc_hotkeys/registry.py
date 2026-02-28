"""Action registry and dispatch primitives for EDMC Hotkeys."""

from __future__ import annotations

import inspect
import logging
from queue import Empty, Queue
import threading
from dataclasses import dataclass, replace
from typing import Any, Callable, Optional, Protocol


ActionCallback = Callable[..., Any]
ACTION_CARDINALITY_SINGLE = "single"
ACTION_CARDINALITY_MULTI = "multi"
VALID_ACTION_CARDINALITIES = {
    ACTION_CARDINALITY_SINGLE,
    ACTION_CARDINALITY_MULTI,
}


def is_valid_action_cardinality(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().casefold() in VALID_ACTION_CARDINALITIES


def normalize_action_cardinality(value: object) -> str:
    if not isinstance(value, str):
        return ACTION_CARDINALITY_SINGLE
    normalized = value.strip().casefold()
    if normalized in VALID_ACTION_CARDINALITIES:
        return normalized
    return ACTION_CARDINALITY_SINGLE


def _callback_supports_kwarg(callback: ActionCallback, name: str) -> bool:
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        return False
    for param in signature.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True
        if param.name == name and param.kind != inspect.Parameter.POSITIONAL_ONLY:
            return True
    return False


class DispatchExecutor(Protocol):
    """Dispatch bridge for routing action callbacks by thread policy."""

    def run_main(self, callback: Callable[[], bool]) -> bool:
        """Run a callback on the main-thread path."""

    def run_worker(self, callback: Callable[[], bool]) -> bool:
        """Run a callback on the worker-thread path."""


class InlineDispatchExecutor:
    """Runs both main and worker paths inline; useful for tests."""

    def run_main(self, callback: Callable[[], bool]) -> bool:
        return callback()

    def run_worker(self, callback: Callable[[], bool]) -> bool:
        return callback()


class ThreadedWorkerDispatchExecutor:
    """Main dispatch runs inline; worker dispatch runs in a daemon thread."""

    def run_main(self, callback: Callable[[], bool]) -> bool:
        return callback()

    def run_worker(self, callback: Callable[[], bool]) -> bool:
        thread = threading.Thread(target=callback, daemon=True, name="edmc-hotkeys-worker")
        thread.start()
        return True


@dataclass
class _QueuedMainDispatchJob:
    callback: Callable[[], bool]
    done: threading.Event
    result: bool = False


class QueuedMainThreadDispatchExecutor:
    """Marshals main-thread callbacks through a queue pumped on the main thread."""

    def __init__(
        self,
        *,
        main_thread_id: Optional[int] = None,
        timeout_seconds: float = 1.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._main_thread_id = main_thread_id or threading.get_ident()
        self._timeout_seconds = timeout_seconds
        self._logger = logger or logging.getLogger("EDMCHotkeys")
        self._main_queue: Queue[_QueuedMainDispatchJob] = Queue()

    def run_main(self, callback: Callable[[], bool]) -> bool:
        if threading.get_ident() == self._main_thread_id:
            return callback()

        job = _QueuedMainDispatchJob(callback=callback, done=threading.Event())
        self._main_queue.put(job)
        if not job.done.wait(self._timeout_seconds):
            self._logger.warning("Timed out waiting for main-thread dispatch")
            return False
        return job.result

    def run_worker(self, callback: Callable[[], bool]) -> bool:
        thread = threading.Thread(target=callback, daemon=True, name="edmc-hotkeys-worker")
        thread.start()
        return True

    def pump(self, max_items: Optional[int] = None) -> int:
        """Execute queued main-thread callbacks; must run on the main thread."""
        if threading.get_ident() != self._main_thread_id:
            self._logger.warning("Ignoring dispatch pump call from non-main thread")
            return 0

        processed = 0
        while max_items is None or processed < max_items:
            try:
                job = self._main_queue.get_nowait()
            except Empty:
                break

            try:
                job.result = job.callback()
            except Exception:
                self._logger.exception("Queued main-thread callback raised an exception")
                job.result = False
            finally:
                job.done.set()
            processed += 1
        return processed


@dataclass(frozen=True)
class Action:
    """Registry action descriptor."""

    id: str
    label: str
    plugin: str
    callback: ActionCallback
    params_schema: Optional[dict[str, Any]] = None
    thread_policy: str = "main"
    enabled: bool = True
    cardinality: str = ACTION_CARDINALITY_SINGLE


class ActionRegistry:
    """In-memory action registry with guarded dispatch."""

    VALID_THREAD_POLICIES = {"main", "worker"}

    def __init__(
        self,
        *,
        logger: Optional[logging.Logger] = None,
        dispatch_executor: Optional[DispatchExecutor] = None,
    ) -> None:
        self._logger = logger or logging.getLogger("EDMCHotkeys")
        self._dispatch_executor = dispatch_executor or InlineDispatchExecutor()
        self._actions: dict[str, Action] = {}

    def clear(self) -> None:
        """Clear all registered actions (used by plugin lifecycle/tests)."""
        self._actions.clear()

    def register_action(self, action: Action) -> bool:
        """Register an action by unique ID; first registration wins."""
        if action.id in self._actions:
            self._logger.warning("Duplicate action id '%s' ignored", action.id)
            return False
        if action.thread_policy not in self.VALID_THREAD_POLICIES:
            self._logger.warning(
                "Invalid thread_policy '%s' for action '%s'",
                action.thread_policy,
                action.id,
            )
            return False
        if not callable(action.callback):
            self._logger.warning("Non-callable callback for action '%s'", action.id)
            return False
        if not is_valid_action_cardinality(action.cardinality):
            self._logger.warning(
                "Invalid cardinality '%s' for action '%s'; defaulting to '%s'",
                action.cardinality,
                action.id,
                ACTION_CARDINALITY_SINGLE,
            )
        normalized_cardinality = normalize_action_cardinality(action.cardinality)
        if normalized_cardinality != action.cardinality:
            action = replace(action, cardinality=normalized_cardinality)

        self._actions[action.id] = action
        self._logger.debug("Registered action '%s' from plugin '%s'", action.id, action.plugin)
        return True

    def list_actions(self) -> list[Action]:
        """Return actions in registration order."""
        return list(self._actions.values())

    def get_action(self, action_id: str) -> Optional[Action]:
        """Return a registered action or None."""
        return self._actions.get(action_id)

    def invoke_action(
        self,
        action_id: str,
        payload: Optional[dict[str, Any]] = None,
        source: str = "hotkey",
        hotkey: Optional[str] = None,
    ) -> bool:
        """Lookup and dispatch an action callback with guarded error handling."""
        action = self.get_action(action_id)
        if action is None:
            self._logger.warning("Action id '%s' was not found", action_id)
            return False
        if not action.enabled:
            self._logger.warning("Action id '%s' is disabled", action_id)
            return False

        callback = lambda: self._invoke_callback(action, payload, source, hotkey)
        dispatcher = (
            self._dispatch_executor.run_worker
            if action.thread_policy == "worker"
            else self._dispatch_executor.run_main
        )

        try:
            return dispatcher(callback)
        except Exception:
            self._logger.exception("Dispatch failed for action '%s'", action_id)
            return False

    def _invoke_callback(
        self,
        action: Action,
        payload: Optional[dict[str, Any]],
        source: str,
        hotkey: Optional[str],
    ) -> bool:
        try:
            kwargs = {"payload": payload, "source": source}
            if hotkey is not None and _callback_supports_kwarg(action.callback, "hotkey"):
                kwargs["hotkey"] = hotkey
            action.callback(**kwargs)
            return True
        except Exception:
            self._logger.exception("Action '%s' raised an exception", action.id)
            return False
