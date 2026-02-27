#!/usr/bin/env python3
"""Build platform-specific EDMC-Hotkeys release artifacts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile


REPO_ROOT = Path(__file__).resolve().parent.parent
TOP_LEVEL_DIR = "EDMC-Hotkeys"
VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:-rc\.\d+)?$")

GLOBAL_EXCLUDES = (
    ".git",
    ".github",
    ".venv",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
    "docs",
    "tests",
    "AGENTS.md",
    "Makefile",
    "requirements-dev.txt",
    "bindings.json",
)

TREE_FORBIDDEN_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

ALWAYS_REQUIRED = (
    "load.py",
    "edmc_hotkeys",
)


class ReleaseArtifactError(RuntimeError):
    """Raised when release artifact build or verification fails."""


@dataclass(frozen=True)
class VariantSpec:
    """Build/verification policy for one release artifact variant."""

    variant: str
    artifact_suffix: str
    vendor_script: str
    required_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    kept_scripts: tuple[str, ...]
    include_companion_setup_doc: bool


VARIANT_SPECS: dict[str, VariantSpec] = {
    "linux-x11": VariantSpec(
        variant="linux-x11",
        artifact_suffix="linux-x11",
        vendor_script="scripts/vendor_xlib.sh",
        required_paths=("Xlib", "six.py"),
        forbidden_paths=(
            "dbus_next",
            "companion",
            "COMPANION_SETUP.md",
            "scripts/gnome_bridge_send.py",
            "scripts/install_gnome_bridge_companion.sh",
            "scripts/uninstall_gnome_bridge_companion.sh",
            "scripts/verify_gnome_bridge_companion.sh",
            "scripts/export_companion_bindings.py",
            "third_party_licenses/dbus-next.LICENSE",
        ),
        kept_scripts=(),
        include_companion_setup_doc=False,
    ),
    "linux-wayland": VariantSpec(
        variant="linux-wayland",
        artifact_suffix="linux-wayland",
        vendor_script="scripts/vendor_dbus_next.sh",
        required_paths=("dbus_next",),
        forbidden_paths=(
            "Xlib",
            "six.py",
            "companion",
            "COMPANION_SETUP.md",
            "scripts/gnome_bridge_send.py",
            "scripts/install_gnome_bridge_companion.sh",
            "scripts/uninstall_gnome_bridge_companion.sh",
            "scripts/verify_gnome_bridge_companion.sh",
            "scripts/export_companion_bindings.py",
            "third_party_licenses/python-xlib.LICENSE",
            "third_party_licenses/six.LICENSE",
        ),
        kept_scripts=(),
        include_companion_setup_doc=False,
    ),
    "linux-wayland-gnome": VariantSpec(
        variant="linux-wayland-gnome",
        artifact_suffix="linux-wayland-gnome",
        vendor_script="scripts/vendor_dbus_next.sh",
        required_paths=(
            "dbus_next",
            "companion",
            "COMPANION_SETUP.md",
            "scripts/gnome_bridge_send.py",
            "scripts/install_gnome_bridge_companion.sh",
            "scripts/uninstall_gnome_bridge_companion.sh",
            "scripts/verify_gnome_bridge_companion.sh",
            "scripts/export_companion_bindings.py",
        ),
        forbidden_paths=(
            "Xlib",
            "six.py",
            "third_party_licenses/python-xlib.LICENSE",
            "third_party_licenses/six.LICENSE",
        ),
        kept_scripts=(
            "scripts/gnome_bridge_send.py",
            "scripts/install_gnome_bridge_companion.sh",
            "scripts/uninstall_gnome_bridge_companion.sh",
            "scripts/verify_gnome_bridge_companion.sh",
            "scripts/export_companion_bindings.py",
        ),
        include_companion_setup_doc=True,
    ),
}


def validate_version(version: str) -> bool:
    return bool(VERSION_PATTERN.fullmatch(version.strip()))


def _remove_path(root: Path, relpath: str) -> None:
    path = root / relpath
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _copy_workspace(workspace_root: Path) -> None:
    ignore = shutil.ignore_patterns(*GLOBAL_EXCLUDES)
    shutil.copytree(REPO_ROOT, workspace_root, ignore=ignore, dirs_exist_ok=False)


def _run_vendor_script(workspace_root: Path, script_relpath: str) -> None:
    script_path = workspace_root / script_relpath
    if not script_path.exists():
        raise ReleaseArtifactError(f"missing vendor script in workspace: {script_relpath}")

    env = dict(os.environ)
    env.setdefault("EDMC_PYTHON", sys.executable)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    result = subprocess.run(
        [str(script_path)],
        cwd=str(workspace_root),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseArtifactError(
            f"vendoring failed for {script_relpath}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _prune_scripts(workspace_root: Path, kept_scripts: tuple[str, ...]) -> None:
    scripts_dir = workspace_root / "scripts"
    if not scripts_dir.exists():
        return
    keep = set(kept_scripts)
    for child in list(scripts_dir.iterdir()):
        relpath = f"scripts/{child.name}"
        if relpath in keep:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    if not any(scripts_dir.iterdir()):
        scripts_dir.rmdir()


def _prune_python_caches(workspace_root: Path) -> None:
    for cache_dir in workspace_root.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
    for pyc in workspace_root.rglob("*.pyc"):
        if pyc.is_file():
            pyc.unlink()


def apply_variant_policy(workspace_root: Path, spec: VariantSpec) -> None:
    for relpath in GLOBAL_EXCLUDES:
        _remove_path(workspace_root, relpath)
    for relpath in spec.forbidden_paths:
        _remove_path(workspace_root, relpath)

    if not spec.include_companion_setup_doc:
        _remove_path(workspace_root, "COMPANION_SETUP.md")

    _prune_scripts(workspace_root, spec.kept_scripts)
    _prune_python_caches(workspace_root)


def verify_tree(workspace_root: Path, spec: VariantSpec) -> None:
    missing: list[str] = []
    for relpath in (*ALWAYS_REQUIRED, *spec.required_paths):
        if not (workspace_root / relpath).exists():
            missing.append(relpath)
    if missing:
        raise ReleaseArtifactError(f"missing required paths for {spec.variant}: {', '.join(sorted(missing))}")

    present_forbidden = [rel for rel in spec.forbidden_paths if (workspace_root / rel).exists()]
    if present_forbidden:
        raise ReleaseArtifactError(
            f"forbidden paths present for {spec.variant}: {', '.join(sorted(present_forbidden))}"
        )

    present_global_excludes = [rel for rel in GLOBAL_EXCLUDES if (workspace_root / rel).exists()]
    if present_global_excludes:
        raise ReleaseArtifactError(
            "global excluded paths present in release artifact: "
            + ", ".join(sorted(present_global_excludes))
        )

    for path in workspace_root.rglob("*"):
        if path.name in TREE_FORBIDDEN_NAMES:
            relpath = path.relative_to(workspace_root).as_posix()
            raise ReleaseArtifactError(f"forbidden cache directory present: {relpath}")
        if path.is_file() and path.suffix == ".pyc":
            relpath = path.relative_to(workspace_root).as_posix()
            raise ReleaseArtifactError(f"forbidden bytecode file present: {relpath}")


def _verify_tar_layout(artifact_path: Path) -> None:
    with tarfile.open(artifact_path, "r:gz") as archive:
        top_levels: set[str] = set()
        for member in archive.getmembers():
            name = member.name.lstrip("./")
            if not name:
                continue
            top = name.split("/", 1)[0]
            top_levels.add(top)
        if top_levels != {TOP_LEVEL_DIR}:
            joined = ", ".join(sorted(top_levels))
            raise ReleaseArtifactError(
                f"artifact must unpack to single top-level '{TOP_LEVEL_DIR}' directory, found: {joined}"
            )


def build_artifact(*, variant: str, version: str, output_dir: Path, keep_work: bool) -> Path:
    if variant not in VARIANT_SPECS:
        raise ReleaseArtifactError(f"unsupported variant: {variant}")
    if not validate_version(version):
        raise ReleaseArtifactError(f"invalid version format: {version}")

    spec = VARIANT_SPECS[variant]
    output_dir.mkdir(parents=True, exist_ok=True)

    tempdir = Path(tempfile.mkdtemp(prefix=f"release-{variant}-"))
    workspace_root = tempdir / TOP_LEVEL_DIR
    try:
        _copy_workspace(workspace_root)
        _run_vendor_script(workspace_root, spec.vendor_script)
        apply_variant_policy(workspace_root, spec)
        verify_tree(workspace_root, spec)

        artifact_name = f"{TOP_LEVEL_DIR}-{spec.artifact_suffix}-{version}.tar.gz"
        artifact_path = output_dir / artifact_name
        with tarfile.open(artifact_path, "w:gz") as archive:
            archive.add(workspace_root, arcname=TOP_LEVEL_DIR)
        _verify_tar_layout(artifact_path)
        return artifact_path
    finally:
        if keep_work:
            print(f"build workspace retained: {workspace_root}")
        else:
            shutil.rmtree(tempdir, ignore_errors=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(VARIANT_SPECS), required=True)
    parser.add_argument("--version", required=True, help="Version/tag, e.g. v0.1.0 or v0.1.0-rc.1")
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "dist"))
    parser.add_argument("--keep-work", action="store_true", help="Keep intermediate build workspace for debugging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        artifact_path = build_artifact(
            variant=args.variant,
            version=args.version,
            output_dir=Path(args.output_dir),
            keep_work=args.keep_work,
        )
    except ReleaseArtifactError as exc:
        print(f"release artifact build failed: {exc}")
        return 1

    print(f"release artifact built: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
