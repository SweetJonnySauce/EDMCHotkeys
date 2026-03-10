#!/usr/bin/env python3
"""Validate/normalize release versions for CI workflows."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edmc_hotkeys.semver import SemVerError, parse_semver


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Release tag version with 'v' prefix")
    parser.add_argument(
        "--require-prerelease",
        action="store_true",
        help="Reject stable versions and require prerelease metadata",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    raw_version = args.version.strip()
    try:
        semver = parse_semver(raw_version, allow_v_prefix=True, require_v_prefix=True)
    except SemVerError as exc:
        print(f"invalid version: {exc}", file=sys.stderr)
        return 1

    if args.require_prerelease and not semver.is_prerelease:
        print("version must be a prerelease for this action", file=sys.stderr)
        return 1

    print(f"version={semver.to_string(v_prefix=True)}")
    print(f"runtime_version={semver.to_string(v_prefix=False)}")
    print(f"base_version=v{semver.core}")
    print(f"prerelease={'true' if semver.is_prerelease else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
