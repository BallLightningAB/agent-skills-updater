"""CLI entry point for agent-skills-updater."""

import click

from agent_skills_updater import __version__


@click.command()
@click.version_option(version=__version__, prog_name="agent-skills-update")
def main() -> None:
    """Automated skill management for AI coding assistants."""
    click.echo("agent-skills-update is not yet implemented.")


if __name__ == "__main__":
    main()
