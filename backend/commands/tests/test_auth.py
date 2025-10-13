"""
Comprehensive tests for auth module.

Tests cover:
- handle_password initialization
- handle_password old password validation
- handle_password new password entry
- handle_password confirmation
- handle_password error handling
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.test_base import BaseCommandTest
from commands.auth import handle_password, handle_password_input


class HandlePasswordInitializationTest(BaseCommandTest):
    """Test handle_password initialization flow."""

    async def test_handle_password_starts_password_change_flow(self):
        """Test handle_password initializes password change flow."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {"player": self.player}
        cmd = {"original": "password"}

        # Act
        await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("pwd_change", self.online_sessions[sid])
        self.assertEqual(
            self.online_sessions[sid]["pwd_change"]["stage"], "old_password"
        )
        self.mock_utils.send_message.assert_called_once()
        call_args = self.mock_utils.send_message.call_args[0]
        self.assertIn("present password", call_args[2])

    async def test_handle_password_sets_input_type_to_password(self):
        """Test handle_password sets input type to password."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {"player": self.player}
        cmd = {"original": "password"}

        # Act
        await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.mock_sio.emit.assert_called_with("setInputType", "password", room=sid)

    async def test_handle_password_returns_empty_string_on_init(self):
        """Test handle_password returns empty string on initialization."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {"player": self.player}
        cmd = {"original": "password"}

        # Act
        result = await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "")

    async def test_handle_password_returns_error_when_no_session(self):
        """Test handle_password returns error when session not found."""
        # Arrange
        cmd = {"original": "password"}

        # Act
        result = await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "Error: Session not found")


class HandlePasswordOldPasswordTest(BaseCommandTest):
    """Test handle_password old password validation."""

    async def test_handle_password_validates_old_password_success(self):
        """Test handle_password successfully validates old password."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "old_password",
                "old_password": None,
                "new_password": None,
            },
        }
        cmd = {"original": "oldpass123"}

        mock_auth = Mock()
        mock_auth.login = Mock()
        self.mock_player_manager.auth_manager = mock_auth

        # Act
        await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(
            self.online_sessions[sid]["pwd_change"]["stage"], "new_password"
        )
        self.assertEqual(
            self.online_sessions[sid]["pwd_change"]["old_password"], "oldpass123"
        )
        mock_auth.login.assert_called_once_with(self.player.name, "oldpass123")

    async def test_handle_password_rejects_invalid_old_password(self):
        """Test handle_password rejects invalid old password."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "old_password",
                "old_password": None,
                "new_password": None,
            },
        }
        cmd = {"original": "wrongpass"}

        mock_auth = Mock()
        mock_auth.login = Mock(side_effect=Exception("Invalid credentials"))
        self.mock_player_manager.auth_manager = mock_auth

        # Act
        result = await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertNotIn("pwd_change", self.online_sessions[sid])
        self.assertIn("Incorrect", result)
        self.mock_sio.emit.assert_called_with("setInputType", "text", room=sid)

    async def test_handle_password_rejects_blank_old_password(self):
        """Test handle_password rejects blank old password."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "old_password",
                "old_password": None,
                "new_password": None,
            },
        }
        cmd = {"original": "   "}

        # Act
        result = await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "")
        self.assertEqual(
            self.online_sessions[sid]["pwd_change"]["stage"], "old_password"
        )
        self.mock_utils.send_message.assert_called()
        call_args = self.mock_utils.send_message.call_args[0]
        self.assertIn("cannot be blank", call_args[2])


class HandlePasswordNewPasswordTest(BaseCommandTest):
    """Test handle_password new password entry."""

    async def test_handle_password_accepts_new_password(self):
        """Test handle_password accepts new password."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "new_password",
                "old_password": "oldpass123",
                "new_password": None,
            },
        }
        cmd = {"original": "newpass456"}

        # Act
        await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(
            self.online_sessions[sid]["pwd_change"]["stage"], "confirm_password"
        )
        self.assertEqual(
            self.online_sessions[sid]["pwd_change"]["new_password"], "newpass456"
        )

    async def test_handle_password_rejects_blank_new_password(self):
        """Test handle_password rejects blank new password."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "new_password",
                "old_password": "oldpass123",
                "new_password": None,
            },
        }
        cmd = {"original": "   "}

        # Act
        result = await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "")
        self.assertEqual(
            self.online_sessions[sid]["pwd_change"]["stage"], "new_password"
        )
        self.mock_utils.send_message.assert_called()


class HandlePasswordConfirmationTest(BaseCommandTest):
    """Test handle_password confirmation flow."""

    async def test_handle_password_successful_confirmation(self):
        """Test handle_password successfully changes password on correct confirmation."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "confirm_password",
                "old_password": "oldpass123",
                "new_password": "newpass456",
            },
        }
        cmd = {"original": "newpass456"}

        mock_auth = Mock()
        mock_auth.credentials = {}
        mock_auth.hash_password = Mock(return_value="hashed_password")
        mock_auth.save_credentials = Mock()
        self.mock_player_manager.auth_manager = mock_auth

        # Act
        result = await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertNotIn("pwd_change", self.online_sessions[sid])
        self.assertIn("successfully", result)
        mock_auth.save_credentials.assert_called_once()
        self.mock_sio.emit.assert_called_with("setInputType", "text", room=sid)

    async def test_handle_password_rejects_mismatched_confirmation(self):
        """Test handle_password rejects mismatched password confirmation."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "confirm_password",
                "old_password": "oldpass123",
                "new_password": "newpass456",
            },
        }
        cmd = {"original": "differentpass"}

        # Act
        result = await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertNotIn("pwd_change", self.online_sessions[sid])
        self.assertIn("different", result)
        self.assertIn("unchanged", result)
        self.mock_sio.emit.assert_called_with("setInputType", "text", room=sid)

    async def test_handle_password_rejects_blank_confirmation(self):
        """Test handle_password rejects blank confirmation."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "confirm_password",
                "old_password": "oldpass123",
                "new_password": "newpass456",
            },
        }
        cmd = {"original": "   "}

        # Act
        result = await handle_password(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertEqual(result, "")
        self.assertEqual(
            self.online_sessions[sid]["pwd_change"]["stage"], "confirm_password"
        )


class HandlePasswordInputTest(BaseCommandTest):
    """Test handle_password_input redirection."""

    async def test_handle_password_input_redirects_to_handle_password(self):
        """Test handle_password_input redirects to handle_password when pwd_change active."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {
            "player": self.player,
            "pwd_change": {
                "stage": "old_password",
                "old_password": None,
                "new_password": None,
            },
        }
        cmd = {"original": "test_input"}

        with patch(
            "commands.auth.handle_password", new_callable=AsyncMock
        ) as mock_handle_pwd:
            mock_handle_pwd.return_value = "redirected"

            # Act
            result = await handle_password_input(
                cmd,
                self.player,
                self.mock_game_state,
                self.mock_player_manager,
                self.online_sessions,
                self.mock_sio,
                self.mock_utils,
            )

            # Assert
            mock_handle_pwd.assert_called_once()
            self.assertEqual(result, "redirected")

    async def test_handle_password_input_returns_message_when_no_pwd_change(self):
        """Test handle_password_input returns instruction when no pwd_change active."""
        # Arrange
        sid = "test_sid"
        self.online_sessions[sid] = {"player": self.player}
        cmd = {"original": "test_input"}

        # Act
        result = await handle_password_input(
            cmd,
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Assert
        self.assertIn("password", result.lower())


if __name__ == "__main__":
    unittest.main()
