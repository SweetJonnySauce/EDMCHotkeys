#!/usr/bin/env python3
"""Validate companion artifact release completeness and doc cross-links."""

from __future__ import annotations

from pathlib import Path
import stat
import sys


ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "companion/gnome-extension/edmc-hotkeys@edcd/metadata.json",
    "companion/gnome-extension/edmc-hotkeys@edcd/extension.js",
    "companion/gnome-extension/edmc-hotkeys@edcd/helper_bridge.js",
    "companion/helper/gnome_bridge_companion_send.py",
    "scripts/install_gnome_bridge_companion.sh",
    "scripts/uninstall_gnome_bridge_companion.sh",
    "scripts/verify_gnome_bridge_companion.sh",
    "scripts/package_gnome_bridge_companion.sh",
    "scripts/export_companion_bindings.py",
    "docs/gnome-wayland-bridge-prototype.md",
    "docs/linux-user-setup.md",
    "docs/gnome-companion-compatibility-matrix.md",
]

REQUIRED_EXECUTABLES = [
    "scripts/install_gnome_bridge_companion.sh",
    "scripts/uninstall_gnome_bridge_companion.sh",
    "scripts/verify_gnome_bridge_companion.sh",
    "scripts/package_gnome_bridge_companion.sh",
    "scripts/export_companion_bindings.py",
    "companion/helper/gnome_bridge_companion_send.py",
]

DOC_PATTERNS = {
    "docs/gnome-wayland-bridge-prototype.md": [
        "install_gnome_bridge_companion.sh",
        "export_companion_bindings.py",
        "gnome-companion-compatibility-matrix.md",
    ],
    "docs/linux-user-setup.md": [
        "install_gnome_bridge_companion.sh",
        "verify_gnome_bridge_companion.sh",
        "uninstall_gnome_bridge_companion.sh",
    ],
}


def _is_executable(path: Path) -> bool:
    mode = path.stat().st_mode
    return bool(mode & stat.S_IXUSR)


def main() -> int:
    failures: list[str] = []

    for relpath in REQUIRED_FILES:
        path = ROOT / relpath
        if not path.exists():
            failures.append(f"missing required file: {relpath}")

    for relpath in REQUIRED_EXECUTABLES:
        path = ROOT / relpath
        if not path.exists():
            continue
        if not _is_executable(path):
            failures.append(f"expected executable bit on: {relpath}")

    for relpath, patterns in DOC_PATTERNS.items():
        path = ROOT / relpath
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            if pattern not in text:
                failures.append(f"doc missing required reference '{pattern}': {relpath}")

    if failures:
        print("Companion release check failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("companion release check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
