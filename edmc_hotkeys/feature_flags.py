"""Temporary feature flags for incremental rollout."""

from __future__ import annotations

import os


ENABLE_WINDOWS_LOW_LEVEL_HOOK = os.getenv("EDMC_HOTKEYS_ENABLE_WINDOWS_LOW_LEVEL_HOOK", "0") == "1"

