"""Tests for backup creation and rollback."""

import json
from pathlib import Path

import pytest

from agent_skills_updater.backup import (
    BackupInfo,
    create_backup,
    list_backups,
    restore_backup,
)
from agent_skills_updater.config import AppConfig
from agent_skills_updater.lockfile import Lockfile


class FakeContext:
    """Minimal context for testing."""

    def __init__(self, *, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.force = False
        self.json_output = False

        from rich.console import Console

        self.console = Console(quiet=True)


def _make_config(tmp_path: Path) -> AppConfig:
    skills = tmp_path / "skills"
    skills.mkdir()
    backups = tmp_path / "backups"
    return AppConfig(
        global_skills_path=skills,
        windsurf_skills_path=tmp_path / "windsurf_skills",
        backup_path=backups,
        keep_backups=3,
    )


def _create_skill(skills_path: Path, name: str, content: str = "# Skill") -> None:
    d = skills_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(content, encoding="utf-8")


class TestCreateBackup:
    def test_empty_lockfile_returns_none(self, tmp_path):
        config = _make_config(tmp_path)
        result = create_backup(config, Lockfile())
        assert result is None

    def test_creates_backup_with_metadata(self, tmp_path):
        config = _make_config(tmp_path)
        _create_skill(config.global_skills_path, "skill-a")
        lf = Lockfile(entries={"skill-a": {"source": "test"}})

        result = create_backup(config, lf)
        assert result is not None
        assert result.skill_count == 1
        assert "skill-a" in result.skills
        assert result.path.is_dir()
        assert (result.path / "backup-meta.json").is_file()
        assert (result.path / "lockfile.json").is_file()

    def test_retention_limit(self, tmp_path):
        config = _make_config(tmp_path)
        _create_skill(config.global_skills_path, "skill-a")
        lf = Lockfile(entries={"skill-a": {"source": "test"}})

        # Create more backups than the limit
        for _ in range(5):
            create_backup(config, lf)

        backups = list_backups(config)
        assert len(backups) <= config.keep_backups


class TestListBackups:
    def test_no_backups(self, tmp_path):
        config = _make_config(tmp_path)
        assert list_backups(config) == []

    def test_lists_backups_newest_first(self, tmp_path):
        config = _make_config(tmp_path)
        _create_skill(config.global_skills_path, "skill-a")
        lf = Lockfile(entries={"skill-a": {"source": "test"}})

        create_backup(config, lf)
        create_backup(config, lf)

        backups = list_backups(config)
        assert len(backups) >= 2
        # Newest first
        assert backups[0].timestamp >= backups[1].timestamp


class TestRestoreBackup:
    def test_restore_all(self, tmp_path):
        config = _make_config(tmp_path)
        _create_skill(config.global_skills_path, "skill-a", "# Original")
        lf = Lockfile(entries={"skill-a": {"source": "test"}})
        create_backup(config, lf)

        # Modify skill
        (config.global_skills_path / "skill-a" / "SKILL.md").write_text("# Modified")

        ctx = FakeContext()
        success = restore_backup(config, ctx)
        assert success
        assert (config.global_skills_path / "skill-a" / "SKILL.md").read_text() == "# Original"

    def test_restore_single_skill(self, tmp_path):
        config = _make_config(tmp_path)
        _create_skill(config.global_skills_path, "skill-a", "# A")
        _create_skill(config.global_skills_path, "skill-b", "# B")
        lf = Lockfile(entries={"skill-a": {"source": "test"}, "skill-b": {"source": "test"}})
        create_backup(config, lf)

        # Modify both
        (config.global_skills_path / "skill-a" / "SKILL.md").write_text("# A Modified")
        (config.global_skills_path / "skill-b" / "SKILL.md").write_text("# B Modified")

        ctx = FakeContext()
        success = restore_backup(config, ctx, skill_name="skill-a")
        assert success
        assert (config.global_skills_path / "skill-a" / "SKILL.md").read_text() == "# A"
        # skill-b should still be modified
        assert (config.global_skills_path / "skill-b" / "SKILL.md").read_text() == "# B Modified"

    def test_restore_dry_run(self, tmp_path):
        config = _make_config(tmp_path)
        _create_skill(config.global_skills_path, "skill-a", "# Original")
        lf = Lockfile(entries={"skill-a": {"source": "test"}})
        create_backup(config, lf)

        (config.global_skills_path / "skill-a" / "SKILL.md").write_text("# Modified")

        ctx = FakeContext(dry_run=True)
        success = restore_backup(config, ctx)
        assert success
        # File should NOT be restored in dry-run
        assert (config.global_skills_path / "skill-a" / "SKILL.md").read_text() == "# Modified"

    def test_restore_no_backups(self, tmp_path):
        config = _make_config(tmp_path)
        ctx = FakeContext()
        assert restore_backup(config, ctx) is False


class TestBackupInfo:
    def test_to_dict(self, tmp_path):
        info = BackupInfo(
            path=tmp_path / "backup",
            timestamp="20250601T120000Z",
            skill_count=3,
            skills=["a", "b", "c"],
        )
        d = info.to_dict()
        assert d["timestamp"] == "20250601T120000Z"
        assert d["skillCount"] == 3
        assert len(d["skills"]) == 3
