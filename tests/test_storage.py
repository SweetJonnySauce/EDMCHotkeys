from __future__ import annotations

import json
import logging

from edmc_hotkeys.bindings import BindingRecord, BindingsDocument, default_document
from edmc_hotkeys.storage import BindingsStore


def test_load_or_create_creates_default_bindings_file(tmp_path) -> None:
    file_path = tmp_path / "bindings.json"
    store = BindingsStore(file_path, logger=logging.getLogger("test.storage"))

    document = store.load_or_create()

    assert document == default_document()
    assert file_path.exists()
    saved = json.loads(file_path.read_text(encoding="utf-8"))
    assert saved["version"] == 1
    assert saved["active_profile"] == "Default"


def test_store_roundtrip_preserves_profiles(tmp_path) -> None:
    file_path = tmp_path / "bindings.json"
    store = BindingsStore(file_path, logger=logging.getLogger("test.storage"))
    document = BindingsDocument(
        version=1,
        active_profile="Combat",
        profiles={
            "Default": [],
            "Combat": [
                BindingRecord(
                    id="b1",
                    hotkey="Ctrl+Shift+O",
                    action_id="overlay.toggle",
                    payload={"visible": False},
                    enabled=True,
                )
            ],
        },
    )

    store.save(document)
    loaded = store.load_or_create()

    assert loaded == document


def test_invalid_file_falls_back_to_default(tmp_path) -> None:
    file_path = tmp_path / "bindings.json"
    file_path.write_text("{invalid json", encoding="utf-8")
    store = BindingsStore(file_path, logger=logging.getLogger("test.storage"))

    loaded = store.load_or_create()

    assert loaded == default_document()

