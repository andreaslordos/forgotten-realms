"""
Comprehensive tests for notifications module.

Tests cover:
- set_context initialization
- broadcast_room functionality
- broadcast_arrival
- broadcast_departure
- broadcast_logout
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.test_base import BaseAsyncTest
from tests.test_helpers import create_mock_player
from services import notifications


class SetContextTest(unittest.TestCase):
    """Test set_context functionality."""

    def test_set_context_sets_sessions(self):
        """Test set_context sets SESSIONS variable."""
        # Arrange
        mock_sessions = {"sid1": {"player": Mock()}}
        mock_send = AsyncMock()

        # Act
        notifications.set_context(mock_sessions, mock_send)

        # Assert
        self.assertEqual(notifications.SESSIONS, mock_sessions)

    def test_set_context_sets_send_message(self):
        """Test set_context sets send_msg variable."""
        # Arrange
        mock_sessions = {}
        mock_send = AsyncMock()

        # Act
        notifications.set_context(mock_sessions, mock_send)

        # Assert
        self.assertEqual(notifications.send_msg, mock_send)


class BroadcastRoomTest(BaseAsyncTest):
    """Test broadcast_room functionality."""

    async def test_broadcast_room_sends_to_all_players_in_room(self):
        """Test broadcast_room sends message to all players in room."""
        # Arrange
        player1 = create_mock_player(name="Alice", location="room1")
        player1.current_room = "room1"
        player2 = create_mock_player(name="Bob", location="room1")
        player2.current_room = "room1"

        mock_sessions = {
            "sid1": {"player": player1},
            "sid2": {"player": player2}
        }
        mock_send = AsyncMock()

        notifications.set_context(mock_sessions, mock_send)

        # Act
        await notifications.broadcast_room("room1", "Test message")

        # Assert
        self.assertEqual(mock_send.call_count, 2)

    async def test_broadcast_room_excludes_specified_players(self):
        """Test broadcast_room excludes specified players."""
        # Arrange
        player1 = create_mock_player(name="Alice", location="room1")
        player1.current_room = "room1"
        player2 = create_mock_player(name="Bob", location="room1")
        player2.current_room = "room1"

        mock_sessions = {
            "sid1": {"player": player1},
            "sid2": {"player": player2}
        }
        mock_send = AsyncMock()

        notifications.set_context(mock_sessions, mock_send)

        # Act
        await notifications.broadcast_room("room1", "Test message", exclude_player=["Alice"])

        # Assert
        self.assertEqual(mock_send.call_count, 1)
        # Only Bob should receive message
        call_args = mock_send.call_args[0]
        self.assertEqual(call_args[0], "sid2")

    async def test_broadcast_room_skips_sleeping_players(self):
        """Test broadcast_room skips sleeping players."""
        # Arrange
        player1 = create_mock_player(name="Alice", location="room1")
        player1.current_room = "room1"

        mock_sessions = {
            "sid1": {"player": player1, "sleeping": True}
        }
        mock_send = AsyncMock()

        notifications.set_context(mock_sessions, mock_send)

        # Act
        await notifications.broadcast_room("room1", "Test message")

        # Assert
        mock_send.assert_not_called()

    async def test_broadcast_room_only_sends_to_correct_room(self):
        """Test broadcast_room only sends to players in specified room."""
        # Arrange
        player1 = create_mock_player(name="Alice", location="room1")
        player1.current_room = "room1"
        player2 = create_mock_player(name="Bob", location="room2")
        player2.current_room = "room2"

        mock_sessions = {
            "sid1": {"player": player1},
            "sid2": {"player": player2}
        }
        mock_send = AsyncMock()

        notifications.set_context(mock_sessions, mock_send)

        # Act
        await notifications.broadcast_room("room1", "Test message")

        # Assert
        self.assertEqual(mock_send.call_count, 1)
        call_args = mock_send.call_args[0]
        self.assertEqual(call_args[0], "sid1")

    async def test_broadcast_room_handles_uninitialized_context(self):
        """Test broadcast_room handles uninitialized context gracefully."""
        # Arrange
        notifications.SESSIONS = None
        notifications.send_msg = None

        # Act
        await notifications.broadcast_room("room1", "Test message")

        # Assert - should not crash


class BroadcastArrivalTest(BaseAsyncTest):
    """Test broadcast_arrival functionality."""

    @patch('services.notifications.broadcast_room', new_callable=AsyncMock)
    async def test_broadcast_arrival_broadcasts_to_current_room(self, mock_broadcast):
        """Test broadcast_arrival broadcasts to player's current room."""
        # Arrange
        player = create_mock_player(name="Alice", level="Hero")
        player.current_room = "room1"

        # Act
        await notifications.broadcast_arrival(player)

        # Assert
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args[0]
        self.assertEqual(call_args[0], "room1")
        self.assertIn("Alice", call_args[1])
        self.assertIn("Hero", call_args[1])

    @patch('services.notifications.broadcast_room', new_callable=AsyncMock)
    async def test_broadcast_arrival_excludes_arriving_player(self, mock_broadcast):
        """Test broadcast_arrival excludes the arriving player."""
        # Arrange
        player = create_mock_player(name="Alice", level="Hero")
        player.current_room = "room1"

        # Act
        await notifications.broadcast_arrival(player)

        # Assert
        call_kwargs = mock_broadcast.call_args[1]
        self.assertIn("Alice", call_kwargs['exclude_player'])


class BroadcastDepartureTest(BaseAsyncTest):
    """Test broadcast_departure functionality."""

    @patch('services.notifications.broadcast_room', new_callable=AsyncMock)
    async def test_broadcast_departure_broadcasts_to_room(self, mock_broadcast):
        """Test broadcast_departure broadcasts to specified room."""
        # Arrange
        player = create_mock_player(name="Bob", level="Warrior")

        # Act
        await notifications.broadcast_departure("room1", player)

        # Assert
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args[0]
        self.assertEqual(call_args[0], "room1")
        self.assertIn("Bob", call_args[1])
        self.assertIn("Warrior", call_args[1])

    @patch('services.notifications.broadcast_room', new_callable=AsyncMock)
    async def test_broadcast_departure_excludes_departing_player(self, mock_broadcast):
        """Test broadcast_departure excludes the departing player."""
        # Arrange
        player = create_mock_player(name="Bob", level="Warrior")

        # Act
        await notifications.broadcast_departure("room1", player)

        # Assert
        call_kwargs = mock_broadcast.call_args[1]
        self.assertIn("Bob", call_kwargs['exclude_player'])


class BroadcastLogoutTest(BaseAsyncTest):
    """Test broadcast_logout functionality."""

    @patch('services.notifications.broadcast_room', new_callable=AsyncMock)
    async def test_broadcast_logout_broadcasts_to_current_room(self, mock_broadcast):
        """Test broadcast_logout broadcasts to player's current room."""
        # Arrange
        player = create_mock_player(name="Charlie", level="Mage")
        player.current_room = "room1"

        # Act
        await notifications.broadcast_logout(player)

        # Assert
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args[0]
        self.assertEqual(call_args[0], "room1")
        self.assertIn("Charlie", call_args[1])
        self.assertIn("passed on", call_args[1])

    @patch('services.notifications.broadcast_room', new_callable=AsyncMock)
    async def test_broadcast_logout_excludes_logging_out_player(self, mock_broadcast):
        """Test broadcast_logout excludes the logging out player."""
        # Arrange
        player = create_mock_player(name="Charlie", level="Mage")
        player.current_room = "room1"

        # Act
        await notifications.broadcast_logout(player)

        # Assert
        call_kwargs = mock_broadcast.call_args[1]
        self.assertIn("Charlie", call_kwargs['exclude_player'])


if __name__ == "__main__":
    unittest.main()
