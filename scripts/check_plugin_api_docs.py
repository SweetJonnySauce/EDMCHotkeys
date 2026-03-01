#!/usr/bin/env python3
"""Validate plugin developer API reference parity with exported API symbols."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = REPO_ROOT / "__init__.py"
LOAD_FILE = REPO_ROOT / "load.py"
REGISTRY_FILE = REPO_ROOT / "edmc_hotkeys" / "registry.py"
PLUGIN_FILE = REPO_ROOT / "edmc_hotkeys" / "plugin.py"
REFERENCE_DOC = REPO_ROOT / "docs" / "plugin-developer-api-reference.md"


@dataclass(frozen=True)
class ApiIssue:
    message: str


def _parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _extract_all_symbols(module: ast.Module) -> list[str]:
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        values: list[str] = []
                        for item in node.value.elts:
                            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                                values.append(item.value)
                        return values
    return []


def _extract_function_param_names(module: ast.Module) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for node in module.body:
        if isinstance(node, ast.FunctionDef):
            params: list[str] = [arg.arg for arg in node.args.posonlyargs]
            params.extend(arg.arg for arg in node.args.args)
            if node.args.vararg is not None:
                params.append(node.args.vararg.arg)
            params.extend(arg.arg for arg in node.args.kwonlyargs)
            if node.args.kwarg is not None:
                params.append(node.args.kwarg.arg)
            output[node.name] = params
    return output


def _extract_dataclass_field_names(module: ast.Module, class_name: str) -> list[str]:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields: list[str] = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.append(item.target.id)
            return fields
    return []


def _parse_reference_signatures() -> dict[str, str]:
    lines = REFERENCE_DOC.read_text(encoding="utf-8").splitlines()
    in_table = False
    table_rows: dict[str, str] = {}

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| Symbol | Signature |"):
            in_table = True
            continue
        if in_table and not stripped.startswith("|"):
            break
        if not in_table or stripped.startswith("| ---"):
            continue

        cells = [cell.strip() for cell in stripped.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        symbol = cells[0].strip("` ")
        signature = cells[1].strip("` ")
        if symbol:
            table_rows[symbol] = signature
    return table_rows


def _extract_signature_param_names(signature: str) -> list[str]:
    match = re.search(r"\((.*)\)", signature)
    if not match:
        return []
    body = match.group(1).strip()
    if not body:
        return []
    names: list[str] = []
    for raw_part in body.split(","):
        part = raw_part.strip()
        if not part:
            continue
        name = part.split(":", 1)[0].strip()
        name = name.split("=", 1)[0].strip()
        if name in {"*", "/"}:
            continue
        names.append(name.lstrip("*"))
    return names


def main(argv: list[str]) -> int:
    del argv
    issues: list[ApiIssue] = []

    init_module = _parse_module(INIT_FILE)
    load_module = _parse_module(LOAD_FILE)
    registry_module = _parse_module(REGISTRY_FILE)
    plugin_module = _parse_module(PLUGIN_FILE)

    exported = _extract_all_symbols(init_module)
    if not exported:
        issues.append(ApiIssue("Could not read __all__ exports from __init__.py"))

    signatures = _parse_reference_signatures()
    for symbol in exported:
        if symbol not in signatures:
            issues.append(ApiIssue(f"API reference is missing exported symbol '{symbol}'"))

    extra_symbols = sorted(set(signatures) - set(exported))
    if extra_symbols:
        for symbol in extra_symbols:
            issues.append(ApiIssue(f"API reference has non-exported symbol '{symbol}'"))

    function_params = _extract_function_param_names(load_module)
    for symbol in exported:
        if symbol in {"Action", "Binding"}:
            continue
        expected = function_params.get(symbol)
        documented = signatures.get(symbol)
        if expected is None or documented is None:
            continue
        doc_params = _extract_signature_param_names(documented)
        if expected != doc_params:
            issues.append(
                ApiIssue(
                    f"Parameter mismatch for '{symbol}': expected {expected}, documented {doc_params}"
                )
            )

    action_fields = _extract_dataclass_field_names(registry_module, "Action")
    action_signature = signatures.get("Action", "")
    if action_signature:
        documented_action_fields = _extract_signature_param_names(action_signature)
        if action_fields != documented_action_fields:
            issues.append(
                ApiIssue(
                    f"Dataclass field mismatch for 'Action': expected {action_fields}, documented {documented_action_fields}"
                )
            )

    binding_fields = _extract_dataclass_field_names(plugin_module, "Binding")
    binding_signature = signatures.get("Binding", "")
    if binding_signature:
        documented_binding_fields = _extract_signature_param_names(binding_signature)
        if binding_fields != documented_binding_fields:
            issues.append(
                ApiIssue(
                    f"Dataclass field mismatch for 'Binding': expected {binding_fields}, documented {documented_binding_fields}"
                )
            )

    if issues:
        print("check_plugin_api_docs: FAIL")
        for issue in issues:
            print(f"  - {issue.message}")
        return 1

    print("check_plugin_api_docs: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
