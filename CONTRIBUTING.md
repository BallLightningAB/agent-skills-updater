# Contributing to Agent Skills Updater

Thank you for your interest in contributing!

## How to Contribute

### Reporting Issues

- Check existing issues before creating a new one
- Include your Python version (`python --version`)
- Include your OS and version
- Provide steps to reproduce the issue

### Adding New Skill Repositories

If you know of a public skill repository that should be included in the default config:

1. Fork the repository
2. Add the repository to `legacy/agent-skills-config.example.yaml`
3. Test that the skills sync correctly
4. Submit a pull request with:
   - The repository URL
   - Which skills it contains
   - Any special structure requirements (`root`, `template`, `multi`)

### Code Contributions

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests: `pytest`
5. Run linter: `ruff check src/ tests/`
6. Test on your platform (Windows/macOS/Linux)
7. Submit a pull request

### Code Style

- Python 3.12+ with type hints
- Format and lint with `ruff`
- Keep cross-platform compatibility in mind
- Use `rich` for terminal output
- Use `click` for CLI arguments

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/agent-skills-updater.git
cd agent-skills-updater

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/ tests/
```

## Questions?

Open an issue or reach out to Nicolas Brulay of [Ball Lightning AB](https://github.com/BallLightningAB).
