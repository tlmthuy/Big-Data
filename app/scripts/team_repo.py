"""Helpers for identifying the adjacent team repository."""

import subprocess
from pathlib import Path


def team_commit(root=None):
    repository = Path(root) if root is not None else Path.cwd()
    try:
        return subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
