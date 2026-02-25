"""Settings UI state + validation for bindings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from .bindings import BindingRecord, BindingsDocument
from .hotkey import canonical_hotkey_text, parse_hotkey, pretty_hotkey_text
from .registry import Action


@dataclass(frozen=True)
class ActionOption:
    action_id: str
    label: str
    plugin: str
    enabled: bool


@dataclass(frozen=True)
class BindingRow:
    id: str
    hotkey: str
    plugin: str
    action_id: str
    payload: dict | None = None
    payload_text: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class ValidationIssue:
    level: str  # "error" | "warning"
    row_id: str
    field: str
    message: str


class SettingsState:
    """Editable state used by settings UI + persistence pipeline."""

    def __init__(
        self,
        *,
        document: BindingsDocument,
        action_options: list[ActionOption],
        rows: list[BindingRow],
    ) -> None:
        self.document = document
        self.action_options = action_options
        self.rows = rows

    @classmethod
    def from_document(cls, *, document: BindingsDocument, actions: Iterable[Action]) -> "SettingsState":
        options = [
            ActionOption(
                action_id=action.id,
                label=action.label,
                plugin=action.plugin,
                enabled=action.enabled,
            )
            for action in actions
        ]
        option_by_id = {option.action_id: option for option in options}

        active_bindings = document.profiles.get(document.active_profile, [])
        rows: list[BindingRow] = []
        for binding in active_bindings:
            option = option_by_id.get(binding.action_id)
            plugin_name = binding.plugin or (option.plugin if option is not None else "")
            hotkey = pretty_hotkey_text(modifiers=binding.modifiers, key=binding.key) or binding.key
            rows.append(
                BindingRow(
                    id=binding.id,
                    hotkey=hotkey,
                    plugin=plugin_name,
                    action_id=binding.action_id,
                    payload=binding.payload,
                    payload_text=_payload_to_text(binding.payload),
                    enabled=binding.enabled,
                )
            )
        return cls(document=document, action_options=options, rows=rows)

    def validate(self) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        seen_ids: dict[str, str] = {}
        action_ids = {option.action_id for option in self.action_options}
        action_by_id = {option.action_id: option for option in self.action_options}
        seen_hotkeys: dict[str, str] = {}

        for index, row in enumerate(self.rows):
            row_key = row.id or f"row-{index + 1}"
            if not row.id:
                issues.append(
                    ValidationIssue(level="error", row_id=row_key, field="id", message="Binding id is required")
                )
            elif row.id in seen_ids:
                issues.append(
                    ValidationIssue(
                        level="error",
                        row_id=row_key,
                        field="id",
                        message=f"Duplicate binding id; already used by '{seen_ids[row.id]}'",
                    )
                )
            else:
                seen_ids[row.id] = row_key

            if not row.hotkey:
                issues.append(
                    ValidationIssue(
                        level="error",
                        row_id=row_key,
                        field="hotkey",
                        message="Hotkey is required",
                    )
                )
                parsed_hotkey = None
            else:
                parsed_hotkey = parse_hotkey(row.hotkey)
                if parsed_hotkey is None:
                    issues.append(
                        ValidationIssue(
                            level="error",
                            row_id=row_key,
                            field="hotkey",
                            message=(
                                "Hotkey must include one key and side-specific modifiers "
                                "(LCtrl/RCtrl/LAlt/RAlt/LShift/RShift/LWin/RWin)"
                            ),
                        )
                    )

            if not row.action_id:
                issues.append(
                    ValidationIssue(
                        level="error",
                        row_id=row_key,
                        field="action_id",
                        message="Action is required",
                    )
                )
            elif row.action_id not in action_ids:
                issues.append(
                    ValidationIssue(
                        level="warning",
                        row_id=row_key,
                        field="action_id",
                        message=f"Unknown action '{row.action_id}'",
                    )
                )
            else:
                option = action_by_id[row.action_id]
                if not option.enabled:
                    issues.append(
                        ValidationIssue(
                            level="warning",
                            row_id=row_key,
                            field="action_id",
                            message=f"Action '{row.action_id}' is currently disabled",
                        )
                    )
                if row.plugin and option.plugin and row.plugin.casefold() != option.plugin.casefold():
                    issues.append(
                        ValidationIssue(
                            level="error",
                            row_id=row_key,
                            field="plugin",
                            message=f"Plugin must match action owner '{option.plugin}'",
                        )
                    )

            if not row.plugin:
                issues.append(
                    ValidationIssue(
                        level="error",
                        row_id=row_key,
                        field="plugin",
                        message="Plugin is required",
                    )
                )

            payload_issue = _validate_payload_text(row.payload_text)
            if payload_issue is not None:
                issues.append(
                    ValidationIssue(
                        level="error",
                        row_id=row_key,
                        field="payload",
                        message=payload_issue,
                    )
                )

            if row.enabled and parsed_hotkey is not None:
                hotkey_key = canonical_hotkey_text(
                    modifiers=parsed_hotkey.modifiers,
                    key=parsed_hotkey.key,
                )
                if hotkey_key is None:
                    continue
                conflict_with = seen_hotkeys.get(hotkey_key)
                if conflict_with is not None:
                    issues.append(
                        ValidationIssue(
                            level="error",
                            row_id=row_key,
                            field="hotkey",
                            message=f"Hotkey conflicts with '{conflict_with}'",
                        )
                    )
                else:
                    seen_hotkeys[hotkey_key] = row_key
        return issues

    def to_document(self) -> BindingsDocument:
        updated_profiles = dict(self.document.profiles)
        converted_rows: list[BindingRecord] = []
        for row in self.rows:
            converted = _binding_record_from_row(row)
            if converted is not None:
                converted_rows.append(converted)
        updated_profiles[self.document.active_profile] = converted_rows
        return BindingsDocument(
            version=self.document.version,
            active_profile=self.document.active_profile,
            profiles=updated_profiles,
        )


def _payload_to_text(payload: dict | None) -> str:
    if payload is None:
        return ""
    return _canonical_payload_json(payload)


def _validate_payload_text(payload_text: str) -> str | None:
    text = payload_text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return "Payload must be valid JSON"
    if not isinstance(parsed, dict):
        return "Payload must be a JSON object"
    return None


def _payload_from_row(row: BindingRow) -> dict | None:
    text = row.payload_text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return row.payload
    if isinstance(parsed, dict):
        return parsed
    return row.payload


def _canonical_payload_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _binding_record_from_row(row: BindingRow) -> BindingRecord | None:
    parsed_hotkey = parse_hotkey(row.hotkey)
    if parsed_hotkey is None:
        return None
    return BindingRecord(
        id=row.id,
        plugin=row.plugin,
        modifiers=parsed_hotkey.modifiers,
        key=parsed_hotkey.key,
        action_id=row.action_id,
        payload=_payload_from_row(row),
        enabled=row.enabled,
    )
