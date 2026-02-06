"""Tests for skill installer."""

from pathlib import Path

import pytest

from agent_skills_updater.config import AppConfig, RepoConfig
from agent_skills_updater.downloader import DownloadResult
from agent_skills_updater.installer import InstalledSkill, install_skills


class FakeContext:
    """Minimal context for testing."""

    def __init__(self, *, dry_run=False, force=False, verbose=False):
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose
        self.json_output = False
        self._messages = []

        from rich.console import Console

        self.console = Console(quiet=True)


def _make_config(tmp_path: Path) -> AppConfig:
    target1 = tmp_path / "target1"
    target1.mkdir()
    return AppConfig(
        global_skills_path=target1,
        windsurf_skills_path=tmp_path / "target2",  # won't exist, tests single target
    )


def _make_standard_repo(tmp_path: Path, skill_name: str) -> Path:
    """Create a standard structure repo on disk."""
    repo_dir = tmp_path / "repo"
    skill_dir = repo_dir / "skills" / skill_name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")
    return repo_dir


class TestInstallSkillsStandard:
    def test_install_standard_skill(self, tmp_path):
        repo_dir = _make_standard_repo(tmp_path, "test-skill")
        config = _make_config(tmp_path)
        repo = RepoConfig(name="test/repo", url="https://example.com", skills=["test-skill"])
        result = DownloadResult(repo=repo, local_path=repo_dir, success=True)

        installed = install_skills(config, [result], FakeContext())
        assert len(installed) == 1
        assert installed[0].name == "test-skill"
        assert (config.global_skills_path / "test-skill" / "SKILL.md").is_file()

    def test_skip_existing_without_force(self, tmp_path):
        repo_dir = _make_standard_repo(tmp_path, "test-skill")
        config = _make_config(tmp_path)
        # Pre-create existing skill
        existing = config.global_skills_path / "test-skill"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("# Old", encoding="utf-8")

        repo = RepoConfig(name="test/repo", url="https://example.com", skills=["test-skill"])
        result = DownloadResult(repo=repo, local_path=repo_dir, success=True)

        installed = install_skills(config, [result], FakeContext(force=False))
        assert len(installed) == 0
        # Original content preserved
        assert (existing / "SKILL.md").read_text() == "# Old"

    def test_overwrite_with_force(self, tmp_path):
        repo_dir = _make_standard_repo(tmp_path, "test-skill")
        config = _make_config(tmp_path)
        existing = config.global_skills_path / "test-skill"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("# Old", encoding="utf-8")

        repo = RepoConfig(name="test/repo", url="https://example.com", skills=["test-skill"])
        result = DownloadResult(repo=repo, local_path=repo_dir, success=True)

        installed = install_skills(config, [result], FakeContext(force=True))
        assert len(installed) == 1
        assert (existing / "SKILL.md").read_text() == "# Test Skill"


class TestInstallSkillsDryRun:
    def test_dry_run_no_mutations(self, tmp_path):
        repo_dir = _make_standard_repo(tmp_path, "test-skill")
        config = _make_config(tmp_path)
        repo = RepoConfig(name="test/repo", url="https://example.com", skills=["test-skill"])
        result = DownloadResult(repo=repo, local_path=repo_dir, success=True)

        installed = install_skills(config, [result], FakeContext(dry_run=True))
        assert len(installed) == 1
        # But no file was actually created
        assert not (config.global_skills_path / "test-skill").exists()


class TestInstallSkillsFilter:
    def test_skill_filter(self, tmp_path):
        repo_dir = tmp_path / "repo"
        for name in ("skill-a", "skill-b"):
            d = repo_dir / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"# {name}", encoding="utf-8")

        config = _make_config(tmp_path)
        repo = RepoConfig(
            name="test/repo", url="https://example.com", skills=["skill-a", "skill-b"]
        )
        result = DownloadResult(repo=repo, local_path=repo_dir, success=True)

        installed = install_skills(config, [result], FakeContext(), skill_filter=["skill-a"])
        assert len(installed) == 1
        assert installed[0].name == "skill-a"


class TestInstallSkillsStructures:
    def test_root_structure(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "SKILL.md").write_text("# Root Skill", encoding="utf-8")

        config = _make_config(tmp_path)
        repo = RepoConfig(
            name="test/repo", url="https://example.com",
            skills=["root-skill"], structure="root",
        )
        result = DownloadResult(repo=repo, local_path=repo_dir, success=True)

        installed = install_skills(config, [result], FakeContext())
        assert len(installed) == 1

    def test_template_structure(self, tmp_path):
        repo_dir = tmp_path / "repo"
        template_dir = repo_dir / "template"
        template_dir.mkdir(parents=True)
        (template_dir / "SKILL.md").write_text("# Template Skill", encoding="utf-8")

        config = _make_config(tmp_path)
        repo = RepoConfig(
            name="test/repo", url="https://example.com",
            skills=["tmpl-skill"], structure="template",
        )
        result = DownloadResult(repo=repo, local_path=repo_dir, success=True)

        installed = install_skills(config, [result], FakeContext())
        assert len(installed) == 1

    def test_multi_structure(self, tmp_path):
        repo_dir = tmp_path / "repo"
        for name in ("sub-a", "sub-b"):
            d = repo_dir / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"# {name}", encoding="utf-8")

        config = _make_config(tmp_path)
        repo = RepoConfig(
            name="test/repo", url="https://example.com",
            skills=["sub-a", "sub-b"], structure="multi",
        )
        result = DownloadResult(repo=repo, local_path=repo_dir, success=True)

        installed = install_skills(config, [result], FakeContext())
        assert len(installed) == 2


class TestInstalledSkill:
    def test_to_dict(self):
        skill = InstalledSkill(
            name="test", source="org/repo",
            source_url="https://example.com", skill_path="skills/test",
        )
        d = skill.to_dict()
        assert d["name"] == "test"
        assert d["source"] == "org/repo"
        assert "installedAt" in d
        assert "updatedAt" in d

    def test_timestamps_auto_set(self):
        skill = InstalledSkill(
            name="test", source="org/repo",
            source_url="https://example.com", skill_path="skills/test",
        )
        assert skill.installed_at != ""
        assert skill.updated_at != ""
