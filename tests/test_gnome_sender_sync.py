from __future__ import annotations

import ast
import logging
from pathlib import Path

from edmc_hotkeys.backends.gnome_sender_sync import GnomeBridgeSenderSync, hotkey_to_gnome_accelerator


class _FakeGSettings:
    def __init__(self) -> None:
        self.custom_keybindings: list[str] = ["/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/existing/"]
        self.entry_values: dict[tuple[str, str], str] = {}

    def run(self, args) -> tuple[int, str, str]:
        if len(args) < 4:
            return 1, "", "bad command"
        _bin, op, schema, key = args[0], args[1], args[2], args[3]
        if op == "get":
            if schema != "org.gnome.settings-daemon.plugins.media-keys" or key != "custom-keybindings":
                return 1, "", "unknown get target"
            rendered = "[" + ", ".join(f"'{path}'" for path in self.custom_keybindings) + "]"
            return 0, rendered, ""
        if op == "set":
            value = args[4] if len(args) > 4 else ""
            if schema == "org.gnome.settings-daemon.plugins.media-keys" and key == "custom-keybindings":
                parsed = ast.literal_eval(value)
                if not isinstance(parsed, list):
                    return 1, "", "invalid list"
                self.custom_keybindings = [str(item) for item in parsed]
                return 0, "", ""
            self.entry_values[(schema, key)] = value
            return 0, "", ""
        return 1, "", "unsupported op"


def test_hotkey_to_gnome_accelerator_mappings() -> None:
    assert hotkey_to_gnome_accelerator("Ctrl+M") == "<Ctrl>m"
    assert hotkey_to_gnome_accelerator("Ctrl+Shift+L") == "<Ctrl><Shift>l"
    assert hotkey_to_gnome_accelerator("F5") == "F5"
    assert hotkey_to_gnome_accelerator("Space") == "space"
    assert hotkey_to_gnome_accelerator("LCtrl+M") is None


def test_sender_sync_updates_managed_paths_and_commands(tmp_path) -> None:
    fake = _FakeGSettings()
    sender_script = tmp_path / "send.py"
    sender_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    sync = GnomeBridgeSenderSync(
        socket_path=str(tmp_path / "bridge.sock"),
        sender_script_path=str(sender_script),
        logger=logging.getLogger("test.sender_sync"),
        run_command=fake.run,
        gsettings_bin="python3",
    )

    result = sync.sync_bindings(
        {
            "hotkeys_test_toggle": "Ctrl+M",
            "hotkeys_test_off": "Ctrl+O",
        }
    )

    assert result.ok is True
    assert result.synced_bindings == 2
    assert len(fake.custom_keybindings) == 3
    assert fake.custom_keybindings[0].endswith("/existing/")
    managed_paths = [path for path in fake.custom_keybindings if "edmc-hotkeys-" in path]
    assert len(managed_paths) == 2

    command_entries = [(schema, key, value) for (schema, key), value in fake.entry_values.items() if key == "command"]
    assert command_entries
    assert all(str(Path(sender_script)) in value for _schema, _key, value in command_entries)


def test_sender_sync_skips_duplicate_and_unsupported_bindings(tmp_path) -> None:
    fake = _FakeGSettings()
    sender_script = tmp_path / "send.py"
    sender_script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    sync = GnomeBridgeSenderSync(
        socket_path=str(tmp_path / "bridge.sock"),
        sender_script_path=str(sender_script),
        logger=logging.getLogger("test.sender_sync"),
        run_command=fake.run,
        gsettings_bin="python3",
    )

    result = sync.sync_bindings(
        {
            "a": "Ctrl+M",
            "b": "Ctrl+M",
            "c": "LCtrl+M",
        }
    )

    assert result.ok is True
    assert result.synced_bindings == 1
    managed_paths = [path for path in fake.custom_keybindings if "edmc-hotkeys-" in path]
    assert len(managed_paths) == 1
