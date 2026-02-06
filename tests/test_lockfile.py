"""Tests for lockfile management."""

import json
from pathlib import Path

import pytest

from agent_skills_updater.config import AppConfig
from agent_skills_updater.installer import InstalledSkill
from agent_skills_updater.lockfile import Lockfile, load_lockfile, save_lockfile


def _make_config(tmp_path: Path) -> AppConfig:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return AppConfig(global_skills_path=skills_dir)


class TestLockfile:
    def test_empty_lockfile(self):
        lf = Lockfile()
        assert lf.entries == {}

    def test_update_entry_new(self):
        lf = Lockfile()
        skill = InstalledSkill(
            name="test-skill",
            source="org/repo",
            source_url="https://example.com",
            skill_path="skills/test-skill",
        )
        lf.update_entry(skill)
        assert "test-skill" in lf.entries
        entry = lf.entries["test-skill"]
        assert entry["source"] == "org/repo"
        assert entry["installedAt"] != ""
        assert entry["updatedAt"] != ""

    def test_update_entry_preserves_installed_at(self):
        lf = Lockfile(entries={
            "test-skill": {
                "source": "org/repo",
                "sourceUrl": "https://example.com",
                "skillPath": "skills/test-skill",
                "installedAt": "2025-01-01T00:00:00+00:00",
                "updatedAt": "2025-01-01T00:00:00+00:00",
            }
        })
        skill = InstalledSkill(
            name="test-skill",
            source="org/repo",
            source_url="https://example.com",
            skill_path="skills/test-skill",
        )
        lf.update_entry(skill)
        assert lf.entries["test-skill"]["installedAt"] == "2025-01-01T00:00:00+00:00"
        assert lf.entries["test-skill"]["updatedAt"] != "2025-01-01T00:00:00+00:00"

    def test_to_dict(self):
        lf = Lockfile(entries={"a": {"source": "x", "sourceUrl": "y"}})
        d = lf.to_dict()
        assert d["version"] == 1
        assert "a" in d["skills"]


class TestLoadSaveLockfile:
    def test_load_missing_returns_empty(self, tmp_path):
        config = _make_config(tmp_path)
        lf = load_lockfile(config)
        assert lf.entries == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        config = _make_config(tmp_path)
        lf = Lockfile(entries={
            "skill-a": {
                "source": "org/repo",
                "sourceUrl": "https://example.com",
                "skillPath": "skills/skill-a",
                "installedAt": "2025-06-01T12:00:00+00:00",
                "updatedAt": "2025-06-01T12:00:00+00:00",
            }
        })
        save_lockfile(config, lf)

        loaded = load_lockfile(config)
        assert "skill-a" in loaded.entries
        assert loaded.entries["skill-a"]["source"] == "org/repo"

    def test_save_creates_parent_dirs(self, tmp_path):
        config = AppConfig(global_skills_path=tmp_path / "deep" / "path" / "skills")
        lf = Lockfile(entries={"a": {"x": "y"}})
        save_lockfile(config, lf)
        # Parent dir should exist now
        lockfile_path = tmp_path / "deep" / "path" / ".skill-lock.json"
        assert lockfile_path.is_file()

    def test_load_corrupt_json_returns_empty(self, tmp_path):
        config = _make_config(tmp_path)
        lockfile_path = tmp_path / ".skill-lock.json"
        lockfile_path.write_text("{corrupt json", encoding="utf-8")
        lf = load_lockfile(config)
        assert lf.entries == {}

    def test_atomic_write(self, tmp_path):
        """Verify no partial writes — lockfile should be valid JSON after save."""
        config = _make_config(tmp_path)
        lf = Lockfile(entries={"a": {"source": "x"}})
        save_lockfile(config, lf)

        lockfile_path = tmp_path / ".skill-lock.json"
        data = json.loads(lockfile_path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert "a" in data["skills"]
