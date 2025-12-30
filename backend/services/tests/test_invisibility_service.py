# backend/services/tests/test_invisibility_service.py

"""
Tests for invisibility_service module.
"""

import time
import unittest
from unittest.mock import AsyncMock, Mock

from services.invisibility_service import (
    is_invisible,
    break_invisibility,
    get_invisibility_item,
    find_player_sid,
    set_invisible,
    process_invisibility_expiry,
)


class IsInvisibleSessionTest(unittest.TestCase):
    """Test is_invisible with session-based invisibility."""

    def test_is_invisible_returns_false_for_visible_player(self) -> None:
        """Test is_invisible returns False when player has no invisibility."""
        # Arrange
        player = Mock()
        player.inventory = []
        online_sessions = {"sid1": {"player": player, "invisible": False}}

        # Act
        result = is_invisible(player, online_sessions)

        # Assert
        self.assertFalse(result)

    def test_is_invisible_returns_true_for_session_invisible(self) -> None:
        """Test is_invisible returns True when session invisible flag is set."""
        # Arrange
        player = Mock()
        player.inventory = []
        online_sessions = {"sid1": {"player": player, "invisible": True}}

        # Act
        result = is_invisible(player, online_sessions)

        # Assert
        self.assertTrue(result)

    def test_is_invisible_returns_false_when_no_session_found(self) -> None:
        """Test is_invisible returns False when player has no session."""
        # Arrange
        player = Mock()
        player.inventory = []
        online_sessions = {}

        # Act
        result = is_invisible(player, online_sessions)

        # Assert
        self.assertFalse(result)


class IsInvisibleItemTest(unittest.TestCase):
    """Test is_invisible with item-based invisibility."""

    def test_is_invisible_returns_true_for_active_invisibility_item(self) -> None:
        """Test is_invisible returns True when player has active invisibility item."""
        # Arrange
        player = Mock()
        invisible_ring = Mock()
        invisible_ring.grants_invisibility = True
        invisible_ring.invisibility_expired = False
        invisible_ring.invisibility_activated_at = time.time()
        invisible_ring.invisibility_duration_seconds = 3600  # 1 hour
        player.inventory = [invisible_ring]
        online_sessions = {"sid1": {"player": player, "invisible": False}}

        # Act
        result = is_invisible(player, online_sessions)

        # Assert
        self.assertTrue(result)

    def test_is_invisible_returns_false_for_expired_invisibility_item(self) -> None:
        """Test is_invisible returns False when invisibility item has expired."""
        # Arrange
        player = Mock()
        expired_ring = Mock()
        expired_ring.grants_invisibility = True
        expired_ring.invisibility_expired = True  # Already marked as expired
        player.inventory = [expired_ring]
        online_sessions = {"sid1": {"player": player, "invisible": False}}

        # Act
        result = is_invisible(player, online_sessions)

        # Assert
        self.assertFalse(result)

    def test_is_invisible_activates_unactivated_item(self) -> None:
        """Test is_invisible activates item on first check."""
        # Arrange
        player = Mock()
        player.name = "TestPlayer"
        new_ring = Mock()
        new_ring.name = "Ring of Invisibility"
        new_ring.grants_invisibility = True
        new_ring.invisibility_expired = False
        new_ring.invisibility_activated_at = None  # Not yet activated
        new_ring.invisibility_duration_seconds = 3600
        player.inventory = [new_ring]
        online_sessions = {"sid1": {"player": player, "invisible": False}}

        # Act
        result = is_invisible(player, online_sessions)

        # Assert
        self.assertTrue(result)
        self.assertIsNotNone(new_ring.invisibility_activated_at)

    def test_is_invisible_marks_item_expired_when_duration_passed(self) -> None:
        """Test is_invisible marks item as expired when duration has passed."""
        # Arrange
        player = Mock()
        old_ring = Mock()
        old_ring.name = "Old Ring"
        old_ring.grants_invisibility = True
        old_ring.invisibility_expired = False
        old_ring.invisibility_activated_at = time.time() - 100  # Activated 100 secs ago
        old_ring.invisibility_duration_seconds = 50  # Only lasts 50 secs
        player.inventory = [old_ring]
        online_sessions = {"sid1": {"player": player, "invisible": False}}

        # Act
        result = is_invisible(player, online_sessions)

        # Assert
        self.assertFalse(result)
        self.assertTrue(old_ring.invisibility_expired)

    def test_is_invisible_returns_false_for_normal_items(self) -> None:
        """Test is_invisible returns False when player has only normal items."""
        # Arrange
        player = Mock()
        normal_item = Mock()
        normal_item.grants_invisibility = False
        player.inventory = [normal_item]
        online_sessions = {"sid1": {"player": player, "invisible": False}}

        # Act
        result = is_invisible(player, online_sessions)

        # Assert
        self.assertFalse(result)


class BreakInvisibilityTest(unittest.TestCase):
    """Test break_invisibility function."""

    def test_break_invisibility_clears_session_flag(self) -> None:
        """Test break_invisibility clears the invisible session flag."""
        # Arrange
        player = Mock()
        player.name = "TestPlayer"
        online_sessions = {"sid1": {"player": player, "invisible": True}}

        # Act
        result = break_invisibility(player, online_sessions, reason="attacking")

        # Assert
        self.assertTrue(result)
        self.assertFalse(online_sessions["sid1"]["invisible"])

    def test_break_invisibility_returns_false_when_not_invisible(self) -> None:
        """Test break_invisibility returns False when player wasn't invisible."""
        # Arrange
        player = Mock()
        player.name = "TestPlayer"
        online_sessions = {"sid1": {"player": player, "invisible": False}}

        # Act
        result = break_invisibility(player, online_sessions, reason="attacking")

        # Assert
        self.assertFalse(result)

    def test_break_invisibility_returns_false_when_no_session(self) -> None:
        """Test break_invisibility returns False when player has no session."""
        # Arrange
        player = Mock()
        player.name = "TestPlayer"
        online_sessions = {}

        # Act
        result = break_invisibility(player, online_sessions, reason="attacking")

        # Assert
        self.assertFalse(result)


class GetInvisibilityItemTest(unittest.TestCase):
    """Test get_invisibility_item function."""

    def test_get_invisibility_item_returns_active_item(self) -> None:
        """Test get_invisibility_item returns an active invisibility item."""
        # Arrange
        player = Mock()
        ring = Mock()
        ring.grants_invisibility = True
        ring.invisibility_expired = False
        ring.invisibility_activated_at = time.time()
        ring.invisibility_duration_seconds = 3600
        player.inventory = [ring]

        # Act
        result = get_invisibility_item(player)

        # Assert
        self.assertEqual(result, ring)

    def test_get_invisibility_item_returns_none_when_expired(self) -> None:
        """Test get_invisibility_item returns None when item is expired."""
        # Arrange
        player = Mock()
        ring = Mock()
        ring.grants_invisibility = True
        ring.invisibility_expired = True
        player.inventory = [ring]

        # Act
        result = get_invisibility_item(player)

        # Assert
        self.assertIsNone(result)

    def test_get_invisibility_item_returns_none_when_no_items(self) -> None:
        """Test get_invisibility_item returns None when no items in inventory."""
        # Arrange
        player = Mock()
        player.inventory = []

        # Act
        result = get_invisibility_item(player)

        # Assert
        self.assertIsNone(result)


class FindPlayerSidTest(unittest.TestCase):
    """Test find_player_sid function."""

    def test_find_player_sid_returns_sid(self) -> None:
        """Test find_player_sid returns the correct session ID."""
        # Arrange
        player = Mock()
        online_sessions = {
            "sid1": {"player": Mock()},
            "sid2": {"player": player},
        }

        # Act
        result = find_player_sid(player, online_sessions)

        # Assert
        self.assertEqual(result, "sid2")

    def test_find_player_sid_returns_none_when_not_found(self) -> None:
        """Test find_player_sid returns None when player not found."""
        # Arrange
        player = Mock()
        online_sessions = {"sid1": {"player": Mock()}}

        # Act
        result = find_player_sid(player, online_sessions)

        # Assert
        self.assertIsNone(result)


class SetInvisibleTest(unittest.TestCase):
    """Test set_invisible function."""

    def test_set_invisible_sets_flag_true(self) -> None:
        """Test set_invisible sets the invisible flag to True."""
        # Arrange
        player = Mock()
        online_sessions = {"sid1": {"player": player, "invisible": False}}

        # Act
        result = set_invisible(player, online_sessions, invisible=True)

        # Assert
        self.assertTrue(result)
        self.assertTrue(online_sessions["sid1"]["invisible"])

    def test_set_invisible_sets_flag_false(self) -> None:
        """Test set_invisible sets the invisible flag to False."""
        # Arrange
        player = Mock()
        online_sessions = {"sid1": {"player": player, "invisible": True}}

        # Act
        result = set_invisible(player, online_sessions, invisible=False)

        # Assert
        self.assertTrue(result)
        self.assertFalse(online_sessions["sid1"]["invisible"])

    def test_set_invisible_returns_false_when_no_session(self) -> None:
        """Test set_invisible returns False when player has no session."""
        # Arrange
        player = Mock()
        online_sessions = {}

        # Act
        result = set_invisible(player, online_sessions, invisible=True)

        # Assert
        self.assertFalse(result)


class ProcessInvisibilityExpiryTest(unittest.IsolatedAsyncioTestCase):
    """Test process_invisibility_expiry function."""

    async def test_process_expiry_notifies_when_item_expires(self) -> None:
        """Test process_invisibility_expiry notifies player when item expires."""
        # Arrange
        player = Mock()
        player.name = "TestPlayer"
        ring = Mock()
        ring.name = "Ring of Invisibility"
        ring.grants_invisibility = True
        ring.invisibility_expired = False
        ring.invisibility_activated_at = time.time() - 100  # Activated 100 secs ago
        ring.invisibility_duration_seconds = 50  # Only lasted 50 secs
        player.inventory = [ring]

        sio = Mock()
        utils = Mock()
        utils.send_message = AsyncMock()

        online_sessions = {"sid1": {"player": player}}

        # Act
        await process_invisibility_expiry(sio, online_sessions, utils)

        # Assert
        self.assertTrue(ring.invisibility_expired)
        utils.send_message.assert_called_once()
        call_args = utils.send_message.call_args[0]
        self.assertEqual(call_args[1], "sid1")
        self.assertIn("Ring of Invisibility", call_args[2])
        self.assertIn("visible", call_args[2].lower())

    async def test_process_expiry_skips_already_expired_items(self) -> None:
        """Test process_invisibility_expiry skips already expired items."""
        # Arrange
        player = Mock()
        ring = Mock()
        ring.grants_invisibility = True
        ring.invisibility_expired = True  # Already expired
        player.inventory = [ring]

        sio = Mock()
        utils = Mock()
        utils.send_message = AsyncMock()

        online_sessions = {"sid1": {"player": player}}

        # Act
        await process_invisibility_expiry(sio, online_sessions, utils)

        # Assert
        utils.send_message.assert_not_called()

    async def test_process_expiry_skips_unactivated_items(self) -> None:
        """Test process_invisibility_expiry skips items not yet activated."""
        # Arrange
        player = Mock()
        ring = Mock()
        ring.grants_invisibility = True
        ring.invisibility_expired = False
        ring.invisibility_activated_at = None  # Not activated
        player.inventory = [ring]

        sio = Mock()
        utils = Mock()
        utils.send_message = AsyncMock()

        online_sessions = {"sid1": {"player": player}}

        # Act
        await process_invisibility_expiry(sio, online_sessions, utils)

        # Assert
        utils.send_message.assert_not_called()


if __name__ == "__main__":
    unittest.main()
