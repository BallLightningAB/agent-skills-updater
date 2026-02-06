"""Lockfile management for tracking installed skills."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_skills_updater.config import AppConfig
    from agent_skills_updater.installer import InstalledSkill

_LOCKFILE_NAME = ".skill-lock.json"


class Lockfile:
    """In-memory representation of the skill lockfile."""

    def __init__(self, entries: dict[str, dict[str, str]] | None = None) -> None:
        self.entries: dict[str, dict[str, str]] = entries or {}

    def update_entry(self, skill: InstalledSkill) -> None:
        """Add or update a skill entry in the lockfile."""
        existing = self.entries.get(skill.name)
        now = datetime.now(UTC).isoformat(timespec="seconds")

        if existing:
            self.entries[skill.name] = {
                "source": skill.source,
                "sourceUrl": skill.source_url,
                "skillPath": skill.skill_path,
                "installedAt": existing.get("installedAt", now),
                "updatedAt": now,
            }
        else:
            self.entries[skill.name] = {
                "source": skill.source,
                "sourceUrl": skill.source_url,
                "skillPath": skill.skill_path,
                "installedAt": now,
                "updatedAt": now,
            }

    def to_dict(self) -> dict[str, Any]:
        """Serialize lockfile to a dict for JSON output."""
        return {
            "version": 1,
            "skills": self.entries,
        }


def _lockfile_path(config: AppConfig) -> Path:
    """Determine the lockfile location (next to global skills path)."""
    return config.global_skills_path.parent / _LOCKFILE_NAME


def load_lockfile(config: AppConfig) -> Lockfile:
    """Load the lockfile from disk. Returns empty Lockfile if not found."""
    path = _lockfile_path(config)

    if not path.is_file():
        return Lockfile()

    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError):
        return Lockfile()

    if not isinstance(data, dict):
        return Lockfile()

    entries = data.get("skills", data)
    if not isinstance(entries, dict):
        return Lockfile()

    # Normalize: ensure all values are dicts with string values
    clean: dict[str, dict[str, str]] = {}
    for name, entry in entries.items():
        if isinstance(entry, dict):
            clean[name] = {k: str(v) for k, v in entry.items()}

    return Lockfile(entries=clean)


def save_lockfile(config: AppConfig, lockfile: Lockfile) -> None:
    """Save the lockfile to disk using atomic write (temp file + rename)."""
    path = _lockfile_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = json.dumps(lockfile.to_dict(), indent=2, ensure_ascii=False) + "\n"

    # Atomic write: write to temp file in same directory, then rename
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=path.parent, suffix=".tmp", prefix=".skill-lock-"
        )
        try:
            with open(fd, "w", encoding="utf-8") as f:
                f.write(content)
            Path(tmp_path).replace(path)
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise
    except OSError as exc:
        raise OSError(f"Failed to write lockfile: {exc}") from exc
