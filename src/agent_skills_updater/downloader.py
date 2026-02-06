"""Repository downloading via git clone and archive fallback."""

from __future__ import annotations

import io
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import requests
from rich.progress import Progress, SpinnerColumn, TextColumn

if TYPE_CHECKING:
    from agent_skills_updater.cli import Context
    from agent_skills_updater.config import AppConfig, RepoConfig


@dataclass
class DownloadResult:
    """Result of downloading a single repository."""

    repo: RepoConfig
    local_path: Path
    success: bool
    error: str | None = None


class DownloadError(Exception):
    """Raised when a download fails."""


def _is_git_available() -> bool:
    """Check if git is installed and available on PATH."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _extract_host(url: str) -> str:
    """Extract hostname from a git URL."""
    if url.startswith("git@"):
        # git@github.com:user/repo.git
        return url.split("@")[1].split(":")[0]
    parsed = urlparse(url)
    return parsed.hostname or ""


def _is_github_url(url: str) -> bool:
    """Check if a URL points to GitHub (trusted by default)."""
    host = _extract_host(url)
    return host in ("github.com", "www.github.com")


def _check_host_allowed(url: str, config: AppConfig, ctx: Context) -> bool:
    """Check if the repo host is allowed, prompting the user if needed."""
    if _is_github_url(url):
        return True

    host = _extract_host(url)

    if host in config.allowed_hosts:
        return True

    if ctx.trust_all:
        return True

    # Interactive prompt
    ctx.console.print(
        f"\n[bold yellow]Unknown host:[/] [cyan]{host}[/] "
        f"(from {url})"
    )

    import click

    choice = click.prompt(
        "  Allow this host?",
        type=click.Choice(["once", "always", "deny"], case_sensitive=False),
        default="deny",
    )

    if choice == "deny":
        return False

    if choice == "always":
        from agent_skills_updater.config import save_allowed_host

        save_allowed_host(config, host)
        ctx.console.print(f"  [dim]Added {host} to allowedHosts in config.[/]")

    return True


def _git_clone(repo: RepoConfig, dest: Path, ctx: Context) -> None:
    """Clone a repository using git."""
    cmd = ["git", "clone", "--depth", "1"]

    if repo.branch:
        cmd.extend(["--branch", repo.branch])

    cmd.extend([repo.url, str(dest)])

    if ctx.verbose:
        ctx.console.print(f"  [dim]$ {' '.join(cmd)}[/]")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise DownloadError(f"git clone failed: {stderr}")


def _archive_download(repo: RepoConfig, dest: Path, ctx: Context) -> None:
    """Download repository as ZIP archive (GitHub fallback)."""
    if not _is_github_url(repo.url):
        raise DownloadError(
            f"Archive fallback only supports GitHub URLs, got: {repo.url}"
        )

    # Convert git URL to GitHub archive URL
    # https://github.com/user/repo.git -> https://github.com/user/repo/archive/refs/heads/main.zip
    base_url = repo.url.removesuffix(".git")
    branch = repo.branch or "main"
    archive_url = f"{base_url}/archive/refs/heads/{branch}.zip"

    if ctx.verbose:
        ctx.console.print(f"  [dim]Downloading archive: {archive_url}[/]")

    try:
        response = requests.get(archive_url, timeout=60, stream=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DownloadError(f"Archive download failed: {exc}") from exc

    try:
        zip_data = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_data) as zf:
            zf.extractall(dest)

        # ZIP extracts into a subdirectory like repo-main/, move contents up
        subdirs = [d for d in dest.iterdir() if d.is_dir()]
        if len(subdirs) == 1:
            extracted = subdirs[0]
            for item in extracted.iterdir():
                shutil.move(str(item), str(dest / item.name))
            extracted.rmdir()
    except (zipfile.BadZipFile, OSError) as exc:
        raise DownloadError(f"Failed to extract archive: {exc}") from exc


def _download_one(
    repo: RepoConfig,
    temp_dir: Path,
    config: AppConfig,
    ctx: Context,
    git_available: bool,
) -> DownloadResult:
    """Download a single repository."""
    dest = temp_dir / repo.name.replace("/", "_")

    # Clean up any previous download
    if dest.exists():
        shutil.rmtree(dest)

    try:
        if git_available:
            _git_clone(repo, dest, ctx)
        else:
            _archive_download(repo, dest, ctx)

        return DownloadResult(repo=repo, local_path=dest, success=True)

    except DownloadError as exc:
        # If git failed and this is a GitHub URL, try archive fallback
        if git_available and _is_github_url(repo.url):
            if ctx.verbose:
                ctx.console.print(
                    "  [dim]Git failed, trying archive fallback...[/]"
                )
            try:
                if dest.exists():
                    shutil.rmtree(dest)
                dest.mkdir(parents=True, exist_ok=True)
                _archive_download(repo, dest, ctx)
                return DownloadResult(repo=repo, local_path=dest, success=True)
            except DownloadError as fallback_exc:
                return DownloadResult(
                    repo=repo,
                    local_path=dest,
                    success=False,
                    error=f"Git: {exc} | Archive: {fallback_exc}",
                )

        return DownloadResult(
            repo=repo, local_path=dest, success=False, error=str(exc)
        )

    except subprocess.TimeoutExpired:
        return DownloadResult(
            repo=repo,
            local_path=dest,
            success=False,
            error="Download timed out after 120 seconds",
        )


def download_repos(config: AppConfig, ctx: Context) -> list[DownloadResult]:
    """Download all configured repositories.

    Returns a list of DownloadResult for each repo (success or failure).
    """
    if not config.repositories:
        ctx.console.print("[dim]No repositories configured.[/]")
        return []

    git_available = _is_git_available()
    if not git_available:
        ctx.console.print(
            "[yellow]git not found on PATH.[/] Using archive download fallback."
        )

    # Ensure temp directory exists
    config.temp_path.mkdir(parents=True, exist_ok=True)

    results: list[DownloadResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=ctx.console,
        transient=True,
    ) as progress:
        for repo in config.repositories:
            # Check host security
            if not _check_host_allowed(repo.url, config, ctx):
                ctx.console.print(
                    f"  [red]Skipped[/] {repo.name} (host not allowed)"
                )
                results.append(
                    DownloadResult(
                        repo=repo,
                        local_path=config.temp_path / repo.name.replace("/", "_"),
                        success=False,
                        error="Host not allowed",
                    )
                )
                continue

            task = progress.add_task(f"Downloading {repo.name}...", total=None)
            result = _download_one(repo, config.temp_path, config, ctx, git_available)
            progress.remove_task(task)

            if result.success:
                ctx.console.print(f"  [green]✓[/] {repo.name}")
            else:
                ctx.console.print(
                    f"  [red]✗[/] {repo.name}: {result.error}"
                )

            results.append(result)

    return results
