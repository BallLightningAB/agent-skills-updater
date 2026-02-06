"""CLI entry point for agent-skills-updater."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console

from agent_skills_updater import __version__

if TYPE_CHECKING:
    from agent_skills_updater.config import AppConfig


class Context:
    """Shared CLI context passed to all commands."""

    def __init__(
        self,
        *,
        config_path: Path | None = None,
        dry_run: bool = False,
        force: bool = False,
        verbose: bool = False,
        trust_all: bool = False,
        json_output: bool = False,
    ) -> None:
        self.config_path = config_path
        self.dry_run = dry_run
        self.force = force
        self.verbose = verbose
        self.trust_all = trust_all
        self.json_output = json_output
        self.console = Console(quiet=json_output)
        self.config: AppConfig | None = None

    def load_config(self) -> AppConfig:
        """Load and cache the application config."""
        if self.config is None:
            from agent_skills_updater.config import load_config

            self.config = load_config(self.config_path)
        return self.config


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="agent-skills-update")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to YAML config file.",
)
@click.option("--dry-run", is_flag=True, help="Preview changes without applying them.")
@click.option("--force", is_flag=True, help="Overwrite existing skills.")
@click.option("--verbose", is_flag=True, help="Show detailed output.")
@click.option(
    "--trust-all", is_flag=True, help="Trust all repository hosts (skip prompts, for CI)."
)
@click.option("--json", "json_output", is_flag=True, help="Machine-readable JSON output.")
@click.option(
    "--skills",
    default=None,
    help="Comma-separated list of specific skills to update.",
)
@click.pass_context
def main(
    ctx: click.Context,
    config_path: Path | None,
    dry_run: bool,
    force: bool,
    verbose: bool,
    trust_all: bool,
    json_output: bool,
    skills: str | None,
) -> None:
    """Automated skill management for AI coding assistants.

    \b
    Examples:
      agent-skills-update                  Update all skills
      agent-skills-update --dry-run        Preview changes
      agent-skills-update --force          Overwrite existing skills
      agent-skills-update --skills a,b     Update specific skills only
      agent-skills-update list             Show installed skills
      agent-skills-update rollback <name>  Restore a skill from backup
    """
    ctx.ensure_object(Context)
    app_ctx = Context(
        config_path=config_path,
        dry_run=dry_run,
        force=force,
        verbose=verbose,
        trust_all=trust_all,
        json_output=json_output,
    )
    ctx.obj = app_ctx

    if ctx.invoked_subcommand is not None:
        return

    # Default action: update skills
    _run_update(app_ctx, skills)


def _run_update(ctx: Context, skills: str | None) -> None:
    """Execute the default update action."""
    skill_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None

    config = ctx.load_config()

    if ctx.dry_run:
        ctx.console.print("[bold yellow]Dry run mode[/] — no changes will be made.")

    if ctx.verbose:
        ctx.console.print(f"[dim]Config: {ctx.config_path or 'default'}[/]")
        if skill_list:
            ctx.console.print(f"[dim]Skills filter: {', '.join(skill_list)}[/]")

    from agent_skills_updater.downloader import download_repos
    from agent_skills_updater.installer import install_skills
    from agent_skills_updater.lockfile import load_lockfile, save_lockfile

    lockfile = load_lockfile(config)

    if not ctx.dry_run:
        from agent_skills_updater.backup import create_backup

        create_backup(config, lockfile)

    results = download_repos(config, ctx)
    installed = install_skills(config, results, ctx, skill_filter=skill_list)

    if not ctx.dry_run:
        for entry in installed:
            lockfile.update_entry(entry)
        save_lockfile(config, lockfile)

    if ctx.json_output:
        import json

        print(json.dumps({"updated": [e.to_dict() for e in installed]}, indent=2))
    else:
        if installed:
            ctx.console.print(f"\n[bold green]Updated {len(installed)} skill(s).[/]")
        else:
            ctx.console.print("\n[dim]No skills were updated.[/]")


@main.command()
@pass_context
def list(ctx: Context) -> None:
    """Show installed skills from the lockfile."""
    config = ctx.load_config()

    from agent_skills_updater.lockfile import load_lockfile

    lockfile = load_lockfile(config)

    if ctx.json_output:
        import json

        print(json.dumps(lockfile.to_dict(), indent=2))
        return

    entries = lockfile.entries
    if not entries:
        ctx.console.print("[dim]No skills installed.[/]")
        return

    from rich.table import Table

    table = Table(title="Installed Skills")
    table.add_column("Skill", style="bold cyan")
    table.add_column("Source")
    table.add_column("Installed")
    table.add_column("Updated")

    for name, entry in sorted(entries.items()):
        table.add_row(
            name,
            entry.get("source", "—"),
            entry.get("installedAt", "—"),
            entry.get("updatedAt", "—"),
        )

    ctx.console.print(table)


@main.command()
@click.argument("skill", required=False, default=None)
@pass_context
def rollback(ctx: Context, skill: str | None) -> None:
    """Restore a skill (or all skills) from the latest backup.

    \b
    Examples:
      agent-skills-update rollback              Roll back all skills
      agent-skills-update rollback copywriting  Roll back a specific skill
    """
    config = ctx.load_config()

    from agent_skills_updater.backup import restore_backup

    if ctx.dry_run:
        ctx.console.print("[bold yellow]Dry run mode[/] — no changes will be made.")

    success = restore_backup(config, ctx, skill_name=skill)

    if success:
        label = f"skill '{skill}'" if skill else "all skills"
        ctx.console.print(f"[bold green]Rolled back {label} from backup.[/]")
    else:
        ctx.console.print("[bold red]Rollback failed.[/] No suitable backup found.")
        sys.exit(1)


@main.command("list-backups")
@pass_context
def list_backups(ctx: Context) -> None:
    """Show available backups."""
    config = ctx.load_config()

    from agent_skills_updater.backup import list_backups as _list_backups

    backups = _list_backups(config)

    if ctx.json_output:
        import json

        print(json.dumps([b.to_dict() for b in backups], indent=2))
        return

    if not backups:
        ctx.console.print("[dim]No backups available.[/]")
        return

    from rich.table import Table

    table = Table(title="Available Backups")
    table.add_column("Timestamp", style="bold cyan")
    table.add_column("Skills")
    table.add_column("Path")

    for backup in backups:
        table.add_row(
            backup.timestamp,
            str(backup.skill_count),
            str(backup.path),
        )

    ctx.console.print(table)


if __name__ == "__main__":
    main()
