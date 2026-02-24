"""Settings UI state + validation for bindings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .bindings import BindingRecord, BindingsDocument
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
            plugin_name = option.plugin if option is not None else ""
            rows.append(
                BindingRow(
                    id=binding.id,
                    hotkey=binding.hotkey,
                    plugin=plugin_name,
                    action_id=binding.action_id,
                    payload=binding.payload,
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
                        level="error",
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

            if row.enabled and row.hotkey:
                hotkey_key = row.hotkey.casefold()
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
        updated_profiles[self.document.active_profile] = [
            BindingRecord(
                id=row.id,
                hotkey=row.hotkey,
                action_id=row.action_id,
                payload=row.payload,
                enabled=row.enabled,
            )
            for row in self.rows
        ]
        return BindingsDocument(
            version=self.document.version,
            active_profile=self.document.active_profile,
            profiles=updated_profiles,
        )

