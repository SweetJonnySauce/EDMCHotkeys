"""Export EDMC bindings.json entries into companion extension binding config."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional

from edmc_hotkeys.backends.gnome_sender_sync import hotkey_to_gnome_accelerator
from edmc_hotkeys.bindings import BindingsDocument, document_from_dict
from edmc_hotkeys.hotkey import canonical_hotkey_text


@dataclass(frozen=True)
class ExportSummary:
    written: int
    skipped_disabled: int
    skipped_unsupported: int


def load_bindings_document(path: str) -> BindingsDocument:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("bindings document must be a JSON object")
    return document_from_dict(raw)


def build_companion_bindings(
    *,
    document: BindingsDocument,
    profile_name: Optional[str] = None,
) -> tuple[list[dict[str, object]], ExportSummary]:
    profile = profile_name or document.active_profile
    records = list(document.profiles.get(profile, []))

    bindings: list[dict[str, object]] = []
    skipped_disabled = 0
    skipped_unsupported = 0
    for record in records:
        if not record.enabled:
            skipped_disabled += 1
            continue
        canonical = canonical_hotkey_text(modifiers=record.modifiers, key=record.key)
        if not canonical:
            skipped_unsupported += 1
            continue
        accelerator = hotkey_to_gnome_accelerator(canonical)
        if not accelerator:
            skipped_unsupported += 1
            continue
        bindings.append(
            {
                "id": record.id,
                "accelerator": accelerator,
                "enabled": True,
            }
        )
    bindings.sort(key=lambda item: str(item.get("id", "")))
    summary = ExportSummary(
        written=len(bindings),
        skipped_disabled=skipped_disabled,
        skipped_unsupported=skipped_unsupported,
    )
    return bindings, summary


def write_companion_bindings(path: str, bindings: list[dict[str, object]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "bindings": bindings,
    }
    target.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
