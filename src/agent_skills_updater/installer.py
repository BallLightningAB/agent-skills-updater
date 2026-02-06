"""Skill installation logic supporting multiple repo structures."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_skills_updater.cli import Context
    from agent_skills_updater.config import AppConfig, RepoConfig
    from agent_skills_updater.downloader import DownloadResult


@dataclass
class InstalledSkill:
    """Record of a single installed skill."""

    name: str
    source: str
    source_url: str
    skill_path: str
    installed_at: str = field(default_factory=lambda: "")
    updated_at: str = field(default_factory=lambda: "")

    def __post_init__(self) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if not self.installed_at:
            self.installed_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "source": self.source,
            "sourceUrl": self.source_url,
            "skillPath": self.skill_path,
            "installedAt": self.installed_at,
            "updatedAt": self.updated_at,
        }


def _find_skill_dir_standard(repo_path: Path, skill_name: str) -> Path | None:
    """Find a skill in standard structure: skills/<name>/ or src/skills/<name>/."""
    candidates = [
        repo_path / "skills" / skill_name,
        repo_path / "src" / "skills" / skill_name,
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _find_skill_dir_root(repo_path: Path, skill_name: str) -> Path | None:
    """Find a skill in root structure: SKILL.md in repo root."""
    if (repo_path / "SKILL.md").is_file():
        return repo_path
    return None


def _find_skill_dir_template(repo_path: Path, skill_name: str) -> Path | None:
    """Find a skill in template structure: template/ subdirectory."""
    template_dir = repo_path / "template"
    if template_dir.is_dir():
        return template_dir
    return None


def _find_skill_dir_multi(repo_path: Path, skill_name: str) -> Path | None:
    """Find a skill in multi structure: subdirectories with SKILL.md each."""
    candidate = repo_path / skill_name
    if candidate.is_dir() and (candidate / "SKILL.md").is_file():
        return candidate

    # Also check direct subdirectories for SKILL.md
    for subdir in repo_path.iterdir():
        if subdir.is_dir() and subdir.name == skill_name:
            if (subdir / "SKILL.md").is_file():
                return subdir

    return None


_STRUCTURE_FINDERS = {
    "standard": _find_skill_dir_standard,
    "root": _find_skill_dir_root,
    "template": _find_skill_dir_template,
    "multi": _find_skill_dir_multi,
}


def _copy_skill(
    source_dir: Path,
    target_dir: Path,
    skill_name: str,
    force: bool,
    dry_run: bool,
    ctx: Context,
) -> bool:
    """Copy a skill directory to the target location.

    Returns True if the skill was copied (or would be in dry-run).
    """
    dest = target_dir / skill_name

    if dest.exists() and not force:
        if ctx.verbose:
            ctx.console.print(f"    [dim]Skipped {dest} (exists, use --force)[/]")
        return False

    if dry_run:
        action = "overwrite" if dest.exists() else "install"
        ctx.console.print(f"    [dim]Would {action}: {dest}[/]")
        return True

    # Ensure parent directory exists
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing if force
    if dest.exists():
        shutil.rmtree(dest)

    shutil.copytree(source_dir, dest)
    return True


def install_skills(
    config: AppConfig,
    results: list[DownloadResult],
    ctx: Context,
    skill_filter: list[str] | None = None,
) -> list[InstalledSkill]:
    """Install skills from downloaded repositories to target directories.

    Returns list of InstalledSkill records for lockfile tracking.
    """
    installed: list[InstalledSkill] = []

    for result in results:
        if not result.success:
            continue

        repo = result.repo
        finder = _STRUCTURE_FINDERS.get(repo.structure)
        if finder is None:
            ctx.console.print(
                f"  [red]Unknown structure '{repo.structure}' for {repo.name}[/]"
            )
            continue

        skills_to_install = repo.skills
        if skill_filter:
            skills_to_install = [s for s in repo.skills if s in skill_filter]

        if not skills_to_install:
            continue

        for skill_name in skills_to_install:
            skill_dir = finder(result.local_path, skill_name)

            if skill_dir is None:
                if ctx.verbose:
                    ctx.console.print(
                        f"    [yellow]Skill '{skill_name}' not found in {repo.name}[/]"
                    )
                continue

            any_copied = False
            for target_path in config.skill_target_paths:
                if not target_path.is_dir():
                    continue
                try:
                    copied = _copy_skill(
                        skill_dir,
                        target_path,
                        skill_name,
                        force=ctx.force,
                        dry_run=ctx.dry_run,
                        ctx=ctx,
                    )
                    if copied:
                        any_copied = True
                except PermissionError as exc:
                    ctx.console.print(
                        f"    [red]Permission denied:[/] {exc}"
                    )
                except OSError as exc:
                    ctx.console.print(
                        f"    [red]Error copying {skill_name}:[/] {exc}"
                    )

            if any_copied:
                installed.append(
                    InstalledSkill(
                        name=skill_name,
                        source=repo.name,
                        source_url=repo.url,
                        skill_path=str(skill_dir.relative_to(result.local_path)),
                    )
                )

    return installed
