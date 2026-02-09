# Agent Skills Updater

![Version](https://img.shields.io/badge/version-0.1.10-blue.svg)
![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)

Automated skill management for AI coding assistants. Keep your agent skills up-to-date across **Windsurf**, **Cursor**, **Claude Code**, **GitHub Copilot**, **Opencode**, other AI-powered IDEs and Agentic tools.

> **🚧 Python rewrite in progress.** The original PowerShell version is available in the [`legacy/`](legacy/) folder. See [Legacy PowerShell Version](#legacy-powershell-version) below.

**Project Board**: Track development and future releases at [GitHub Project](https://github.com/users/BallLightningAB/projects/7)

## What Are Skills?

Skills are markdown files that provide context, instructions, and capabilities to AI coding assistants. They extend your AI's knowledge with specific expertise like SEO optimization, copywriting, frontend design, and more.

- **Discover skills**: [skills.sh](https://skills.sh/) — Browse and search the ecosystem of available skills
- **Windsurf skills guide**: [docs.windsurf.com/windsurf/cascade/skills](https://docs.windsurf.com/windsurf/cascade/skills) — Learn how skills work in Windsurf (and other IDEs)
- **Manual installation**: Skills are typically installed via your IDE's skill manager or by copying to the appropriate directory (see [Supported IDEs](#supported-ides))

## The Problem

AI coding assistants use "skills" (markdown files with context and instructions) to extend their capabilities. These skills come from various GitHub repositories with different structures:

- Skills in `skills/<name>/SKILL.md`
- Skills in repository root
- Skills in `template/` subdirectories
- Multiple skills in subdirectories

Keeping these updated manually is tedious. This tool automates the process.

## Features

- **Multi-source updates** — Clone skills from any public Git repository
- **Structure-aware** — Handles root, template, multi-skill, and standard repo layouts
- **Branch support** — Clone from specific branches (e.g., `canary`, `main`)
- **Lockfile tracking** — Maintains `.skill-lock.json` with install/update timestamps
- **Configurable** — External YAML config for easy customization
- **Schedulable** — Run manually or via Task Scheduler / cron
- **List installed** — See what skills you currently have installed
- **Dry-run mode** — Preview changes before applying them
- **Backup & rollback** — Automatic backups before updates with restore support
- **Security** — Interactive allowlist for non-GitHub repository hosts

## Repository Structure

```
agent-skills-updater/
├── pyproject.toml                     # Python package config
├── README.md                          # This file
├── CONTRIBUTING.md                    # Contribution guidelines
├── LICENSE                            # Apache-2.0 license
├── .gitignore
├── src/
│   └── agent_skills_updater/
│       ├── __init__.py                # Package version
│       ├── cli.py                     # Click-based CLI
│       ├── config.py                  # YAML config loading
│       ├── downloader.py              # Git clone + archive fallback
│       ├── installer.py               # Skill installation logic
│       ├── lockfile.py                # Lockfile management
│       └── backup.py                  # Backup and rollback
├── tests/
│   ├── conftest.py
│   └── ...
└── legacy/
    ├── agent-skills-update.ps1        # Original PowerShell script
    └── agent-skills-config.example.yaml
```

## Quick Start

### Installation

```bash
pip install agent-skills-updater
```

Or install from source:

```bash
git clone https://github.com/BallLightningAB/agent-skills-updater.git
cd agent-skills-updater
pip install -e ".[dev]"
```

### Usage

```bash
# Update all skills
agent-skills-update

# Force overwrite existing skills
agent-skills-update --force

# Update specific skills only
agent-skills-update --skills copywriting,seo-audit

# Show installed skills
agent-skills-update --list

# Dry run (show what would be updated)
agent-skills-update --dry-run

# Verbose output
agent-skills-update --verbose

# Trust all hosts (CI mode, skip prompts)
agent-skills-update --trust-all

# List available backups
agent-skills-update --list-backups

# Roll back a specific skill
agent-skills-update --rollback copywriting

# Roll back all skills to last backup
agent-skills-update --rollback-all

# Machine-readable output (for automation)
agent-skills-update --json

# Custom config path
agent-skills-update --config ~/my-config.yaml
```

## Configuration

### `agent-skills-config.yaml`

```yaml
settings:
  globalSkillsPath: ~/.agents/skills
  windsurfSkillsPath: ~/.codeium/windsurf/skills
  tempPath: ~/.temp-agent-skills-update
  logPath: ~/scripts/agent-skills-update.log
  backupPath: ~/.agent-skills-updater/backups
  keepBackups: 5

  # Auto-updated when user selects "Allow always" for non-GitHub hosts
  allowedHosts:
    - gitlab.com
    - bitbucket.org

repositories:
  coreyhaines31/marketingskills:
    url: https://github.com/coreyhaines31/marketingskills.git
    skills:
      - copywriting
      - seo-audit
      - page-cro

  resend/react-email:
    url: https://github.com/resend/react-email.git
    branch: canary
    skills:
      - react-email
```

### Repository structure types

| Type | Config | Description |
|------|--------|-------------|
| **standard** | (default) | `skills/<name>/SKILL.md` or `src/skills/<name>/SKILL.md` |
| **root** | `structure: root` | `SKILL.md` in repository root |
| **template** | `structure: template` | `SKILL.md` in `template/` subdirectory |
| **multi** | `structure: multi` | Multiple skills as subdirectories with `SKILL.md` each |

## Supported IDEs

The tool copies skills to these locations by default:

| IDE | Default Path |
|-----|--------------|
| Generic agents | `~/.agents/skills` |
| Windsurf | `~/.codeium/windsurf/skills` |
| Amp            | `~/.config/agents/skills`             |
| Kimi Code CLI  | `~/.config/agents/skills`             |
| Antigravity    | `~/.gemini/antigravity/global_skills` |
| Augment        | `~/.augment/rules`                    |
| Claude Code    | `~/.claude/skills`                    |
| OpenClaw       | `~/.moltbot/skills`                   |
| Cline          | `~/.cline/skills`                     |
| CodeBuddy      | `~/.codebuddy/skills`                 |
| Codex          | `~/.codex/skills`                     |
| Command Code   | `~/.commandcode/skills`               |
| Continue       | `~/.continue/skills`                  |
| Crush          | `~/.config/crush/skills`              |
| Cursor         | `~/.cursor/skills`                    |
| Droid          | `~/.factory/skills`                   |
| Gemini CLI     | `~/.gemini/skills`                    |
| GitHub Copilot | `~/.copilot/skills`                   |
| Goose          | `~/.config/goose/skills`              |
| Junie          | `~/.junie/skills`                     |
| iFlow CLI      | `~/.iflow/skills`                     |
| Kilo Code      | `~/.kilocode/skills`                  |
| Kiro CLI       | `~/.kiro/skills`                      |
| Kode           | `~/.kode/skills`                      |
| MCPJam         | `~/.mcpjam/skills`                    |
| Mistral Vibe   | `~/.vibe/skills`                      |
| Mux            | `~/.mux/skills`                       |
| OpenCode       | `~/.config/opencode/skills`           |
| OpenClaude IDE | `~/.openclaude/skills`                |
| OpenHands      | `~/.openhands/skills`                 |
| Pi             | `~/.pi/agent/skills`                  |
| Qoder          | `~/.qoder/skills`                     |
| Qwen Code      | `~/.qwen/skills`                      |
| Replit         | Project-only (no global path)         |
| Roo Code       | `~/.roo/skills`                       |
| Trae           | `~/.trae/skills`                      |
| Trae CN        | `~/.trae-cn/skills`                   |
| Windsurf       | `~/.codeium/windsurf/skills`          |
| Zencoder       | `~/.zencoder/skills`                  |
| Neovate        | `~/.neovate/skills`                   |
| Pochi          | `~/.pochi/skills`                     |
| AdaL           | `~/.adal/skills`                      |

## Cross-Platform Notes

- **Python 3.12+** required
- Paths use `~` which expands correctly on all platforms
- Git must be installed and available in PATH (archive fallback available when git is unavailable)

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

Apache-2.0 — see [LICENSE](LICENSE)

## Credits

Built by Nicolas Brulay of [Ball Lightning AB](https://github.com/BallLightningAB) as part of the Chronomation ecosystem.

Inspired by the growing ecosystem of AI agent skills from:
- [Anthropic](https://github.com/anthropics/skills)
- [Vercel Labs](https://github.com/vercel-labs/agent-skills)
- [Resend](https://github.com/resend)
- Community contributors

## Legacy PowerShell Version

The original PowerShell version (v1.0.2) is available in the [`legacy/`](legacy/) folder. It requires PowerShell 5.1+ (Windows) or PowerShell 7+ (macOS/Linux). See [`legacy/agent-skills-config.example.yaml`](legacy/agent-skills-config.example.yaml) for configuration.

### Migrating from PowerShell

1. Install the Python version: `pip install agent-skills-updater`
2. Your existing `agent-skills-config.yaml` is compatible — no changes needed
3. Run `agent-skills-update` instead of `.\agent-skills-update.ps1`
4. The lockfile format (`.skill-lock.json`) is preserved

## Version History

### v0.1.1 (Python rewrite — in progress)
- Python 3.12+ rewrite with pip installation
- Click-based CLI with `--dry-run`, `--force`, `--verbose`, `--json` flags
- Backup and rollback support
- Interactive security allowlist for non-GitHub repos
- Same YAML config format as PowerShell version

### v1.0.0 (2026-01-30) — PowerShell (legacy)
- Initial release
- Multi-source skill updates from GitHub repositories
- Support for 4 repository structures (standard, root, template, multi)
- Branch-specific cloning
- Lockfile tracking with timestamps
- Cross-platform support (Windows PowerShell 5.1+, PowerShell 7+)
- List installed skills (`-List`)
- Dry-run mode (`-WhatIf`)
- Support for 43+ IDEs and AI coding tools

## Follow Along

This project and other Ball Lightning AB initiatives are documented on **[The Builder Coil](https://thebuildercoil.com)** — a public builder's log covering the journey of building products, tools, and the Chronomation ecosystem.

Subscribe to **[The Upkeep](https://theupkeep.balllightningab.com)** newsletter for weekly updates on new releases, behind-the-scenes insights, and practical tips for developers and solopreneurs.
