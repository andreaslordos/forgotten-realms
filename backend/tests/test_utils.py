"""
Comprehensive tests for utils module (backend root) - CRITICAL.

Tests cover:
- send_message functionality
- send_stats_update with player
- send_stats_update validation
- create_linked_doors functionality
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_base import BaseAsyncTest
from tests.test_helpers import create_mock_player
from utils import send_message, send_stats_update, create_linked_doors


class SendMessageTest(BaseAsyncTest):
    """Test send_message functionality."""

    async def test_send_message_emits_to_socket(self):
        """Test send_message emits message to socket."""
        # Arrange
        sid = "test_sid_123"
        message = "Hello, player!"

        # Act
        await send_message(self.mock_sio, sid, message)

        # Assert
        self.mock_sio.emit.assert_called_once_with("message", message, room=sid)

    async def test_send_message_handles_empty_message(self):
        """Test send_message handles empty message."""
        # Arrange
        sid = "test_sid_123"
        message = ""

        # Act
        await send_message(self.mock_sio, sid, message)

        # Assert
        self.mock_sio.emit.assert_called_once()

    async def test_send_message_handles_multiline_message(self):
        """Test send_message handles multiline message."""
        # Arrange
        sid = "test_sid_123"
        message = "Line 1\nLine 2\nLine 3"

        # Act
        await send_message(self.mock_sio, sid, message)

        # Assert
        call_args = self.mock_sio.emit.call_args[0]
        self.assertEqual(call_args[1], message)


class SendStatsUpdateTest(BaseAsyncTest):
    """Test send_stats_update functionality."""

    async def test_send_stats_update_emits_stats_data(self):
        """Test send_stats_update emits correct stats data."""
        # Arrange
        player = create_mock_player(name="TestPlayer", points=1000)
        player.stamina = 75
        player.max_stamina = 100
        sid = "test_sid_123"

        # Act
        await send_stats_update(self.mock_sio, sid, player)

        # Assert
        self.mock_sio.emit.assert_called_once()
        call_args = self.mock_sio.emit.call_args
        self.assertEqual(call_args[0][0], "statsUpdate")
        stats_data = call_args[0][1]
        self.assertEqual(stats_data["name"], "TestPlayer")
        self.assertEqual(stats_data["score"], 1000)
        self.assertEqual(stats_data["stamina"], 75)
        self.assertEqual(stats_data["max_stamina"], 100)

    async def test_send_stats_update_returns_early_when_player_none(self):
        """Test send_stats_update returns early when player is None."""
        # Arrange
        sid = "test_sid_123"

        # Act
        await send_stats_update(self.mock_sio, sid, None)

        # Assert
        self.mock_sio.emit.assert_not_called()

    async def test_send_stats_update_validates_required_attributes(self):
        """Test send_stats_update validates player has required attributes."""
        # Arrange
        invalid_player = Mock(spec=["name"])  # Only has name, missing other attrs
        invalid_player.name = "Test"
        sid = "test_sid_123"

        # Act
        await send_stats_update(self.mock_sio, sid, invalid_player)

        # Assert
        self.mock_sio.emit.assert_not_called()

    async def test_send_stats_update_handles_mob_objects(self):
        """Test send_stats_update handles non-player objects gracefully."""
        # Arrange
        mob = Mock(spec=["name"])  # Only has name, missing points
        mob.name = "Orc"
        sid = "test_sid_123"

        # Act
        await send_stats_update(self.mock_sio, sid, mob)

        # Assert
        # Should not crash, just return early
        self.mock_sio.emit.assert_not_called()


class CreateLinkedDoorsTest(unittest.TestCase):
    """Test create_linked_doors functionality."""

    def test_create_linked_doors_returns_two_doors(self):
        """Test create_linked_doors returns two door objects."""
        # Act
        door1, door2 = create_linked_doors(
            "room1", "room2", "door1", "door2", "wooden door", "north", "south"
        )

        # Assert
        self.assertIsNotNone(door1)
        self.assertIsNotNone(door2)

    def test_create_linked_doors_sets_door_names(self):
        """Test create_linked_doors sets correct door names."""
        # Act
        door1, door2 = create_linked_doors(
            "room1", "room2", "door1", "door2", "iron door", "north", "south"
        )

        # Assert
        self.assertEqual(door1.name, "iron door")
        self.assertEqual(door2.name, "iron door")

    def test_create_linked_doors_sets_initial_state_closed(self):
        """Test create_linked_doors sets initial state to closed."""
        # Act
        door1, door2 = create_linked_doors(
            "room1",
            "room2",
            "door1",
            "door2",
            "door",
            "north",
            "south",
            initial_state="closed",
        )

        # Assert
        self.assertEqual(door1.state, "closed")
        self.assertEqual(door2.state, "closed")

    def test_create_linked_doors_sets_initial_state_open(self):
        """Test create_linked_doors sets initial state to open."""
        # Act
        door1, door2 = create_linked_doors(
            "room1",
            "room2",
            "door1",
            "door2",
            "door",
            "north",
            "south",
            initial_state="open",
        )

        # Assert
        self.assertEqual(door1.state, "open")
        self.assertEqual(door2.state, "open")

    def test_create_linked_doors_links_doors_together(self):
        """Test create_linked_doors links doors together."""
        # Act
        door1, door2 = create_linked_doors(
            "room1", "room2", "door1_id", "door2_id", "door", "north", "south"
        )

        # Assert
        # Doors should be linked
        self.assertGreater(len(door1.linked_items), 0)
        self.assertGreater(len(door2.linked_items), 0)
        self.assertIn("door2_id", door1.linked_items)
        self.assertIn("door1_id", door2.linked_items)

    def test_create_linked_doors_sets_room_ids(self):
        """Test create_linked_doors sets room IDs on doors."""
        # Act
        door1, door2 = create_linked_doors(
            "tavern", "street", "door1", "door2", "door", "out", "in"
        )

        # Assert
        self.assertEqual(door1.room_id, "tavern")
        self.assertEqual(door2.room_id, "street")

    def test_create_linked_doors_adds_open_interaction(self):
        """Test create_linked_doors adds open interaction."""
        # Act
        door1, door2 = create_linked_doors(
            "room1", "room2", "door1", "door2", "door", "north", "south"
        )

        # Assert
        # Doors should have open interaction
        self.assertIn("open", door1.interactions)

    def test_create_linked_doors_adds_close_interaction(self):
        """Test create_linked_doors adds close interaction."""
        # Act
        door1, door2 = create_linked_doors(
            "room1", "room2", "door1", "door2", "door", "north", "south"
        )

        # Assert
        # Doors should have close interaction
        self.assertIn("close", door1.interactions)

    def test_create_linked_doors_sets_doors_not_takeable(self):
        """Test create_linked_doors sets doors as not takeable."""
        # Act
        door1, door2 = create_linked_doors(
            "room1", "room2", "door1", "door2", "door", "north", "south"
        )

        # Assert
        self.assertFalse(door1.takeable)
        self.assertFalse(door2.takeable)

    def test_create_linked_doors_adds_to_game_state_rooms(self):
        """Test create_linked_doors adds doors to game state rooms."""
        # Arrange
        from tests.test_helpers import create_mock_room, create_mock_game_state

        room1 = create_mock_room("room1")
        room2 = create_mock_room("room2")
        game_state = create_mock_game_state(rooms={"room1": room1, "room2": room2})

        # Act
        door1, door2 = create_linked_doors(
            "room1",
            "room2",
            "door1",
            "door2",
            "door",
            "north",
            "south",
            game_state=game_state,
        )

        # Assert
        room1.add_item.assert_called_once()
        room2.add_item.assert_called_once()

    def test_create_linked_doors_adds_to_rooms_dict(self):
        """Test create_linked_doors adds doors to rooms dictionary."""
        # Arrange
        from tests.test_helpers import create_mock_room

        room1 = create_mock_room("room1")
        room2 = create_mock_room("room2")
        rooms = {"room1": room1, "room2": room2}

        # Act
        door1, door2 = create_linked_doors(
            "room1", "room2", "door1", "door2", "door", "north", "south", rooms=rooms
        )

        # Assert
        room1.add_item.assert_called_once()
        room2.add_item.assert_called_once()

    def test_create_linked_doors_adds_exits_when_open(self):
        """Test create_linked_doors adds exits when initial state is open."""
        # Arrange
        from tests.test_helpers import create_mock_room

        room1 = create_mock_room("room1")
        room2 = create_mock_room("room2")
        rooms = {"room1": room1, "room2": room2}

        # Act
        door1, door2 = create_linked_doors(
            "room1",
            "room2",
            "door1",
            "door2",
            "door",
            "north",
            "south",
            initial_state="open",
            rooms=rooms,
        )

        # Assert
        self.assertEqual(room1.exits["north"], "room2")
        self.assertEqual(room2.exits["south"], "room1")


if __name__ == "__main__":
    unittest.main()
