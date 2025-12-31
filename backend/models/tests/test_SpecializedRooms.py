"""
Comprehensive tests for SpecializedRooms module.

Tests cover:
- SwampRoom initialization
- handle_treasure_drop with points awarded
- handle_treasure_drop without points
- handle_treasure_drop moves item to destination
- Serialization (to_dict, from_dict)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.SpecializedRooms import SwampRoom
from models.Item import Item
from models.Room import Room


class SwampRoomInitializationTest(unittest.TestCase):
    """Test SwampRoom initialization."""

    def test_swamp_room_inherits_from_room(self):
        """Test SwampRoom is a subclass of Room."""
        swamp = SwampRoom(
            room_id="swamp1", name="The Swamp", description="A murky swamp"
        )
        self.assertIsInstance(swamp, Room)

    def test_swamp_room_sets_treasure_destination(self):
        """Test SwampRoom sets treasure_destination attribute."""
        swamp = SwampRoom(
            room_id="swamp1",
            name="The Swamp",
            description="A murky swamp",
            treasure_destination="treasure_room",
        )
        self.assertEqual(swamp.treasure_destination, "treasure_room")

    def test_swamp_room_sets_awards_points_true_by_default(self):
        """Test SwampRoom sets awards_points to True by default."""
        swamp = SwampRoom(
            room_id="swamp1", name="The Swamp", description="A murky swamp"
        )
        self.assertTrue(swamp.awards_points)

    def test_swamp_room_is_outdoor_by_default(self):
        """Test SwampRoom sets is_outdoor to True by default."""
        swamp = SwampRoom(
            room_id="swamp1", name="The Swamp", description="A murky swamp"
        )
        self.assertTrue(swamp.is_outdoor)


class SwampRoomTreasureDropTest(unittest.TestCase):
    """Test SwampRoom.handle_treasure_drop functionality."""

    def setUp(self):
        """Set up common test fixtures."""
        self.swamp = SwampRoom(
            room_id="swamp1",
            name="The Swamp",
            description="A murky swamp",
            treasure_destination="treasure_room",
            awards_points=True,
        )

        self.treasure_room = Room(
            room_id="treasure_room",
            name="Treasure Room",
            description="A room full of treasure",
        )

        self.game_state = Mock()
        self.game_state.get_room.return_value = self.treasure_room

        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.add_points = Mock(return_value=(100, "You gain 50 points!"))

        self.player_manager = Mock()
        self.player_manager.save_players = Mock()

        self.sio = AsyncMock()
        self.online_sessions = {}

    def test_handle_treasure_drop_moves_item_to_destination(self):
        """Test handle_treasure_drop moves item to treasure_destination."""
        treasure = Item(name="gold coin", id="gold_1", description="A shiny gold coin")
        treasure.value = 50

        success, message = self.swamp.handle_treasure_drop(
            treasure,
            self.player,
            self.game_state,
            self.player_manager,
            self.sio,
            self.online_sessions,
        )

        self.assertTrue(success)
        self.assertIn(treasure, self.treasure_room.items)

    def test_handle_treasure_drop_awards_points_when_enabled(self):
        """Test handle_treasure_drop awards points when awards_points is True."""
        treasure = Item(name="gold coin", id="gold_1", description="A shiny gold coin")
        treasure.value = 50

        success, message = self.swamp.handle_treasure_drop(
            treasure,
            self.player,
            self.game_state,
            self.player_manager,
            self.sio,
            self.online_sessions,
        )

        self.player.add_points.assert_called_once_with(
            50, self.sio, self.online_sessions, send_notification=False
        )

    def test_handle_treasure_drop_does_not_award_points_when_disabled(self):
        """Test handle_treasure_drop does not award points when awards_points is False."""
        self.swamp.awards_points = False

        treasure = Item(name="gold coin", id="gold_1", description="A shiny gold coin")
        treasure.value = 50

        success, message = self.swamp.handle_treasure_drop(
            treasure,
            self.player,
            self.game_state,
            self.player_manager,
            self.sio,
            self.online_sessions,
        )

        self.player.add_points.assert_not_called()

    def test_handle_treasure_drop_with_no_value(self):
        """Test handle_treasure_drop with item that has no value."""
        item = Item(name="rock", id="rock_1", description="A worthless rock")
        # No value attribute

        success, message = self.swamp.handle_treasure_drop(
            item,
            self.player,
            self.game_state,
            self.player_manager,
            self.sio,
            self.online_sessions,
        )

        self.assertTrue(success)
        self.player.add_points.assert_not_called()


class SwampRoomSerializationTest(unittest.TestCase):
    """Test SwampRoom serialization and deserialization."""

    def test_to_dict_includes_treasure_destination(self):
        """Test to_dict includes treasure_destination."""
        swamp = SwampRoom(
            room_id="swamp1",
            name="The Swamp",
            description="A murky swamp",
            treasure_destination="treasure_room",
            awards_points=True,
        )

        data = swamp.to_dict()

        self.assertEqual(data["treasure_destination"], "treasure_room")

    def test_to_dict_includes_awards_points(self):
        """Test to_dict includes awards_points."""
        swamp = SwampRoom(
            room_id="swamp1",
            name="The Swamp",
            description="A murky swamp",
            treasure_destination="treasure_room",
            awards_points=False,
        )

        data = swamp.to_dict()

        self.assertFalse(data["awards_points"])

    def test_to_dict_includes_room_type_as_swamp(self):
        """Test to_dict includes room_type as 'swamp'."""
        swamp = SwampRoom(
            room_id="swamp1", name="The Swamp", description="A murky swamp"
        )

        data = swamp.to_dict()

        self.assertEqual(data["room_type"], "swamp")

    def test_from_dict_creates_swamp_room(self):
        """Test from_dict creates SwampRoom instance."""
        data = {
            "room_id": "swamp1",
            "name": "The Swamp",
            "description": "A murky swamp",
            "exits": {"north": "room1"},
            "treasure_destination": "treasure_room",
            "awards_points": True,
        }

        swamp = SwampRoom.from_dict(data)

        self.assertIsInstance(swamp, SwampRoom)
        self.assertEqual(swamp.room_id, "swamp1")
        self.assertEqual(swamp.name, "The Swamp")
        self.assertEqual(swamp.treasure_destination, "treasure_room")
        self.assertTrue(swamp.awards_points)

    def test_serialization_roundtrip(self):
        """Test SwampRoom can be serialized and deserialized."""
        original = SwampRoom(
            room_id="swamp1",
            name="The Swamp",
            description="A murky swamp",
            exits={"north": "room1", "south": "room2"},
            treasure_destination="treasure_room",
            awards_points=False,
        )

        data = original.to_dict()
        restored = SwampRoom.from_dict(data)

        self.assertEqual(restored.room_id, original.room_id)
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.description, original.description)
        self.assertEqual(restored.exits, original.exits)
        self.assertEqual(restored.treasure_destination, original.treasure_destination)
        self.assertEqual(restored.awards_points, original.awards_points)


class SwampRoomItemsTest(unittest.TestCase):
    """Test SwampRoom handles items correctly."""

    def test_swamp_room_can_add_items(self):
        """Test SwampRoom can add items like regular Room."""
        swamp = SwampRoom(
            room_id="swamp1", name="The Swamp", description="A murky swamp"
        )

        item = Item(name="bronze key", id="key_1", description="A key")

        swamp.add_item(item)

        self.assertIn(item, swamp.items)

    def test_swamp_room_can_remove_items(self):
        """Test SwampRoom can remove items like regular Room."""
        swamp = SwampRoom(
            room_id="swamp1", name="The Swamp", description="A murky swamp"
        )

        item = Item(name="bronze key", id="key_1", description="A key")

        swamp.add_item(item)
        swamp.remove_item(item)

        self.assertNotIn(item, swamp.items)


if __name__ == "__main__":
    unittest.main()
