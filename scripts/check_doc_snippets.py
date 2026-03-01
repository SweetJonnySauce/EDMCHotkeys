#!/usr/bin/env python3
"""Syntax-check canonical fenced snippets in plugin developer docs."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_FILES = (
    "README.md",
    "docs/register-action-with-edmchotkeys.md",
    "docs/plugin-developer-quickstart.md",
    "docs/plugin-developer-api-reference.md",
    "docs/plugin-developer-api-troubleshooting.md",
    "docs/plugin-developer-api-review-checklist.md",
    "docs/plugin-developer-docs-maintenance-pass-phase4.md",
)

SUPPORTED_LANGS = {"python", "py", "json"}


@dataclass(frozen=True)
class SnippetIssue:
    file_path: Path
    start_line: int
    language: str
    message: str


def _iter_fenced_blocks(file_path: Path):
    in_fence = False
    language = ""
    start_line = 0
    lines: list[str] = []

    for idx, raw_line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            if not in_fence:
                in_fence = True
                language = stripped[3:].strip().lower()
                start_line = idx + 1
                lines = []
            else:
                yield language, start_line, "\n".join(lines)
                in_fence = False
                language = ""
                start_line = 0
                lines = []
            continue
        if in_fence:
            lines.append(raw_line)


def _check_block(language: str, content: str) -> str | None:
    if language in {"python", "py"}:
        try:
            ast.parse(content)
        except SyntaxError as exc:
            return f"python syntax error: {exc.msg}"
        return None
    if language == "json":
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            return f"json parse error: {exc.msg}"
        return None
    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional markdown files to check. Defaults to canonical plugin developer docs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    candidates = [Path(path) for path in args.paths] if args.paths else [Path(path) for path in DEFAULT_FILES]
    files = [(REPO_ROOT / path).resolve() for path in candidates]

    missing_inputs = [path for path in files if not path.exists()]
    if missing_inputs:
        for path in missing_inputs:
            print(f"check_doc_snippets: missing input file: {path}")
        return 2

    issues: list[SnippetIssue] = []
    for file_path in files:
        if file_path.suffix.lower() != ".md":
            continue
        for language, start_line, content in _iter_fenced_blocks(file_path):
            if language not in SUPPORTED_LANGS:
                continue
            problem = _check_block(language, content)
            if problem:
                issues.append(
                    SnippetIssue(
                        file_path=file_path,
                        start_line=start_line,
                        language=language,
                        message=problem,
                    )
                )

    if issues:
        print("check_doc_snippets: FAIL")
        for issue in issues:
            rel = issue.file_path.relative_to(REPO_ROOT)
            print(f"  - {rel}:{issue.start_line} [{issue.language}] {issue.message}")
        return 1

    print("check_doc_snippets: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
