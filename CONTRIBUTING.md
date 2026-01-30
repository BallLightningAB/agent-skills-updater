# Contributing to Agent Skills Updater

Thank you for your interest in contributing!

## How to Contribute

### Reporting Issues

- Check existing issues before creating a new one
- Include your PowerShell version (`$PSVersionTable.PSVersion`)
- Include your OS and version
- Provide steps to reproduce the issue

### Adding New Skill Repositories

If you know of a public skill repository that should be included in the default config:

1. Fork the repository
2. Add the repository to `agent-skills-config.example.yaml`
3. Test that the skills sync correctly
4. Submit a pull request with:
   - The repository URL
   - Which skills it contains
   - Any special structure requirements (`root`, `template`, `multi`)

### Code Contributions

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Test on your platform (Windows/macOS/Linux)
5. Submit a pull request

### Code Style

- Follow existing PowerShell conventions
- Use `Write-Log` for all output
- Keep cross-platform compatibility in mind
- Test with both PowerShell 5.1 (Windows) and PowerShell 7+ (cross-platform)

## Development Setup

```powershell
# Clone your fork
git clone https://github.com/YOUR-USERNAME/agent-skills-updater.git
cd agent-skills-updater

# Copy config
cp agent-skills-config.example.yaml agent-skills-config.yaml

# Test the script
.\agent-skills-update.ps1 -Force
```

## Questions?

Open an issue or reach out to Nicolas Brulay of [Ball Lightning AB](https://github.com/BallLightningAB).
