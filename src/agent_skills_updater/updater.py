"""Self-update functionality for agent-skills-updater."""

from __future__ import annotations

import subprocess
import sys

import requests

from agent_skills_updater import __version__

_PYPI_URL = "https://pypi.org/pypi/agent-skills-updater/json"
_PACKAGE_NAME = "agent-skills-updater"
_CHECK_TIMEOUT = 2  # seconds


def check_for_update() -> tuple[str, str | None, bool]:
    """Check PyPI for a newer version.

    Returns:
        (current_version, latest_version_or_None, needs_update)
        If the check fails (timeout, offline, etc.), returns (current, None, False).
    """
    current = __version__
    try:
        resp = requests.get(_PYPI_URL, timeout=_CHECK_TIMEOUT)
        resp.raise_for_status()
        latest = resp.json()["info"]["version"]
        needs_update = _version_tuple(latest) > _version_tuple(current)
        return current, latest, needs_update
    except Exception:
        return current, None, False


def run_self_update() -> tuple[bool, str]:
    """Run pip install --upgrade agent-skills-updater.

    Returns:
        (success, output_message)
    """
    current, latest, needs_update = check_for_update()

    if latest is None:
        return False, "Could not reach PyPI to check for updates."

    if not needs_update:
        return True, f"Already up to date (v{current})."

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", _PACKAGE_NAME],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return True, f"Updated v{current} -> v{latest}."
        return False, f"pip exited with code {result.returncode}: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, "Update timed out after 60 seconds."
    except Exception as exc:
        return False, f"Update failed: {exc}"


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse a version string into a comparable tuple."""
    parts: list[int] = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)
