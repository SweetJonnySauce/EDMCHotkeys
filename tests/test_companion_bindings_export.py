from __future__ import annotations

import json
from pathlib import Path

from companion.helper.companion_bindings_export import (
    build_companion_bindings,
    load_bindings_document,
    write_companion_bindings,
)
from edmc_hotkeys.bindings import BindingRecord, BindingsDocument, document_to_dict


def test_build_companion_bindings_skips_unsupported_and_disabled() -> None:
    document = BindingsDocument(
        version=3,
        active_profile="Default",
        profiles={
            "Default": [
                BindingRecord(
                    id="enabled-generic",
                    plugin="PluginA",
                    modifiers=("ctrl",),
                    key="m",
                    action_id="a",
                    enabled=True,
                ),
                BindingRecord(
                    id="enabled-side-specific",
                    plugin="PluginA",
                    modifiers=("ctrl_l",),
                    key="m",
                    action_id="a",
                    enabled=True,
                ),
                BindingRecord(
                    id="disabled-generic",
                    plugin="PluginA",
                    modifiers=("ctrl",),
                    key="o",
                    action_id="a",
                    enabled=False,
                ),
            ]
        },
    )

    bindings, summary = build_companion_bindings(document=document)

    assert bindings == [{"id": "enabled-generic", "accelerator": "<Ctrl>m", "enabled": True}]
    assert summary.written == 1
    assert summary.skipped_disabled == 1
    assert summary.skipped_unsupported == 1


def test_load_bindings_document_from_file(tmp_path: Path) -> None:
    document = BindingsDocument(version=3, active_profile="Default", profiles={"Default": []})
    path = tmp_path / "bindings.json"
    path.write_text(json.dumps(document_to_dict(document)), encoding="utf-8")

    loaded = load_bindings_document(str(path))

    assert loaded.version == 3
    assert loaded.active_profile == "Default"


def test_write_companion_bindings_writes_expected_json(tmp_path: Path) -> None:
    target = tmp_path / "companion-bindings.json"
    write_companion_bindings(
        str(target),
        [{"id": "b1", "accelerator": "<Ctrl>m", "enabled": True}],
    )

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["bindings"] == [{"id": "b1", "accelerator": "<Ctrl>m", "enabled": True}]
