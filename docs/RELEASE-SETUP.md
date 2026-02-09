# Release Setup Guide

This guide walks you through setting up PyPI trusted publishing and running your first integration test.

> **Version**: Before creating a release, check the current version in `pyproject.toml` (line 7) or run `python -c "import agent_skills_updater; print(agent_skills_updater.__version__)"`. Use that version wherever `{VERSION}` appears below.

---

## Step 1: Create a PyPI Account (if needed)

1. Go to [https://pypi.org/account/register/](https://pypi.org/account/register/)
2. Create an account or log in
3. Enable 2FA (required for trusted publishing)

---

## Step 2: Set Up Trusted Publishing on PyPI

Trusted publishing lets GitHub Actions publish packages **without API tokens** — PyPI verifies the request came from your repo.

1. Go to [https://pypi.org/manage/account/publishing/](https://pypi.org/manage/account/publishing/)
2. Scroll to **"Add a new pending publisher"**
3. Fill in:
   - **PyPI project name**: `agent-skills-updater`
   - **Owner**: `BallLightningAB`
   - **Repository name**: `agent-skills-updater`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`
4. Click **"Add"**

> This creates a "pending publisher" — it will activate automatically the first time your workflow publishes.

---

## Step 3: Create the GitHub Environment

GitHub environments add a layer of protection — only the `publish.yml` workflow running in the `pypi` environment can trigger a release.

1. Go to [https://github.com/BallLightningAB/agent-skills-updater/settings/environments](https://github.com/BallLightningAB/agent-skills-updater/settings/environments)
2. Click **"New environment"**
3. Name it exactly: **`pypi`**
4. Click **"Configure environment"**
5. *(Optional but recommended)* Under **"Environment protection rules"**:
   - Enable **"Required reviewers"** and add yourself — this means you'll need to manually approve each PyPI publish
   - This prevents accidental releases
6. Click **"Save protection rules"**

---

## Step 4: Create Your First Release

Once Steps 2 and 3 are done, you can publish to PyPI:

1. Go to [https://github.com/BallLightningAB/agent-skills-updater/releases/new](https://github.com/BallLightningAB/agent-skills-updater/releases/new)
2. Click **"Choose a tag"** → type `v{VERSION}` → click **"Create new tag: v{VERSION} on publish"**
3. **Release title**: `Agent Skills Updater v{VERSION} — Keep Your AI Coding Skills in Sync`
4. **Description** (suggested):
   ```
   # Agent Skills Updater v{VERSION}

   **One command to keep all your AI coding skills up-to-date.**

   If you use AI coding assistants like Windsurf, Cursor, Claude Code, GitHub Copilot, or any of the 40+ IDEs and agentic tools that support skills — you've probably noticed that keeping skill files in sync across tools and machines is a pain. This tool fixes that.

   Agent Skills Updater pulls skills from any Git repository, handles four different repo structures automatically, and copies them to the right places. Configure once with a simple YAML file, then run a single command whenever you want to update or use a scheduler.

   ## Install

   ```bash
   pip install agent-skills-updater
   ```

   ## What's New in v{VERSION}

   - **Multi-source skill management** — Pull skills from any number of Git repositories with a single command
   - **Works with 40+ IDEs** — Windsurf, Cursor, Claude Code, GitHub Copilot, Opencode, Cline, Roo Code, and many more
   - **Structure-aware** — Automatically handles standard, root, template, and multi-skill repo layouts
   - **Safe by default** — Dry-run mode, automatic backups before every update, and one-command rollback
   - **Lockfile tracking** — Atomic writes to `.skill-lock.json` with precise UTC timestamps, so you always know what's installed and when
   - **Security built in** — GitHub repos work out of the box; other hosts require explicit approval via an interactive allowlist
   - **Cross-platform** — Windows, macOS, Linux. Python 3.12+
   - **CI-friendly** — `--trust-all` flag for automation, `--json` output for scripting

   ## Quick Start

   ```bash
   # Install
   pip install agent-skills-updater

   # Preview what would change
   agent-skills-update --dry-run --verbose

   # Update all skills
   agent-skills-update

   # Update specific skills only
   agent-skills-update --skills copywriting,seo-audit

   # Roll back if something goes wrong
   agent-skills-update rollback
   ```

   ## Why This Exists

   AI skills are becoming a core part of how developers work with coding assistants — but the ecosystem is fragmented. Skills live across dozens of repos with different structures, and there's no standard way to keep them updated. This tool brings order to that.

   Built by [Nicolas Brulay](https://github.com/BallLightningAB) of [Ball Lightning AB](https://balllightning.cloud) as part of the open-source tooling around AI-assisted development. Follow the build journey on [The Builder Coil](https://thebuildercoil.com) and support me on [Ko-fi](https://ko-fi.com/balllightning) if you like what I'm building.

   ## Links

   - **GitHub**: https://github.com/BallLightningAB/agent-skills-updater
   - **PyPI**: https://pypi.org/project/agent-skills-updater/
   - **Discover skills**: https://skills.sh
   - **Apache-2.0 licensed**
   ```
5. Click **"Publish release"**
6. Go to the **Actions** tab to watch the `Publish to PyPI` workflow run
7. If you set up required reviewers, you'll need to approve the deployment

---

## Step 5: Verify the Installation

After the PyPI workflow succeeds (usually takes 1-2 minutes):

```powershell
# Install from PyPI (in a fresh terminal or venv)
pip install agent-skills-updater

# Verify CLI works
agent-skills-update --version
# Should print: agent-skills-update, version {VERSION}

agent-skills-update --help
# Should show all commands and options
```

---

## Step 6: Integration Test with Real Skill Repos

Test with your actual skill configuration to make sure everything works end-to-end.

### 6a. Create a test config

Create a file `agent-skills-config.yaml` in your home directory (`~` or `%USERPROFILE%`):

```yaml
settings:
  globalSkillsPath: ~/test-skills-output
  keepBackups: 3

repositories:
  # Use a public skills repo you trust for testing
  BallLightningAB/windsurf-skills:
    url: https://github.com/BallLightningAB/windsurf-skills.git
    skills:
      - copywriting
      - seo-audit
    branch: main
    structure: standard
```

> **Adjust the repository URL and skill names** to match a real skills repo you have access to.

### 6b. Dry-run first (safe, no changes)

```powershell
agent-skills-update --config ~/agent-skills-config.yaml --dry-run --verbose
```

This will:
- Load the config
- Clone the repo to a temp directory
- Show which skills would be installed
- **NOT** actually copy anything

### 6c. Real install

```powershell
agent-skills-update --config ~/agent-skills-config.yaml --verbose
```

### 6d. Verify results

```powershell
# Check installed skills
agent-skills-update list --config ~/agent-skills-config.yaml

# Check lockfile was created
Get-Content ~/test-skills-output/../.skill-lock.json

# Check backups
agent-skills-update list-backups --config ~/agent-skills-config.yaml
```

### 6e. Test rollback

```powershell
# Run update again with --force to create a new backup
agent-skills-update --config ~/agent-skills-config.yaml --force --verbose

# Rollback to previous state
agent-skills-update rollback --config ~/agent-skills-config.yaml --verbose
```

### 6f. Test JSON output (for CI/automation)

```powershell
agent-skills-update list --config ~/agent-skills-config.yaml --json
```

---

## Cleanup

After testing, remove the test output:

```powershell
Remove-Item -Recurse -Force ~/test-skills-output
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| PyPI workflow fails with "publisher not found" | Double-check the workflow name is exactly `publish.yml` and environment is exactly `pypi` in both PyPI and GitHub settings |
| `pip install` shows old version | Wait 1-2 min for PyPI CDN to update, then `pip install --no-cache-dir agent-skills-updater` |
| Git clone fails in integration test | Ensure the repo URL is correct and accessible (public or with credentials) |
| Permission denied on skill path | Run terminal as admin, or choose a path you have write access to |
