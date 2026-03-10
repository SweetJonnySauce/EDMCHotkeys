#!/usr/bin/env python3
"""Export EDMCHotkeys bindings.json into keyd configuration."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edmc_hotkeys.bindings import document_from_dict
from edmc_hotkeys.keyd_export import export_keyd_bindings, render_keyd_bindings_preview, should_use_systemd
from edmc_hotkeys.runtime_config import load_runtime_config


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export EDMCHotkeys bindings for keyd")
    parser.add_argument("--bindings", default="bindings.json", help="Path to bindings.json")
    parser.add_argument("--plugin-dir", default=".", help="Plugin root path used for runtime/config resolution")
    parser.add_argument("--dry-run", action="store_true", help="Render preview to stdout without writing files")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("EDMCHotkeys.keyd.export")
    plugin_dir = Path(args.plugin_dir).resolve()
    bindings_path = Path(args.bindings).resolve()
    try:
        raw = json.loads(bindings_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("bindings JSON root must be an object")
        document = document_from_dict(raw)
    except Exception as exc:
        log.error("Failed to load bindings document '%s': %s", bindings_path, exc)
        return 2

    config, _sources = load_runtime_config(plugin_dir=plugin_dir, logger=log)
    if args.dry_run:
        print(render_keyd_bindings_preview(document=document), end="")
        return 0

    summary = export_keyd_bindings(
        document=document,
        plugin_dir=plugin_dir,
        config=config,
        logger=log,
    )
    if summary.reload_required:
        if should_use_systemd():
            log.info("keyd export requires reload: %s", summary.systemd_prompt_command)
        else:
            log.info("keyd export requires apply step: %s", summary.non_systemd_prompt_command)
            log.info(summary.non_systemd_restart_hint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
