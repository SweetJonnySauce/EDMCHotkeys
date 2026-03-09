"""Canonical runtime plugin version surface."""

from __future__ import annotations

from pathlib import Path

from .semver import SemVerError, add_v_prefix, parse_semver


DEFAULT_PLUGIN_VERSION = "0.0.0-dev.0"
VERSION_FILE_NAME = "VERSION"


def _version_file_path() -> Path:
    return Path(__file__).resolve().parents[1] / VERSION_FILE_NAME


def _read_version_string() -> str:
    path = _version_file_path()
    try:
        raw_value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return DEFAULT_PLUGIN_VERSION
    return raw_value or DEFAULT_PLUGIN_VERSION


def _resolve_plugin_version() -> str:
    value = _read_version_string()
    try:
        parse_semver(value, allow_v_prefix=False)
    except SemVerError as exc:
        raise RuntimeError(f"Invalid plugin runtime version '{value}' from {VERSION_FILE_NAME}: {exc}") from exc
    return value


PLUGIN_VERSION = _resolve_plugin_version()
PLUGIN_TAG_VERSION = add_v_prefix(PLUGIN_VERSION)
