"""Tests for config loading and validation."""

from pathlib import Path

import pytest

from agent_skills_updater.config import (
    AppConfig,
    ConfigError,
    RepoConfig,
    _expand_path,
    load_config,
)


class TestExpandPath:
    def test_tilde_expansion(self):
        result = _expand_path("~/test")
        assert result == Path.home() / "test"

    def test_absolute_path(self, tmp_path):
        result = _expand_path(str(tmp_path / "foo"))
        assert result == tmp_path / "foo"


class TestRepoConfig:
    def test_valid_structures(self):
        for structure in ("standard", "root", "template", "multi"):
            repo = RepoConfig(name="test", url="https://example.com", structure=structure)
            assert repo.structure == structure

    def test_invalid_structure_raises(self):
        with pytest.raises(ConfigError, match="invalid structure"):
            RepoConfig(name="test", url="https://example.com", structure="invalid")

    def test_default_structure(self):
        repo = RepoConfig(name="test", url="https://example.com")
        assert repo.structure == "standard"


class TestLoadConfig:
    def test_no_config_returns_defaults(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert isinstance(config, AppConfig)
        assert config.repositories == []
        assert config.keep_backups == 5

    def test_load_minimal_config(self, tmp_path):
        config_file = tmp_path / "agent-skills-config.yaml"
        config_file.write_text(
            "settings:\n  globalSkillsPath: ~/test-skills\nrepositories: {}\n",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert config.global_skills_path == Path.home() / "test-skills"
        assert config.repositories == []

    def test_load_with_repositories(self, tmp_path):
        config_file = tmp_path / "agent-skills-config.yaml"
        config_file.write_text(
            """
settings:
  globalSkillsPath: ~/skills
repositories:
  test/repo:
    url: https://github.com/test/repo.git
    skills:
      - skill-a
      - skill-b
    branch: main
    structure: multi
""",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert len(config.repositories) == 1
        repo = config.repositories[0]
        assert repo.name == "test/repo"
        assert repo.url == "https://github.com/test/repo.git"
        assert repo.skills == ["skill-a", "skill-b"]
        assert repo.branch == "main"
        assert repo.structure == "multi"

    def test_load_with_allowed_hosts(self, tmp_path):
        config_file = tmp_path / "agent-skills-config.yaml"
        config_file.write_text(
            """
settings:
  allowedHosts:
    - gitlab.com
    - bitbucket.org
repositories: {}
""",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert config.allowed_hosts == ["gitlab.com", "bitbucket.org"]

    def test_load_with_keep_backups(self, tmp_path):
        config_file = tmp_path / "agent-skills-config.yaml"
        config_file.write_text(
            "settings:\n  keepBackups: 10\nrepositories: {}\n",
            encoding="utf-8",
        )
        config = load_config(config_file)
        assert config.keep_backups == 10

    def test_missing_url_raises(self, tmp_path):
        config_file = tmp_path / "agent-skills-config.yaml"
        config_file.write_text(
            """
repositories:
  bad/repo:
    skills:
      - something
""",
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="'url' is required"):
            load_config(config_file)

    def test_invalid_yaml_raises(self, tmp_path):
        config_file = tmp_path / "agent-skills-config.yaml"
        config_file.write_text("{{invalid yaml", encoding="utf-8")
        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(config_file)

    def test_explicit_nonexistent_path_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="Config file not found"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_config_file_path_stored(self, tmp_path):
        config_file = tmp_path / "agent-skills-config.yaml"
        config_file.write_text("settings: {}\nrepositories: {}\n", encoding="utf-8")
        config = load_config(config_file)
        assert config.config_file_path == config_file

    def test_skill_target_paths(self):
        config = AppConfig()
        paths = config.skill_target_paths
        assert len(paths) == 2
        assert config.global_skills_path in paths
        assert config.windsurf_skills_path in paths
