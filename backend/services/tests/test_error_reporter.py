"""
Tests for the error reporter.

Tests cover:
- Reading relay settings from arguments and the environment
- Filing a report through the bug relay
- Skipping duplicate and unconfigured reports
- Surviving relay failures
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.error_reporter import ErrorReporter

RELAY_URL = "https://relay.example/"
RELAY_TOKEN = "relay-token"


def _raised(message: str = "boom") -> ValueError:
    """Return a ValueError that carries a real traceback."""
    try:
        raise ValueError(message)
    except ValueError as exc:
        return exc


def _relay_client(response: Mock) -> MagicMock:
    """Return an httpx.AsyncClient stand-in whose post() returns response."""
    client = MagicMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    client.post = AsyncMock(return_value=response)
    return client


class ErrorReporterInitTest(unittest.TestCase):
    """Test ErrorReporter configuration."""

    def test_init_reads_relay_settings_from_env(self) -> None:
        """Test __init__ falls back to ERROR_RELAY_URL and ERROR_RELAY_TOKEN."""
        # Arrange
        env = {"ERROR_RELAY_URL": RELAY_URL, "ERROR_RELAY_TOKEN": RELAY_TOKEN}

        # Act
        with patch.dict(os.environ, env):
            reporter = ErrorReporter()

        # Assert
        self.assertEqual(reporter.relay_url, RELAY_URL)
        self.assertEqual(reporter.relay_token, RELAY_TOKEN)

    def test_init_prefers_explicit_arguments(self) -> None:
        """Test __init__ arguments override the environment."""
        # Arrange
        env = {"ERROR_RELAY_URL": "https://env.example/", "ERROR_RELAY_TOKEN": "env"}

        # Act
        with patch.dict(os.environ, env):
            reporter = ErrorReporter(relay_url=RELAY_URL, relay_token=RELAY_TOKEN)

        # Assert
        self.assertEqual(reporter.relay_url, RELAY_URL)
        self.assertEqual(reporter.relay_token, RELAY_TOKEN)


class ErrorReporterReportTest(unittest.IsolatedAsyncioTestCase):
    """Test ErrorReporter.report."""

    async def test_report_posts_title_and_body_to_relay(self) -> None:
        """Test report sends the issue to the relay with the relay token."""
        # Arrange
        reporter = ErrorReporter(relay_url=RELAY_URL, relay_token=RELAY_TOKEN)
        client = _relay_client(Mock())

        # Act
        with patch("services.error_reporter.httpx.AsyncClient", return_value=client):
            filed = await reporter.report(
                _raised("bad exit"), command="go north", player="Ada", room="square"
            )

        # Assert
        self.assertTrue(filed)
        client.post.assert_awaited_once()
        args, kwargs = client.post.call_args
        self.assertEqual(args, (RELAY_URL,))
        self.assertEqual(kwargs["headers"], {"Authorization": f"Bearer {RELAY_TOKEN}"})
        # The relay picks the labels, so a report carries only a title and body.
        self.assertEqual(set(kwargs["json"]), {"title", "body"})
        self.assertEqual(kwargs["json"]["title"], "[BugFix] ValueError: bad exit")
        self.assertIn("**Command:** `go north`", kwargs["json"]["body"])

    async def test_report_skips_an_error_it_already_reported(self) -> None:
        """Test report files each error signature only once."""
        # Arrange
        reporter = ErrorReporter(relay_url=RELAY_URL, relay_token=RELAY_TOKEN)
        client = _relay_client(Mock())
        error = _raised()

        # Act
        with patch("services.error_reporter.httpx.AsyncClient", return_value=client):
            first = await reporter.report(error, command="look")
            second = await reporter.report(error, command="look")

        # Assert
        self.assertTrue(first)
        self.assertFalse(second)
        client.post.assert_awaited_once()

    async def test_report_returns_false_when_relay_rejects_report(self) -> None:
        """Test report logs relay errors instead of raising them."""
        # Arrange
        reporter = ErrorReporter(relay_url=RELAY_URL, relay_token=RELAY_TOKEN)
        response = Mock()
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "502 Bad Gateway", request=Mock(), response=Mock()
        )
        client = _relay_client(response)

        # Act
        with patch("services.error_reporter.httpx.AsyncClient", return_value=client):
            filed = await reporter.report(_raised())

        # Assert
        self.assertIs(filed, False)

    async def test_report_does_nothing_without_relay_settings(self) -> None:
        """Test report skips the relay when the URL or token is missing."""
        for settings in ({"relay_url": RELAY_URL}, {"relay_token": RELAY_TOKEN}):
            with self.subTest(settings=settings):
                # Arrange
                with patch.dict(os.environ, {}, clear=True):
                    reporter = ErrorReporter(**settings)

                # Act
                with patch("services.error_reporter.httpx.AsyncClient") as client_cls:
                    filed = await reporter.report(_raised())

                # Assert
                self.assertFalse(filed)
                client_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
