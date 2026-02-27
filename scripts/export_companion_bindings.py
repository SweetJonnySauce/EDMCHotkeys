#!/usr/bin/env python3
"""Export EDMC bindings.json into companion extension config format."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from companion.helper.companion_bindings_export import (
    build_companion_bindings,
    load_bindings_document,
    write_companion_bindings,
)


def _default_output_path() -> str:
    return str(Path.home() / ".config" / "edmc-hotkeys" / "companion-bindings.json")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export EDMC-Hotkeys bindings for GNOME companion extension")
    parser.add_argument("--bindings", default="bindings.json", help="Path to EDMC bindings.json")
    parser.add_argument("--output", default=_default_output_path(), help="Output companion bindings config path")
    parser.add_argument("--profile", default="", help="Profile name override (defaults to active profile)")
    parser.add_argument("--fail-on-skip", action="store_true", help="Exit nonzero when unsupported bindings are skipped")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("EDMC-Hotkeys.companion.export")

    bindings_path = os.path.abspath(args.bindings)
    output_path = os.path.abspath(args.output)
    profile_name = args.profile.strip() or None

    try:
        document = load_bindings_document(bindings_path)
    except Exception as exc:
        log.error("Failed to load bindings document '%s': %s", bindings_path, exc)
        return 2

    bindings, summary = build_companion_bindings(document=document, profile_name=profile_name)
    try:
        write_companion_bindings(output_path, bindings)
    except Exception as exc:
        log.error("Failed to write companion bindings '%s': %s", output_path, exc)
        return 2

    log.info(
        "Companion export complete: output=%s written=%d skipped_disabled=%d skipped_unsupported=%d",
        output_path,
        summary.written,
        summary.skipped_disabled,
        summary.skipped_unsupported,
    )
    if args.fail_on_skip and summary.skipped_unsupported > 0:
        log.error("Unsupported bindings were skipped and --fail-on-skip was set")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
