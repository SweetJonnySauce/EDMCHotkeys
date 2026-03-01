#!/usr/bin/env python3
"""Validate local markdown links for plugin developer documentation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_FILES = (
    "README.md",
    "docs/register-action-with-edmchotkeys.md",
    "docs/plugin-developer-quickstart.md",
    "docs/plugin-developer-api-reference.md",
    "docs/plugin-developer-api-troubleshooting.md",
    "docs/plugin-developer-api-phase1-requirements.md",
    "docs/plugin-developer-docs-architecture.md",
    "docs/plugin-developer-api-versioning-policy.md",
    "docs/plugin-developer-api-review-checklist.md",
    "docs/plugin-developer-docs-maintenance-pass-phase4.md",
    "docs/architecture/plugin_developer_api_reference_strategy.md",
    "docs/plans/PLUGIN_DEVELOPER_API_DOCUMENTATION_PLAN.md",
)

LINK_RE = re.compile(r"(!)?\[[^\]]*]\(([^)]+)\)")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$")


@dataclass(frozen=True)
class LinkIssue:
    file_path: Path
    line: int
    target: str
    message: str


def _iter_markdown_links(file_path: Path) -> Iterable[tuple[int, str]]:
    in_fence = False
    for idx, raw_line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in LINK_RE.finditer(raw_line):
            target = match.group(2).strip()
            if target:
                yield idx, target


def _split_link_target(target: str) -> tuple[str, str]:
    clean = target.strip()
    if clean.startswith("<") and clean.endswith(">"):
        clean = clean[1:-1].strip()
    if " " in clean:
        clean = clean.split(" ", 1)[0]
    if "#" in clean:
        base, anchor = clean.split("#", 1)
        return base, anchor
    return clean, ""


def _slugify_heading(text: str) -> str:
    lowered = text.strip().lower()
    normalized = re.sub(r"[^\w\s-]", "", lowered)
    dashed = re.sub(r"\s+", "-", normalized)
    return re.sub(r"-{2,}", "-", dashed).strip("-")


def _collect_headings(file_path: Path) -> set[str]:
    in_fence = False
    anchors: set[str] = set()
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(raw_line)
        if not match:
            continue
        anchors.add(_slugify_heading(match.group(1)))
    return anchors


def _is_external(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(("http://", "https://", "mailto:", "ftp://"))


def _resolve_local_target(origin: Path, target_path: str) -> Path:
    if target_path.startswith("/"):
        return (REPO_ROOT / target_path.lstrip("/")).resolve()
    return (origin.parent / target_path).resolve()


def _check_file(file_path: Path) -> list[LinkIssue]:
    issues: list[LinkIssue] = []
    for line, raw_target in _iter_markdown_links(file_path):
        target_path, anchor = _split_link_target(raw_target)
        if _is_external(target_path):
            continue

        if not target_path:
            anchors = _collect_headings(file_path)
            if anchor and anchor not in anchors:
                issues.append(
                    LinkIssue(
                        file_path=file_path,
                        line=line,
                        target=raw_target,
                        message="missing in-file anchor",
                    )
                )
            continue

        resolved = _resolve_local_target(file_path, target_path)
        if not resolved.exists():
            issues.append(
                LinkIssue(
                    file_path=file_path,
                    line=line,
                    target=raw_target,
                    message="target path does not exist",
                )
            )
            continue

        if anchor and resolved.suffix.lower() == ".md":
            anchors = _collect_headings(resolved)
            if anchor not in anchors:
                issues.append(
                    LinkIssue(
                        file_path=file_path,
                        line=line,
                        target=raw_target,
                        message=f"anchor '#{anchor}' not found in target",
                    )
                )
    return issues


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Optional markdown files to check. Defaults to plugin developer docs set.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    candidates = [Path(path) for path in args.paths] if args.paths else [Path(path) for path in DEFAULT_FILES]
    files = [(REPO_ROOT / path).resolve() for path in candidates]

    missing_inputs = [path for path in files if not path.exists()]
    if missing_inputs:
        for path in missing_inputs:
            print(f"check_docs_links: missing input file: {path}")
        return 2

    issues: list[LinkIssue] = []
    for file_path in files:
        if file_path.suffix.lower() != ".md":
            continue
        issues.extend(_check_file(file_path))

    if issues:
        print("check_docs_links: FAIL")
        for issue in issues:
            rel = issue.file_path.relative_to(REPO_ROOT)
            print(f"  - {rel}:{issue.line}: {issue.message}: {issue.target}")
        return 1

    print("check_docs_links: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
