#!/usr/bin/env python3
"""Print the current keyd prefs alert state as EDMCHotkeys computes it."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))

from edmc_hotkeys.backends.selector import detect_linux_session
from edmc_hotkeys.keyd_prefs_alerts import (
    detect_keyd_availability,
    detect_keyd_export_required,
    detect_keyd_integration,
)
from edmc_hotkeys.runtime_config import load_runtime_config


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plugin-dir",
        default=str(_PLUGIN_ROOT),
        help="Path to EDMCHotkeys plugin directory (default: repo root)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    plugin_dir = Path(args.plugin_dir).resolve()
    config, _sources = load_runtime_config(plugin_dir=plugin_dir)
    session = detect_linux_session(os.environ)
    mode = (config.backend_mode or "auto").strip().lower()
    keyd = detect_keyd_availability()

    if mode == "wayland_keyd":
        selected = "linux-wayland-keyd"
    elif mode == "x11":
        selected = "linux-x11"
    elif mode == "auto" and session == "wayland":
        selected = "linux-wayland-keyd" if keyd.available else "inactive"
    else:
        selected = "inactive"

    state = "Inactive"
    reason = ""
    if selected == "linux-wayland-keyd":
        if not keyd.available:
            state = "KeydMissing"
            reason = keyd.reason
        else:
            integration = detect_keyd_integration(apply_target_path=config.keyd_apply_target_path)
            if not integration.installed:
                state = "IntegrationMissing"
                reason = integration.reason
            else:
                export = detect_keyd_export_required(plugin_dir=plugin_dir, config=config)
                if export.export_required:
                    state = "ExportRequired"
                    reason = export.reason
                else:
                    state = "Ready"
    elif mode == "auto" and session == "wayland" and not keyd.available:
        state = "AutoHint"
        reason = keyd.reason

    print(f"plugin_dir={plugin_dir}")
    print(f"mode={mode}")
    print(f"session={session}")
    print(f"selected_backend={selected}")
    print(f"keyd_available={keyd.available} ({keyd.reason})")
    print(f"alert_state={state}")
    if reason:
        print(f"reason={reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
