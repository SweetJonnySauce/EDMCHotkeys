"""Bindings schema models and conversion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_PROFILE = "Default"


@dataclass(frozen=True)
class BindingRecord:
    """Serializable binding record for bindings.json."""

    id: str
    hotkey: str
    action_id: str
    payload: dict[str, Any] | None = None
    enabled: bool = True


@dataclass(frozen=True)
class BindingsDocument:
    """Versioned document stored in bindings.json."""

    version: int
    active_profile: str
    profiles: dict[str, list[BindingRecord]]


def default_document() -> BindingsDocument:
    return BindingsDocument(version=SCHEMA_VERSION, active_profile=DEFAULT_PROFILE, profiles={DEFAULT_PROFILE: []})


def document_from_dict(data: dict[str, Any]) -> BindingsDocument:
    version = int(data.get("version", SCHEMA_VERSION))
    if version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported bindings version: {version}")

    active_profile = _safe_profile_name(data.get("active_profile"), default=DEFAULT_PROFILE)
    raw_profiles = data.get("profiles")
    if not isinstance(raw_profiles, dict):
        raw_profiles = {DEFAULT_PROFILE: []}

    profiles: dict[str, list[BindingRecord]] = {}
    for profile_name, raw_bindings in raw_profiles.items():
        normalized_profile_name = _safe_profile_name(profile_name, default=DEFAULT_PROFILE)
        bindings: list[BindingRecord] = []
        if isinstance(raw_bindings, list):
            for item in raw_bindings:
                record = binding_record_from_dict(item)
                if record is not None:
                    bindings.append(record)
        profiles[normalized_profile_name] = bindings

    if active_profile not in profiles:
        profiles.setdefault(active_profile, [])
    return BindingsDocument(version=version, active_profile=active_profile, profiles=profiles)


def document_to_dict(document: BindingsDocument) -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "active_profile": document.active_profile,
        "profiles": {
            profile_name: [binding_record_to_dict(binding) for binding in bindings]
            for profile_name, bindings in document.profiles.items()
        },
    }


def binding_record_from_dict(data: Any) -> BindingRecord | None:
    if not isinstance(data, dict):
        return None
    binding_id = _safe_string(data.get("id"))
    hotkey = _safe_string(data.get("hotkey"))
    action_id = _safe_string(data.get("action_id"))
    payload = data.get("payload")
    if payload is not None and not isinstance(payload, dict):
        payload = None
    enabled = bool(data.get("enabled", True))
    if not binding_id or not hotkey or not action_id:
        return None
    return BindingRecord(id=binding_id, hotkey=hotkey, action_id=action_id, payload=payload, enabled=enabled)


def binding_record_to_dict(binding: BindingRecord) -> dict[str, Any]:
    output: dict[str, Any] = {
        "id": binding.id,
        "hotkey": binding.hotkey,
        "action_id": binding.action_id,
        "enabled": binding.enabled,
    }
    if binding.payload is not None:
        output["payload"] = binding.payload
    return output


def _safe_string(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _safe_profile_name(value: Any, *, default: str) -> str:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return default

