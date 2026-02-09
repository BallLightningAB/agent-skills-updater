# Release Setup Guide

This guide walks you through setting up PyPI trusted publishing and running your first integration test.

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
2. Click **"Choose a tag"** → type `v0.1.3` → click **"Create new tag: v0.1.3 on publish"**
3. **Release title**: `v0.1.3 — Python Rewrite`
4. **Description** (suggested):
   ```
   # Agent Skills Updater v0.1.3

   Automated skill management for AI coding assistants. Keep your agent skills up-to-date across **Windsurf**, **Cursor**, **Claude Code**, **GitHub Copilot**, **Opencode**, and other AI-powered IDEs.

   ## What's New in v0.1.3
   - **Complete Python rewrite** (replaces PowerShell version)
   - **Cross-platform**: Windows, macOS, Linux
   - **Easy install**: `pip install agent-skills-updater`
   - **Rich CLI**: dry-run, force, JSON output, verbose mode
   - **Smart downloads**: Git clone with archive fallback
   - **Security**: Interactive allowlist for non-GitHub hosts
   - **Flexible repos**: Supports 4 repository structures
   - **Atomic operations**: Lockfile with UTC timestamps
   - **Safe updates**: Timestamped backups with rollback
   - **Production ready**: 44 tests, CI on 3 OS × 2 Python versions

   ## Quick Start
   ```bash
   pip install agent-skills-updater
   agent-skills-update --help
   ```

   ## Migration from PowerShell
   The original PowerShell version is preserved in the `legacy/` folder. Your existing `agent-skills-config.yaml` files are fully compatible with the Python version.
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
# Should print: agent-skills-update, version 0.1.3

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
