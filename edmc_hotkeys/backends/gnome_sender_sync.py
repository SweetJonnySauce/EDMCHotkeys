"""GNOME custom-keybinding sync for bridge sender automation."""

from __future__ import annotations

import ast
import hashlib
import logging
from pathlib import Path
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Sequence

from .hotkey_parser import parse_hotkey

_MEDIA_KEYS_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
_CUSTOM_KEYBINDINGS_KEY = "custom-keybindings"
_ENTRY_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
_ENTRY_PATH_PREFIX = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"
_ENTRY_NAME_PREFIX = "EDMC Hotkeys"
_MANAGED_PREFIX = "edmc-hotkeys-"

_SPECIAL_GNOME_KEYS = {
    "enter": "Return",
    "esc": "Escape",
    "space": "space",
    "tab": "Tab",
}

_MODIFIER_TOKENS = {
    "ctrl": "<Ctrl>",
    "alt": "<Alt>",
    "shift": "<Shift>",
    "win": "<Super>",
}


RunCommand = Callable[[Sequence[str]], tuple[int, str, str]]


@dataclass(frozen=True)
class SyncResult:
    """Result of attempting to synchronize managed GNOME keybindings."""

    ok: bool
    synced_bindings: int
    error: Optional[str] = None


def default_sender_script_path() -> str:
    plugin_root = Path(__file__).resolve().parents[2]
    return str(plugin_root / "scripts" / "gnome_bridge_send.py")


def hotkey_to_gnome_accelerator(hotkey: str) -> Optional[str]:
    """Convert canonical/pretty EDMC hotkey text to GNOME accelerator text."""
    parsed = parse_hotkey(hotkey)
    if parsed is None:
        return None

    modifier_tokens: list[str] = []
    for modifier in parsed.modifiers:
        if modifier.endswith("_l") or modifier.endswith("_r"):
            return None
        token = _MODIFIER_TOKENS.get(modifier)
        if token is None:
            return None
        modifier_tokens.append(token)

    key = parsed.key
    if len(key) == 1:
        gnome_key = key.lower()
    elif key.startswith("f") and key[1:].isdigit():
        gnome_key = f"F{key[1:]}"
    else:
        gnome_key = _SPECIAL_GNOME_KEYS.get(key)
        if gnome_key is None:
            return None
    return "".join([*modifier_tokens, gnome_key])


def _default_run_command(args: Sequence[str]) -> tuple[int, str, str]:
    completed = subprocess.run(args, capture_output=True, text=True, check=False)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _format_string_array(paths: Sequence[str]) -> str:
    if not paths:
        return "[]"
    quoted = ", ".join(f"'{path}'" for path in paths)
    return f"[{quoted}]"


def _parse_string_array(raw: str) -> Optional[list[str]]:
    text = raw.strip()
    if text in {"", "@as []"}:
        return []
    try:
        parsed = ast.literal_eval(text)
    except Exception:
        return None
    if not isinstance(parsed, list):
        return None
    values: list[str] = []
    for item in parsed:
        if not isinstance(item, str):
            return None
        values.append(item)
    return values


class GnomeBridgeSenderSync:
    """Synchronize EDMC bridge bindings into GNOME custom keybindings."""

    def __init__(
        self,
        *,
        socket_path: str,
        sender_script_path: str,
        token_file_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        run_command: Optional[RunCommand] = None,
        gsettings_bin: str = "gsettings",
    ) -> None:
        self._socket_path = socket_path
        self._sender_script_path = sender_script_path
        self._token_file_path = token_file_path
        self._logger = logger or logging.getLogger("EDMC-Hotkeys")
        self._run_command = run_command or _default_run_command
        self._gsettings_bin = gsettings_bin

    def set_token_file_path(self, token_file_path: str) -> None:
        self._token_file_path = token_file_path

    def is_available(self) -> tuple[bool, Optional[str]]:
        executable = shutil.which(self._gsettings_bin)
        if executable is None:
            return False, f"{self._gsettings_bin} not found"
        script_path = Path(self._sender_script_path)
        if not script_path.exists():
            return False, f"sender script missing: {script_path}"
        return True, None

    def sync_bindings(self, bindings: Mapping[str, str]) -> SyncResult:
        available, reason = self.is_available()
        if not available:
            return SyncResult(ok=False, synced_bindings=0, error=reason)

        selected: list[tuple[str, str, str]] = []
        seen_accelerators: dict[str, str] = {}
        for binding_id in sorted(bindings):
            hotkey = bindings[binding_id]
            accelerator = hotkey_to_gnome_accelerator(hotkey)
            if accelerator is None:
                self._logger.warning(
                    "GNOME sender sync skipped unsupported binding: id=%s hotkey=%s",
                    binding_id,
                    hotkey,
                )
                continue
            conflict_with = seen_accelerators.get(accelerator)
            if conflict_with is not None:
                self._logger.warning(
                    "GNOME sender sync skipped duplicate accelerator: accelerator=%s id=%s conflicts_with=%s",
                    accelerator,
                    binding_id,
                    conflict_with,
                )
                continue
            seen_accelerators[accelerator] = binding_id
            selected.append((self._entry_path_for_binding(binding_id), binding_id, accelerator))

        existing = self._read_custom_keybinding_paths()
        if existing is None:
            return SyncResult(ok=False, synced_bindings=0, error="could not read GNOME custom keybinding list")

        unowned = [path for path in existing if not self._is_managed_path(path)]
        desired_paths = [path for path, _, _ in selected]
        merged_paths = [*unowned, *desired_paths]
        if merged_paths != existing:
            if not self._set_key(_MEDIA_KEYS_SCHEMA, _CUSTOM_KEYBINDINGS_KEY, _format_string_array(merged_paths)):
                return SyncResult(ok=False, synced_bindings=0, error="could not update GNOME custom keybinding list")

        for path, binding_id, accelerator in selected:
            scoped_schema = f"{_ENTRY_SCHEMA}:{path}"
            if not self._set_key(scoped_schema, "name", f"{_ENTRY_NAME_PREFIX}: {binding_id}"):
                return SyncResult(ok=False, synced_bindings=0, error=f"could not set name for {binding_id}")
            if not self._set_key(scoped_schema, "command", self._command_for_binding(binding_id)):
                return SyncResult(ok=False, synced_bindings=0, error=f"could not set command for {binding_id}")
            if not self._set_key(scoped_schema, "binding", accelerator):
                return SyncResult(ok=False, synced_bindings=0, error=f"could not set accelerator for {binding_id}")
        return SyncResult(ok=True, synced_bindings=len(selected))

    def clear_managed_bindings(self) -> SyncResult:
        return self.sync_bindings({})

    def _entry_path_for_binding(self, binding_id: str) -> str:
        digest = hashlib.sha1(binding_id.encode("utf-8")).hexdigest()[:8]
        safe_token = "".join(ch if ch.isalnum() else "-" for ch in binding_id.lower()).strip("-")
        if not safe_token:
            safe_token = "binding"
        return f"{_ENTRY_PATH_PREFIX}{_MANAGED_PREFIX}{safe_token}-{digest}/"

    def _is_managed_path(self, path: str) -> bool:
        return path.startswith(f"{_ENTRY_PATH_PREFIX}{_MANAGED_PREFIX}")

    def _command_for_binding(self, binding_id: str) -> str:
        script = shlex.quote(self._sender_script_path)
        socket_path = shlex.quote(self._socket_path)
        binding = shlex.quote(binding_id)
        token_arg = ""
        if self._token_file_path:
            token_file = shlex.quote(self._token_file_path)
            token_arg = f" --token-file {token_file}"
        return f"python3 {script} --socket {socket_path} --binding-id {binding}{token_arg}"

    def _read_custom_keybinding_paths(self) -> Optional[list[str]]:
        code, stdout, stderr = self._run(
            [self._gsettings_bin, "get", _MEDIA_KEYS_SCHEMA, _CUSTOM_KEYBINDINGS_KEY]
        )
        if code != 0:
            self._logger.warning(
                "GNOME sender sync failed to read custom keybindings: code=%s stderr=%s",
                code,
                stderr or stdout,
            )
            return None
        parsed = _parse_string_array(stdout)
        if parsed is None:
            self._logger.warning("GNOME sender sync got unparseable custom keybinding list: %s", stdout)
            return None
        return parsed

    def _set_key(self, schema: str, key: str, value: str) -> bool:
        code, stdout, stderr = self._run([self._gsettings_bin, "set", schema, key, value])
        if code == 0:
            return True
        self._logger.warning(
            "GNOME sender sync failed gsettings set: schema=%s key=%s code=%s stderr=%s",
            schema,
            key,
            code,
            stderr or stdout,
        )
        return False

    def _run(self, args: Sequence[str]) -> tuple[int, str, str]:
        try:
            return self._run_command(args)
        except Exception as exc:
            self._logger.warning("GNOME sender sync command failed: %s", exc)
            return 1, "", str(exc)
