#!/usr/bin/env python3
"""Fail if production modules use print() instead of logger calls."""

from __future__ import annotations

import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    ROOT / "load.py",
    ROOT / "edmc_hotkeys",
]


def _python_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(file_path for file_path in path.rglob("*.py") if file_path.is_file())


def _print_call_lines(path: Path) -> list[int]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            lines.append(int(node.lineno))
    return sorted(lines)


def main() -> int:
    failures: list[str] = []
    for target in TARGETS:
        for file_path in _python_files(target):
            lines = _print_call_lines(file_path)
            for line in lines:
                failures.append(f"{file_path.relative_to(ROOT)}:{line}: print() is not allowed")

    if failures:
        print("Found disallowed print() usage:")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print("check_no_print: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
