# Agent Skills Updater

![Version](https://img.shields.io/badge/version-1.0.1-blue.svg)
![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)
![PowerShell](https://img.shields.io/badge/powershell-5.1%2B-blue.svg)

Automated skill management for AI coding assistants. Keep your agent skills up-to-date across **Windsurf**, **Cursor**, **Claude Code**, **GitHub Copilot**, **Opencode**, **Moltbot**, other AI-powered IDEs and Agentic tools.

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

Keeping these updated manually is tedious. This script automates the process.

## Features

- **Multi-source updates** — Clone skills from any public GitHub repository
- **Structure-aware** — Handles root, template, multi-skill, and standard repo layouts
- **Branch support** — Clone from specific branches (e.g., `canary`, `main`)
- **Lockfile tracking** — Maintains `.skill-lock.json` with install/update timestamps
- **Configurable** — External YAML config for easy customization
- **Schedulable** — Run manually or via Task Scheduler / cron
- **List installed** — See what skills you currently have installed
- **Dry-run mode** — Preview changes before applying them (`-WhatIf`)

## Repository Structure

```
agent-skills-updater/
├── .gitignore                         # Excludes user config and logs
├── CONTRIBUTING.md                    # Contribution guidelines
├── LICENSE                            # Apache-2.0 license
├── README.md                          # This file
├── VERSION                            # Version number (v1.0.0)
├── agent-skills-config.example.yaml   # Template config (copy to customize)
└── agent-skills-update.ps1            # Main PowerShell script
```

## Quick Start

### 1. Clone this repository

```bash
git clone https://github.com/BallLightningAB/agent-skills-updater.git
cd agent-skills-updater
```

### 2. Copy and customize the config

```bash
cp agent-skills-config.example.yaml agent-skills-config.yaml
```

Edit `agent-skills-config.yaml` to add/remove skill repositories.

### 3. Run the script

**Windows (PowerShell 5.1+):**
```powershell
.\agent-skills-update.ps1
```

**macOS/Linux (PowerShell 7+):**
```bash
pwsh ./agent-skills-update.ps1
```

## Configuration

### `agent-skills-config.yaml`

```yaml
settings:
  globalSkillsPath: ~/.agents/skills
  windsurfSkillsPath: ~/.codeium/windsurf/skills
  tempPath: ~/.temp-agent-skills-update
  logPath: ~/scripts/agent-skills-update.log

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

## Usage

```powershell
# Update all skills
.\agent-skills-update.ps1

# Force overwrite existing skills
.\agent-skills-update.ps1 -Force

# Update specific skills only
.\agent-skills-update.ps1 -SpecificSkills copywriting,seo-audit

# Show installed skills
.\agent-skills-update.ps1 -List

# Dry run (show what would be updated)
.\agent-skills-update.ps1 -WhatIf

# Mark as scheduled run (for logging)
.\agent-skills-update.ps1 -Scheduled
```

## Scheduling Updates

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task → Name it "Agent Skills Update"
3. Trigger: Daily or Weekly
4. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\agent-skills-update.ps1" -Scheduled`
5. Finish

### macOS/Linux (cron)

```bash
# Edit crontab
crontab -e

# Add weekly update (Sundays at 3am)
0 3 * * 0 pwsh /path/to/agent-skills-update.ps1 -Scheduled
```

## Supported IDEs

The script copies skills to these locations by default:

| IDE | Default Path |
|-----|--------------|
| Generic agents | `~/.agents/skills` |
| Windsurf | `~/.codeium/windsurf/skills` |

Add more paths in `agent-skills-config.yaml` under `settings`.

### Complete list of supported IDEs as per 2026-01-30

| IDE            | Default Path                          |
| -------------- | ------------------------------------- |
| Generic agents | `~/.config/agents/skills`             |
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

- **Windows**: PowerShell 5.1+ (built-in)
- **macOS/Linux**: Requires [PowerShell 7+](https://docs.microsoft.com/en-us/powershell/scripting/install/installing-powershell)
- Paths use `~` which expands correctly on all platforms
- Git must be installed and available in PATH

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

## Version History

### v1.0.0 (2026-01-30)
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
