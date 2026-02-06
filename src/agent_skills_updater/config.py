"""Configuration loading and validation."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Default config search paths (checked in order)
_DEFAULT_CONFIG_NAMES = [
    "agent-skills-config.yaml",
    "agent-skills-config.yml",
]


def _default_config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    if platform.system() == "Windows":
        base = Path.home() / "AppData" / "Local"
    else:
        xdg = Path.home() / ".config"
        base = xdg
    return base / "agent-skills-updater"


def _expand_path(raw: str) -> Path:
    """Expand ~ and environment variables in a path string."""
    return Path(raw).expanduser().resolve()


@dataclass
class RepoConfig:
    """Configuration for a single skill repository."""

    name: str
    url: str
    skills: list[str] = field(default_factory=list)
    branch: str | None = None
    structure: str = "standard"

    def __post_init__(self) -> None:
        valid_structures = {"standard", "root", "template", "multi"}
        if self.structure not in valid_structures:
            raise ConfigError(
                f"Repository '{self.name}': invalid structure '{self.structure}'. "
                f"Must be one of: {', '.join(sorted(valid_structures))}"
            )


@dataclass
class AppConfig:
    """Application configuration loaded from YAML."""

    # Skill install paths
    global_skills_path: Path = field(default_factory=lambda: Path.home() / ".agents" / "skills")
    windsurf_skills_path: Path = field(
        default_factory=lambda: Path.home() / ".codeium" / "windsurf" / "skills"
    )

    # Working paths
    temp_path: Path = field(
        default_factory=lambda: Path.home() / ".temp-agent-skills-update"
    )
    log_path: Path = field(
        default_factory=lambda: Path.home() / "scripts" / "agent-skills-update.log"
    )
    backup_path: Path = field(
        default_factory=lambda: Path.home() / ".agent-skills-updater" / "backups"
    )
    keep_backups: int = 5

    # Security
    allowed_hosts: list[str] = field(default_factory=list)

    # Repositories
    repositories: list[RepoConfig] = field(default_factory=list)

    # Path to the config file itself (for updating allowedHosts)
    config_file_path: Path | None = None

    @property
    def skill_target_paths(self) -> list[Path]:
        """Return all paths where skills should be installed."""
        return [self.global_skills_path, self.windsurf_skills_path]


class ConfigError(Exception):
    """Raised when the configuration is invalid."""


def _find_config_file(config_path: Path | None = None) -> Path | None:
    """Locate the config file.

    Search order:
    1. Explicit path (if provided)
    2. Current working directory
    3. Platform config directory (~/.config/agent-skills-updater/ or AppData)
    4. Home directory
    """
    if config_path is not None:
        if config_path.is_file():
            return config_path
        raise ConfigError(f"Config file not found: {config_path}")

    search_dirs = [
        Path.cwd(),
        _default_config_dir(),
        Path.home(),
    ]

    for search_dir in search_dirs:
        for name in _DEFAULT_CONFIG_NAMES:
            candidate = search_dir / name
            if candidate.is_file():
                return candidate

    return None


def _parse_settings(raw: dict[str, Any]) -> dict[str, Any]:
    """Parse the settings section of the config."""
    result: dict[str, Any] = {}

    path_keys = {
        "globalSkillsPath": "global_skills_path",
        "windsurfSkillsPath": "windsurf_skills_path",
        "tempPath": "temp_path",
        "logPath": "log_path",
        "backupPath": "backup_path",
    }

    for yaml_key, attr_name in path_keys.items():
        if yaml_key in raw:
            result[attr_name] = _expand_path(raw[yaml_key])

    if "keepBackups" in raw:
        result["keep_backups"] = int(raw["keepBackups"])

    if "allowedHosts" in raw:
        hosts = raw["allowedHosts"]
        if isinstance(hosts, list):
            result["allowed_hosts"] = [str(h) for h in hosts]

    return result


def _parse_repositories(raw: dict[str, Any]) -> list[RepoConfig]:
    """Parse the repositories section of the config."""
    repos: list[RepoConfig] = []

    if not isinstance(raw, dict):
        return repos

    for repo_name, repo_data in raw.items():
        if not isinstance(repo_data, dict):
            raise ConfigError(
                f"Repository '{repo_name}': expected a mapping, got {type(repo_data).__name__}"
            )

        url = repo_data.get("url")
        if not url:
            raise ConfigError(f"Repository '{repo_name}': 'url' is required")

        skills = repo_data.get("skills", [])
        if not isinstance(skills, list):
            raise ConfigError(f"Repository '{repo_name}': 'skills' must be a list")

        repos.append(
            RepoConfig(
                name=repo_name,
                url=str(url),
                skills=[str(s) for s in skills],
                branch=repo_data.get("branch"),
                structure=repo_data.get("structure", "standard"),
            )
        )

    return repos


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load application config from YAML file.

    Returns sensible defaults if no config file is found.
    """
    found_path = _find_config_file(config_path)

    if found_path is None:
        return AppConfig()

    try:
        text = found_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file: {exc}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in config file: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a YAML mapping at the top level")

    # Parse settings
    settings_raw = data.get("settings", {})
    if not isinstance(settings_raw, dict):
        raise ConfigError("'settings' must be a mapping")
    settings = _parse_settings(settings_raw)

    # Parse repositories
    repos_raw = data.get("repositories", {})
    repositories = _parse_repositories(repos_raw)

    return AppConfig(
        **settings,
        repositories=repositories,
        config_file_path=found_path,
    )


def save_allowed_host(config: AppConfig, host: str) -> None:
    """Add a host to allowedHosts in the config file.

    This is called when a user selects 'Allow always' for a non-GitHub host.
    """
    if config.config_file_path is None:
        return

    if host in config.allowed_hosts:
        return

    config.allowed_hosts.append(host)

    try:
        text = config.config_file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
    except (OSError, yaml.YAMLError):
        return

    if "settings" not in data:
        data["settings"] = {}

    data["settings"]["allowedHosts"] = config.allowed_hosts

    try:
        config.config_file_path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
    except OSError:
        pass
