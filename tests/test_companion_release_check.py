from __future__ import annotations

from pathlib import Path
import subprocess


def test_companion_release_check_script_passes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["python3", "scripts/check_companion_release.py"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "companion release check: OK" in result.stdout
