from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


def _run_script(repo_root: Path, script_relpath: str, *, env: dict[str, str], args: list[str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [str(repo_root / script_relpath)]
    if args:
        cmd.extend(args)
    return subprocess.run(
        cmd,
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_companion_install_verify_uninstall_workflow(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["HOME"] = str(home)

    install = _run_script(repo_root, "scripts/install_gnome_bridge_companion.sh", env=env)
    assert install.returncode == 0, install.stderr or install.stdout

    ext_dir = home / ".local" / "share" / "gnome-shell" / "extensions" / "edmc-hotkeys@edcd"
    assert (ext_dir / "metadata.json").exists()
    assert (ext_dir / "extension.js").exists()
    assert (ext_dir / "helper" / "gnome_bridge_companion_send.py").exists()

    verify = _run_script(repo_root, "scripts/verify_gnome_bridge_companion.sh", env=env)
    assert verify.returncode == 0, verify.stderr or verify.stdout
    assert "verify: OK" in verify.stdout

    uninstall = _run_script(
        repo_root,
        "scripts/uninstall_gnome_bridge_companion.sh",
        env=env,
        args=["--remove-config"],
    )
    assert uninstall.returncode == 0, uninstall.stderr or uninstall.stdout
    assert not ext_dir.exists()
    assert not (home / ".config" / "edmc-hotkeys" / "companion-bindings.json").exists()


def test_export_companion_bindings_script_generates_output(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    bindings_path = tmp_path / "bindings.json"
    output_path = tmp_path / "companion-bindings.json"
    bindings_path.write_text(
        json.dumps(
            {
                "version": 3,
                "active_profile": "Default",
                "profiles": {
                    "Default": [
                        {
                            "id": "binding-1",
                            "plugin": "PluginA",
                            "modifiers": ["ctrl"],
                            "key": "m",
                            "action_id": "a",
                            "enabled": True,
                        }
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(repo_root / "scripts" / "export_companion_bindings.py"),
            "--bindings",
            str(bindings_path),
            "--output",
            str(output_path),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["bindings"] == [{"id": "binding-1", "accelerator": "<Ctrl>m", "enabled": True}]
