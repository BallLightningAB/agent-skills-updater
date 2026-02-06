"""Backup creation and rollback functionality."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_skills_updater.cli import Context
    from agent_skills_updater.config import AppConfig
    from agent_skills_updater.lockfile import Lockfile


@dataclass
class BackupInfo:
    """Metadata about a single backup."""

    path: Path
    timestamp: str
    skill_count: int
    skills: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "timestamp": self.timestamp,
            "skillCount": self.skill_count,
            "skills": self.skills,
        }


def _backup_dir(config: AppConfig) -> Path:
    """Return the root backup directory."""
    return config.backup_path


def _timestamp_label() -> str:
    """Generate a filesystem-safe UTC timestamp label with microseconds for uniqueness."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def create_backup(config: AppConfig, lockfile: Lockfile) -> BackupInfo | None:
    """Create a timestamped backup of all currently installed skills.

    Copies each skill target directory's contents and a snapshot of the lockfile
    into a single backup folder.

    Returns BackupInfo on success, None if nothing to back up.
    """
    if not lockfile.entries:
        return None

    ts = _timestamp_label()
    backup_root = _backup_dir(config) / ts
    backup_root.mkdir(parents=True, exist_ok=True)

    backed_up_skills: list[str] = []

    for target_path in config.skill_target_paths:
        if not target_path.is_dir():
            continue

        # Create a subdirectory per target to avoid collisions
        target_label = str(target_path).replace("\\", "_").replace("/", "_").replace(":", "")
        dest = backup_root / target_label

        for skill_name in lockfile.entries:
            skill_dir = target_path / skill_name
            if skill_dir.is_dir():
                skill_dest = dest / skill_name
                skill_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(skill_dir, skill_dest, dirs_exist_ok=True)
                if skill_name not in backed_up_skills:
                    backed_up_skills.append(skill_name)

    # Save lockfile snapshot
    lockfile_snapshot = backup_root / "lockfile.json"
    lockfile_snapshot.write_text(
        json.dumps(lockfile.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Save metadata
    meta = {
        "timestamp": ts,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "skills": backed_up_skills,
    }
    (backup_root / "backup-meta.json").write_text(
        json.dumps(meta, indent=2) + "\n",
        encoding="utf-8",
    )

    # Enforce retention limit
    _enforce_retention(config)

    return BackupInfo(
        path=backup_root,
        timestamp=ts,
        skill_count=len(backed_up_skills),
        skills=backed_up_skills,
    )


def _enforce_retention(config: AppConfig) -> None:
    """Remove old backups exceeding keep_backups limit."""
    root = _backup_dir(config)
    if not root.is_dir():
        return

    backups = sorted(
        [d for d in root.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )

    for old_backup in backups[config.keep_backups :]:
        shutil.rmtree(old_backup, ignore_errors=True)


def list_backups(config: AppConfig) -> list[BackupInfo]:
    """List all available backups, newest first."""
    root = _backup_dir(config)
    if not root.is_dir():
        return []

    results: list[BackupInfo] = []

    dirs = sorted(
        [d for d in root.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )

    for backup_dir in dirs:
        meta_file = backup_dir / "backup-meta.json"
        if meta_file.is_file():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                skills = meta.get("skills", [])
                results.append(
                    BackupInfo(
                        path=backup_dir,
                        timestamp=meta.get("timestamp", backup_dir.name),
                        skill_count=len(skills),
                        skills=skills,
                    )
                )
            except (OSError, json.JSONDecodeError):
                results.append(
                    BackupInfo(
                        path=backup_dir,
                        timestamp=backup_dir.name,
                        skill_count=0,
                        skills=[],
                    )
                )
        else:
            results.append(
                BackupInfo(
                    path=backup_dir,
                    timestamp=backup_dir.name,
                    skill_count=0,
                    skills=[],
                )
            )

    return results


def restore_backup(
    config: AppConfig,
    ctx: Context,
    skill_name: str | None = None,
) -> bool:
    """Restore skills from the latest backup.

    If skill_name is provided, only that skill is restored.
    Otherwise, all skills from the backup are restored.

    Returns True on success.
    """
    backups = list_backups(config)
    if not backups:
        return False

    latest = backups[0]

    if ctx.verbose:
        ctx.console.print(f"  [dim]Restoring from backup: {latest.timestamp}[/]")

    restored_any = False

    for target_path in config.skill_target_paths:
        target_label = str(target_path).replace("\\", "_").replace("/", "_").replace(":", "")
        backup_target = latest.path / target_label

        if not backup_target.is_dir():
            continue

        if skill_name:
            # Restore single skill
            skill_backup = backup_target / skill_name
            if skill_backup.is_dir():
                dest = target_path / skill_name
                if not ctx.dry_run:
                    if dest.exists():
                        shutil.rmtree(dest)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(skill_backup, dest)
                else:
                    ctx.console.print(f"    [dim]Would restore: {dest}[/]")
                restored_any = True
        else:
            # Restore all skills
            for skill_dir in backup_target.iterdir():
                if not skill_dir.is_dir():
                    continue
                dest = target_path / skill_dir.name
                if not ctx.dry_run:
                    if dest.exists():
                        shutil.rmtree(dest)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(skill_dir, dest)
                else:
                    ctx.console.print(f"    [dim]Would restore: {dest}[/]")
                restored_any = True

    # Restore lockfile snapshot if restoring all
    if not skill_name and not ctx.dry_run:
        lockfile_snapshot = latest.path / "lockfile.json"
        if lockfile_snapshot.is_file():
            from agent_skills_updater.lockfile import _lockfile_path

            dest_lockfile = _lockfile_path(config)
            shutil.copy2(lockfile_snapshot, dest_lockfile)

    return restored_any
