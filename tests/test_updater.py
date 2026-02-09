"""Tests for the self-update / version check module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agent_skills_updater.updater import (
    _version_tuple,
    check_for_update,
    run_self_update,
)


class TestVersionTuple:
    def test_simple(self):
        assert _version_tuple("0.1.8") == (0, 1, 8)

    def test_two_part(self):
        assert _version_tuple("1.0") == (1, 0)

    def test_prerelease_truncated(self):
        assert _version_tuple("1.2.3rc1") == (1, 2)

    def test_comparison(self):
        assert _version_tuple("0.2.0") > _version_tuple("0.1.9")
        assert _version_tuple("1.0.0") > _version_tuple("0.99.99")
        assert _version_tuple("0.1.8") == _version_tuple("0.1.8")


class TestCheckForUpdate:
    @patch("agent_skills_updater.updater.requests.get")
    def test_newer_version_available(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"info": {"version": "99.0.0"}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        current, latest, needs_update = check_for_update()

        assert latest == "99.0.0"
        assert needs_update is True

    @patch("agent_skills_updater.updater.requests.get")
    def test_already_up_to_date(self, mock_get):
        from agent_skills_updater import __version__

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"info": {"version": __version__}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        current, latest, needs_update = check_for_update()

        assert current == __version__
        assert latest == __version__
        assert needs_update is False

    @patch("agent_skills_updater.updater.requests.get")
    def test_network_error_returns_safe_default(self, mock_get):
        mock_get.side_effect = Exception("network down")

        current, latest, needs_update = check_for_update()

        assert latest is None
        assert needs_update is False

    @patch("agent_skills_updater.updater.requests.get")
    def test_timeout_returns_safe_default(self, mock_get):
        import requests

        mock_get.side_effect = requests.Timeout("timed out")

        current, latest, needs_update = check_for_update()

        assert latest is None
        assert needs_update is False


class TestRunSelfUpdate:
    @patch("agent_skills_updater.updater.check_for_update")
    def test_already_up_to_date(self, mock_check):
        from agent_skills_updater import __version__

        mock_check.return_value = (__version__, __version__, False)

        success, message = run_self_update()

        assert success is True
        assert "Already up to date" in message

    @patch("agent_skills_updater.updater.check_for_update")
    def test_pypi_unreachable(self, mock_check):
        mock_check.return_value = ("0.1.8", None, False)

        success, message = run_self_update()

        assert success is False
        assert "Could not reach PyPI" in message

    @patch("agent_skills_updater.updater.subprocess.run")
    @patch("agent_skills_updater.updater.check_for_update")
    def test_successful_update(self, mock_check, mock_run):
        mock_check.return_value = ("0.1.8", "0.2.0", True)
        mock_run.return_value = MagicMock(returncode=0)

        success, message = run_self_update()

        assert success is True
        assert "0.1.8" in message
        assert "0.2.0" in message

    @patch("agent_skills_updater.updater.subprocess.run")
    @patch("agent_skills_updater.updater.check_for_update")
    def test_pip_failure(self, mock_check, mock_run):
        mock_check.return_value = ("0.1.8", "0.2.0", True)
        mock_run.return_value = MagicMock(returncode=1, stderr="error msg")

        success, message = run_self_update()

        assert success is False
        assert "error msg" in message
