"""
Comprehensive tests for communication commands.

Tests cover:
- Say command (room messages)
- Tell command (private messages)
- Shout command (global messages)
- Act command (emotes)
- Converse mode
- Pending communication handling
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.communication import (
    handle_say,
    handle_tell,
    handle_shout,
    handle_act,
    handle_converse,
    handle_pending_communication,
)
from models.Player import Player


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """Base class for async tests."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Player("TestPlayer")
        self.player.current_room = "test_room"

        self.other_player = Player("OtherPlayer")
        self.other_player.current_room = "test_room"

        self.remote_player = Player("RemotePlayer")
        self.remote_player.current_room = "other_room"

        # Mock sio and utils
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

        # Set up online sessions
        self.online_sessions = {
            "sid1": {"player": self.player},
            "sid2": {"player": self.other_player},
            "sid3": {"player": self.remote_player},
        }

        self.game_state = None
        self.player_manager = None


class SayCommandTest(AsyncTestCase):
    """Test say command (room messages)."""

    async def test_say_broadcasts_to_room(self):
        """Test saying something broadcasts to players in same room."""
        cmd = {"verb": "say", "subject": "Hello everyone!"}

        result = await handle_say(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should return empty string
        self.assertEqual(result, "")

        # Should send message to other player in room
        self.utils.send_message.assert_called_once()
        call_args = self.utils.send_message.call_args
        self.assertEqual(call_args[0][1], "sid2")  # OtherPlayer's sid
        self.assertIn("Hello everyone!", call_args[0][2])
        self.assertIn("TestPlayer", call_args[0][2])

    async def test_say_no_message_returns_error(self):
        """Test say without message returns error."""
        cmd = {"verb": "say"}

        result = await handle_say(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "What do you want to say?")
        self.utils.send_message.assert_not_called()

    async def test_say_not_sent_to_different_room(self):
        """Test say is not sent to players in different rooms."""
        cmd = {"verb": "say", "subject": "Hello!"}

        await handle_say(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should only be called once (for sid2), not for sid3
        self.assertEqual(self.utils.send_message.call_count, 1)
        call_args = self.utils.send_message.call_args
        self.assertNotEqual(call_args[0][1], "sid3")


class TellCommandTest(AsyncTestCase):
    """Test tell command (private messages)."""

    async def test_tell_sends_private_message(self):
        """Test sending a private message to another player."""
        cmd = {"verb": "tell", "subject": "OtherPlayer", "instrument": "Secret message"}

        result = await handle_tell(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should confirm message sent
        self.assertIn("You tell OtherPlayer", result)
        self.assertIn("Secret message", result)

        # Should send message to recipient
        self.utils.send_message.assert_called_once()
        call_args = self.utils.send_message.call_args
        self.assertEqual(call_args[0][1], "sid2")  # OtherPlayer's sid
        self.assertIn("Secret message", call_args[0][2])
        self.assertIn("tells you", call_args[0][2])

    async def test_tell_no_recipient_returns_error(self):
        """Test tell without recipient returns error."""
        cmd = {"verb": "tell"}

        result = await handle_tell(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("who do you want to tell", result.lower())

    async def test_tell_offline_player_returns_error(self):
        """Test telling offline player returns error."""
        cmd = {
            "verb": "tell",
            "subject": "OfflinePlayer",
            "instrument": "Are you there?",
        }

        result = await handle_tell(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("not online", result)
        self.utils.send_message.assert_not_called()

    async def test_tell_case_insensitive(self):
        """Test tell works with different case."""
        cmd = {
            "verb": "tell",
            "subject": "otherplayer",  # lowercase
            "instrument": "Hello!",
        }

        result = await handle_tell(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("You tell", result)
        self.utils.send_message.assert_called_once()


class ShoutCommandTest(AsyncTestCase):
    """Test shout command (global messages)."""

    async def test_shout_broadcasts_globally(self):
        """Test shout broadcasts to all online players."""
        cmd = {"verb": "shout", "subject": "Important announcement!"}

        result = await handle_shout(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should return empty string
        self.assertEqual(result, "")

        # Should send to all other players (2 calls)
        self.assertEqual(self.utils.send_message.call_count, 2)

        # Check messages contain shout text
        for call in self.utils.send_message.call_args_list:
            message = call[0][2]
            self.assertIn("shouts", message)
            self.assertIn("Important announcement!", message)

    async def test_shout_no_message_prompts(self):
        """Test shout without message prompts for input."""
        cmd = {"verb": "shout"}

        result = await handle_shout(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("tell me the message", result.lower())


class ActCommandTest(AsyncTestCase):
    """Test act command (emotes)."""

    async def test_act_broadcasts_emote(self):
        """Test acting broadcasts emote to room."""
        cmd = {"verb": "act", "subject": "waves hello"}

        result = await handle_act(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should return formatted action
        self.assertIn("TestPlayer", result)
        self.assertIn("waves hello", result)
        self.assertIn("**", result)  # Formatted with asterisks

        # Should send to other player in room
        self.utils.send_message.assert_called_once()

    async def test_act_no_action_returns_error(self):
        """Test act without action returns error."""
        cmd = {"verb": "act"}

        result = await handle_act(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "What do you want to do?")


class ConverseCommandTest(AsyncTestCase):
    """Test converse mode toggling."""

    async def test_converse_toggles_on(self):
        """Test converse mode can be turned on."""
        cmd = {"verb": "converse"}

        result = await handle_converse(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("ON", result)
        self.assertTrue(self.online_sessions["sid1"].get("converse_mode"))

    async def test_converse_toggles_off(self):
        """Test converse mode can be turned off."""
        # Turn it on first
        self.online_sessions["sid1"]["converse_mode"] = True

        cmd = {"verb": "converse"}

        result = await handle_converse(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("OFF", result)
        self.assertFalse(self.online_sessions["sid1"].get("converse_mode"))


class PendingCommunicationTest(AsyncTestCase):
    """Test pending communication handling."""

    async def test_pending_shout_completes(self):
        """Test completing a pending shout."""
        pending = {"type": "shout"}
        message = "Delayed announcement"

        # Set up pending_comm in session
        self.online_sessions["sid1"]["pending_comm"] = pending

        await handle_pending_communication(
            pending,
            message,
            self.player,
            "sid1",
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should broadcast to others
        self.assertEqual(self.utils.send_message.call_count, 2)

        # Should have removed pending comm
        self.assertNotIn("pending_comm", self.online_sessions.get("sid1", {}))

    async def test_pending_tell_completes(self):
        """Test completing a pending tell."""
        pending = {"type": "private", "recipient": "OtherPlayer"}
        message = "Delayed message"

        # Set up pending_comm in session
        self.online_sessions["sid1"]["pending_comm"] = pending

        await handle_pending_communication(
            pending,
            message,
            self.player,
            "sid1",
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should send to recipient
        self.utils.send_message.assert_called_once()
        call_args = self.utils.send_message.call_args
        self.assertEqual(call_args[0][1], "sid2")

    async def test_pending_empty_message_cancels(self):
        """Test empty message cancels pending communication."""
        pending = {"type": "shout"}
        # Set up pending_comm in session
        self.online_sessions["sid1"]["pending_comm"] = pending

        result = await handle_pending_communication(
            pending, "", self.player, "sid1", self.online_sessions, self.sio, self.utils
        )

        self.assertIn("cancelled", result.lower())
        self.assertNotIn("pending_comm", self.online_sessions["sid1"])


class InvisibilityCommunicationTest(AsyncTestCase):
    """Test invisibility effects on communication commands."""

    @patch("commands.communication.is_invisible")
    async def test_shout_shows_someone_when_invisible(self, mock_is_invisible):
        """Test shouting while invisible shows 'Someone shouts'."""
        # Arrange
        mock_is_invisible.return_value = True
        cmd = {"verb": "shout", "subject": "Hello!"}

        # Act
        await handle_shout(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert
        self.assertTrue(self.utils.send_message.called)
        call_args = self.utils.send_message.call_args_list[0]
        message = call_args[0][2]
        self.assertIn("Someone shouts", message)
        self.assertNotIn("TestPlayer", message)

    @patch("commands.communication.is_invisible")
    async def test_say_shows_someone_when_invisible(self, mock_is_invisible):
        """Test saying something while invisible shows 'Someone says'."""
        # Arrange
        mock_is_invisible.return_value = True
        cmd = {"verb": "say", "subject": "Hello room!"}

        # Act
        await handle_say(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert
        self.assertTrue(self.utils.send_message.called)
        call_args = self.utils.send_message.call_args
        message = call_args[0][2]
        self.assertIn("Someone says", message)
        self.assertNotIn("TestPlayer", message)

    @patch("commands.communication.is_invisible")
    async def test_tell_shows_someone_when_sender_invisible(self, mock_is_invisible):
        """Test telling someone while invisible shows 'Someone tells you'."""

        # Arrange
        # Only the sender (self.player) is invisible
        def check_invisible(player, sessions):
            return player == self.player

        mock_is_invisible.side_effect = check_invisible
        cmd = {"verb": "tell", "subject": "OtherPlayer", "instrument": "Secret!"}

        # Act
        await handle_tell(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert
        self.assertTrue(self.utils.send_message.called)
        call_args = self.utils.send_message.call_args
        message = call_args[0][2]
        self.assertIn("Someone tells you", message)
        self.assertNotIn("TestPlayer", message)

    @patch("commands.communication.is_invisible")
    async def test_tell_fails_when_recipient_invisible(self, mock_is_invisible):
        """Test telling an invisible player fails."""

        # Arrange
        # Only the recipient (other_player) is invisible
        def check_invisible(player, sessions):
            return player == self.other_player

        mock_is_invisible.side_effect = check_invisible
        cmd = {"verb": "tell", "subject": "OtherPlayer", "instrument": "Hello!"}

        # Act
        result = await handle_tell(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert
        self.assertIn("not online", result)
        self.utils.send_message.assert_not_called()

    @patch("commands.communication.is_invisible")
    async def test_act_shows_someone_when_invisible(self, mock_is_invisible):
        """Test emoting while invisible shows 'Someone'."""
        # Arrange
        mock_is_invisible.return_value = True
        cmd = {"verb": "act", "subject": "waves"}

        # Act
        await handle_act(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert
        self.assertTrue(self.utils.send_message.called)
        call_args = self.utils.send_message.call_args
        message = call_args[0][2]
        self.assertIn("Someone", message)
        self.assertNotIn("TestPlayer", message)


if __name__ == "__main__":
    unittest.main()
