"""
Comprehensive tests for archmage module.

Tests cover:
- handle_set_points permission checking
- handle_set_points for online and offline players
- handle_set_points error cases
- handle_reset permission checking
- handle_reset confirmation flow
- handle_reset world reset execution
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.archmage import (
    handle_set_points,
    handle_reset,
    handle_invisible,
    handle_visible,
)


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """Base class for async tests."""

    def setUp(self):
        """Set up common test fixtures."""
        # Initialize mocks
        self.mock_sio = AsyncMock()
        self.mock_utils = Mock()
        self.mock_utils.send_message = AsyncMock()
        self.mock_utils.send_stats_update = AsyncMock()

        # Mock player manager
        self.mock_player_manager = Mock()
        self.mock_player_manager.save_players = Mock()
        self.mock_player_manager.login = Mock()

        # Mock game state
        self.mock_game_state = Mock()

        # Online sessions dict
        self.online_sessions = {}

        # Create mock players
        self.archmage_player = Mock()
        self.archmage_player.name = "GodMage"
        self.archmage_player.level = "Archmage"

        self.normal_player = Mock()
        self.normal_player.name = "NormalGuy"
        self.normal_player.level = "Hero"

        self.target_player = Mock()
        self.target_player.name = "TargetPlayer"
        self.target_player.level = "Novice"
        self.target_player.points = 100
        self.target_player.level_up = Mock()


class HandleSetPointsPermissionTest(AsyncTestCase):
    """Test handle_set_points permission checking."""

    async def test_handle_set_points_denies_non_archmage(self):
        """Test handle_set_points denies access to non-Archmage players."""
        # Arrange
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer 1000"}

        # Act
        result = await handle_set_points(
            cmd,
            self.normal_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "You do not have the authority to use this command.")
        self.mock_player_manager.save_players.assert_not_called()

    async def test_handle_set_points_allows_archmage(self):
        """Test handle_set_points allows Archmage players."""
        # Arrange
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer 1000"}
        self.mock_player_manager.login.return_value = self.target_player

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("Points for TargetPlayer set to 1000", result)


class HandleSetPointsOnlinePlayerTest(AsyncTestCase):
    """Test handle_set_points with online players."""

    async def test_handle_set_points_sets_points_for_online_player(self):
        """Test handle_set_points successfully sets points for an online player."""
        # Arrange
        target_sid = "target_sid_123"
        self.online_sessions[target_sid] = {"player": self.target_player}
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer 1000"}

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(self.target_player.points, 1000)
        self.target_player.level_up.assert_called_once()
        self.mock_player_manager.save_players.assert_called_once()
        self.assertIn("Points for TargetPlayer set to 1000", result)

    async def test_handle_set_points_sends_message_to_online_player(self):
        """Test handle_set_points sends notification to online target player."""
        # Arrange
        target_sid = "target_sid_123"
        self.online_sessions[target_sid] = {"player": self.target_player}
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer 1000"}

        # Act
        await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.mock_utils.send_stats_update.assert_called_once_with(
            self.mock_sio, target_sid, self.target_player
        )
        self.mock_utils.send_message.assert_called_once()
        call_args = self.mock_utils.send_message.call_args[0]
        self.assertEqual(call_args[0], self.mock_sio)
        self.assertEqual(call_args[1], target_sid)
        self.assertIn("points to 1000", call_args[2])

    async def test_handle_set_points_reports_level_change(self):
        """Test handle_set_points reports when player level changes."""
        # Arrange
        target_sid = "target_sid_123"
        self.target_player.level = "Novice"

        def mock_level_up():
            self.target_player.level = "Hero"

        self.target_player.level_up = Mock(side_effect=mock_level_up)
        self.online_sessions[target_sid] = {"player": self.target_player}
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer 5000"}

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("Level changed from Novice to Hero", result)

    async def test_handle_set_points_reports_no_level_change(self):
        """Test handle_set_points reports when level remains the same."""
        # Arrange
        target_sid = "target_sid_123"
        self.target_player.level = "Novice"
        self.online_sessions[target_sid] = {"player": self.target_player}
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer 150"}

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("Level remains Novice", result)


class HandleSetPointsOfflinePlayerTest(AsyncTestCase):
    """Test handle_set_points with offline players."""

    async def test_handle_set_points_sets_points_for_offline_player(self):
        """Test handle_set_points successfully sets points for an offline player."""
        # Arrange
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer 1000"}
        self.mock_player_manager.login.return_value = self.target_player

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(self.target_player.points, 1000)
        self.target_player.level_up.assert_called_once()
        self.mock_player_manager.save_players.assert_called_once()
        self.assertIn("Points for TargetPlayer set to 1000", result)

    async def test_handle_set_points_no_message_to_offline_player(self):
        """Test handle_set_points does not send message to offline player."""
        # Arrange
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer 1000"}
        self.mock_player_manager.login.return_value = self.target_player

        # Act
        await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.mock_utils.send_message.assert_not_called()
        self.mock_utils.send_stats_update.assert_not_called()


class HandleSetPointsErrorTest(AsyncTestCase):
    """Test handle_set_points error handling."""

    async def test_handle_set_points_rejects_missing_arguments(self):
        """Test handle_set_points rejects command with missing arguments."""
        # Arrange
        cmd = {"subject": None, "original": "set"}

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("Set points for whom?", result)

    async def test_handle_set_points_rejects_player_not_found(self):
        """Test handle_set_points rejects when player not found."""
        # Arrange
        cmd = {"subject": "UnknownPlayer", "original": "set UnknownPlayer 1000"}
        self.mock_player_manager.login.return_value = None

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("not found", result)

    async def test_handle_set_points_rejects_negative_points(self):
        """Test handle_set_points rejects negative points."""
        # Arrange
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer -100"}
        self.mock_player_manager.login.return_value = self.target_player

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("Points cannot be negative", result)

    async def test_handle_set_points_rejects_invalid_points(self):
        """Test handle_set_points rejects non-numeric points."""
        # Arrange
        cmd = {"subject": "TargetPlayer", "original": "set TargetPlayer abc"}
        self.mock_player_manager.login.return_value = self.target_player

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("Points must be a number", result)

    async def test_handle_set_points_handles_multiword_player_names(self):
        """Test handle_set_points handles player names with spaces."""
        # Arrange
        multi_word_player = Mock()
        multi_word_player.name = "Lord Blackwood"
        multi_word_player.level = "Hero"
        multi_word_player.points = 100
        multi_word_player.level_up = Mock()

        cmd = {"subject": "Lord Blackwood", "original": "set Lord Blackwood 1000"}
        self.mock_player_manager.login.return_value = multi_word_player

        # Act
        result = await handle_set_points(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(multi_word_player.points, 1000)
        self.assertIn("Points for Lord Blackwood set to 1000", result)


class HandleResetPermissionTest(AsyncTestCase):
    """Test handle_reset permission checking."""

    async def test_handle_reset_denies_non_archmage(self):
        """Test handle_reset denies access to non-Archmage players."""
        # Arrange
        cmd = {"subject": "confirm", "original": "reset confirm"}

        # Act
        result = await handle_reset(
            cmd,
            self.normal_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "You do not have the authority to use this command.")

    async def test_handle_reset_allows_archmage(self):
        """Test handle_reset allows Archmage players."""
        # Arrange
        cmd = {"subject": None, "original": "reset"}

        # Act
        result = await handle_reset(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("reset the entire world", result)


class HandleResetConfirmationTest(AsyncTestCase):
    """Test handle_reset confirmation flow."""

    async def test_handle_reset_requires_confirmation(self):
        """Test handle_reset requires confirmation before executing."""
        # Arrange
        cmd = {"subject": None, "original": "reset"}

        # Act
        result = await handle_reset(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("reset the entire world", result)
        self.assertIn("reset confirm", result)
        self.mock_utils.send_message.assert_not_called()

    @patch("commands.archmage.asyncio.sleep", new_callable=AsyncMock)
    @patch("commands.archmage.os.execl")
    async def test_handle_reset_executes_with_confirmation(
        self, mock_execl, mock_sleep
    ):
        """Test handle_reset executes reset when confirmed."""
        # Arrange
        cmd = {"subject": "confirm", "original": "reset confirm"}

        player1_sid = "sid1"
        player2_sid = "sid2"
        self.online_sessions[player1_sid] = {"player": self.normal_player}
        self.online_sessions[player2_sid] = {"player": self.target_player}

        # Act
        await handle_reset(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        # Should send messages to all players
        self.assertEqual(self.mock_utils.send_message.call_count, 2)

        # Should disconnect all players
        self.assertEqual(self.mock_sio.disconnect.call_count, 2)

        # Should restart the process
        mock_execl.assert_called_once()

    @patch("commands.archmage.asyncio.sleep", new_callable=AsyncMock)
    @patch("commands.archmage.os.execl")
    async def test_handle_reset_broadcasts_warning_message(
        self, mock_execl, mock_sleep
    ):
        """Test handle_reset broadcasts warning message to all players."""
        # Arrange
        cmd = {"subject": "confirm", "original": "reset confirm"}

        player1_sid = "sid1"
        self.online_sessions[player1_sid] = {"player": self.normal_player}

        # Act
        await handle_reset(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        call_args = self.mock_utils.send_message.call_args[0]
        message = call_args[2]
        self.assertIn("WORLD RESET INITIATED", message)
        self.assertIn("disconnected", message)

    @patch("commands.archmage.asyncio.sleep", new_callable=AsyncMock)
    @patch("commands.archmage.os.execl")
    async def test_handle_reset_delays_before_restart(self, mock_execl, mock_sleep):
        """Test handle_reset delays 2 seconds before restarting."""
        # Arrange
        cmd = {"subject": "confirm", "original": "reset confirm"}

        # Act
        await handle_reset(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        mock_sleep.assert_called_once_with(2)

    @patch("commands.archmage.asyncio.sleep", new_callable=AsyncMock)
    @patch("commands.archmage.os.execl")
    @patch("commands.archmage.logger")
    async def test_handle_reset_handles_disconnect_errors(
        self, mock_logger, mock_execl, mock_sleep
    ):
        """Test handle_reset handles errors during player disconnection."""
        # Arrange
        cmd = {"subject": "confirm", "original": "reset confirm"}

        player1_sid = "sid1"
        self.online_sessions[player1_sid] = {"player": self.normal_player}

        # Make disconnect raise an error
        self.mock_sio.disconnect.side_effect = Exception("Connection error")

        # Act
        await handle_reset(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        # Should still attempt to restart even if disconnection fails
        mock_execl.assert_called_once()


class HandleInvisiblePermissionTest(AsyncTestCase):
    """Test handle_invisible permission checking."""

    async def test_handle_invisible_denies_non_archmage(self) -> None:
        """Test handle_invisible denies access to non-Archmage players."""
        # Arrange
        cmd = {"verb": "invisible", "original": "invis"}

        # Act
        result = await handle_invisible(
            cmd,
            self.normal_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "You do not have the authority to use this command.")


class HandleInvisibleSessionTest(AsyncTestCase):
    """Test handle_invisible session handling."""

    async def test_handle_invisible_returns_error_when_no_session(self) -> None:
        """Test handle_invisible returns error when player has no session."""
        # Arrange
        cmd = {"verb": "invisible", "original": "invis"}
        # No session added for archmage_player

        # Act
        result = await handle_invisible(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "Error: Session not found.")

    async def test_handle_invisible_returns_already_invisible(self) -> None:
        """Test handle_invisible returns message when already invisible."""
        # Arrange
        cmd = {"verb": "invisible", "original": "invis"}
        archmage_sid = "archmage_sid"
        self.online_sessions[archmage_sid] = {
            "player": self.archmage_player,
            "invisible": True,
        }

        # Act
        result = await handle_invisible(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "You are already invisible.")

    async def test_handle_invisible_makes_player_invisible(self) -> None:
        """Test handle_invisible successfully makes player invisible."""
        # Arrange
        cmd = {"verb": "invisible", "original": "invis"}
        archmage_sid = "archmage_sid"
        self.online_sessions[archmage_sid] = {
            "player": self.archmage_player,
            "invisible": False,
        }

        # Act
        result = await handle_invisible(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "You fade from view. You are now invisible.")
        self.assertTrue(self.online_sessions[archmage_sid]["invisible"])


class HandleVisiblePermissionTest(AsyncTestCase):
    """Test handle_visible permission checking."""

    async def test_handle_visible_denies_non_archmage(self) -> None:
        """Test handle_visible denies access to non-Archmage players."""
        # Arrange
        cmd = {"verb": "visible", "original": "vis"}

        # Act
        result = await handle_visible(
            cmd,
            self.normal_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "You do not have the authority to use this command.")


class HandleVisibleSessionTest(AsyncTestCase):
    """Test handle_visible session handling."""

    async def test_handle_visible_returns_error_when_no_session(self) -> None:
        """Test handle_visible returns error when player has no session."""
        # Arrange
        cmd = {"verb": "visible", "original": "vis"}
        # No session added for archmage_player

        # Act
        result = await handle_visible(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "Error: Session not found.")

    async def test_handle_visible_returns_already_visible(self) -> None:
        """Test handle_visible returns message when already visible."""
        # Arrange
        cmd = {"verb": "visible", "original": "vis"}
        archmage_sid = "archmage_sid"
        self.online_sessions[archmage_sid] = {
            "player": self.archmage_player,
            "invisible": False,
        }

        # Act
        result = await handle_visible(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "You are already visible.")

    async def test_handle_visible_makes_player_visible(self) -> None:
        """Test handle_visible successfully makes player visible."""
        # Arrange
        cmd = {"verb": "visible", "original": "vis"}
        archmage_sid = "archmage_sid"
        self.online_sessions[archmage_sid] = {
            "player": self.archmage_player,
            "invisible": True,
        }

        # Act
        result = await handle_visible(
            cmd,
            self.archmage_player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "You shimmer back into view. You are now visible.")
        self.assertFalse(self.online_sessions[archmage_sid]["invisible"])


if __name__ == "__main__":
    unittest.main()
