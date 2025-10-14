"""
Comprehensive tests for darkness_utils module.

Tests cover:
- room_is_visible function with various lighting scenarios
- get_dark_room_description function
- Shared lighting mechanics (ground items, other players)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.darkness_utils import room_is_visible, get_dark_room_description
from models.Room import Room
from models.Player import Player
from models.Item import Item


class RoomIsVisibleTest(unittest.TestCase):
    """Test room_is_visible function for various lighting conditions."""

    def test_room_is_visible_returns_true_for_non_dark_room(self):
        """Test room_is_visible returns True for naturally lit rooms."""
        room = Room("room1", "Lit Room", "A lit room", is_dark=False)
        online_sessions = {}
        game_state = Mock()

        self.assertTrue(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_returns_true_for_room_without_is_dark_attribute(self):
        """Test room_is_visible returns True for rooms missing is_dark attribute."""
        room = Mock()
        room.room_id = "room1"
        del room.is_dark  # Simulate missing attribute
        online_sessions = {}
        game_state = Mock()

        self.assertTrue(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_returns_false_for_dark_room_with_no_light_sources(self):
        """Test room_is_visible returns False for dark room without any light."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        room.get_items = Mock(return_value=[])
        online_sessions = {}
        game_state = Mock()

        self.assertFalse(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_returns_true_with_light_emitting_item_on_ground(self):
        """Test room_is_visible returns True when light source is on ground."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        torch = Item("torch", "torch_1", "A torch", emits_light=True)
        room.items = [torch]
        online_sessions = {}
        game_state = Mock()

        self.assertTrue(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_returns_false_with_non_emitting_items_on_ground(self):
        """Test room_is_visible returns False when ground items don't emit light."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        sword = Item("sword", "sword_1", "A sword", emits_light=False)
        shield = Item("shield", "shield_1", "A shield", emits_light=False)
        room.items = [sword, shield]
        room.get_items = Mock(return_value=[sword, shield])
        online_sessions = {}
        game_state = Mock()

        self.assertFalse(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_returns_true_when_player_has_light_source(self):
        """Test room_is_visible returns True when a player in room has light."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        room.get_items = Mock(return_value=[])

        player = Player("TestPlayer")
        player.current_room = "room1"
        torch = Item("torch", "torch_1", "A torch", emits_light=True)
        player.inventory = [torch]

        online_sessions = {"sid1": {"player": player}}
        game_state = Mock()

        self.assertTrue(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_returns_false_when_player_has_no_light_source(self):
        """Test room_is_visible returns False when player has no light source."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        room.get_items = Mock(return_value=[])

        player = Player("TestPlayer")
        player.current_room = "room1"
        player.inventory = []  # No light source

        online_sessions = {"sid1": {"player": player}}
        game_state = Mock()

        self.assertFalse(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_ignores_players_in_different_rooms(self):
        """Test room_is_visible ignores players not in the same room."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        room.get_items = Mock(return_value=[])

        player_with_light = Player("PlayerWithLight")
        player_with_light.current_room = "room2"  # Different room
        torch = Item("torch", "torch_1", "A torch", emits_light=True)
        player_with_light.inventory = [torch]

        player_in_dark = Player("PlayerInDark")
        player_in_dark.current_room = "room1"
        player_in_dark.inventory = []

        online_sessions = {
            "sid1": {"player": player_with_light},
            "sid2": {"player": player_in_dark},
        }
        game_state = Mock()

        self.assertFalse(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_handles_shared_lighting_from_other_player(self):
        """Test room_is_visible with shared lighting from another player."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        room.get_items = Mock(return_value=[])

        player1 = Player("Player1")
        player1.current_room = "room1"
        player1.inventory = []  # No light

        player2 = Player("Player2")
        player2.current_room = "room1"
        torch = Item("torch", "torch_1", "A torch", emits_light=True)
        player2.inventory = [torch]  # Has light

        online_sessions = {
            "sid1": {"player": player1},
            "sid2": {"player": player2},
        }
        game_state = Mock()

        # Both players can see because player2 has light
        self.assertTrue(room_is_visible(room, online_sessions, game_state))

    def test_room_is_visible_handles_mixed_light_sources(self):
        """Test room_is_visible with both ground and inventory light sources."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        torch_on_ground = Item("torch", "torch_1", "A torch", emits_light=True)
        room.items = [torch_on_ground]

        player = Player("TestPlayer")
        player.current_room = "room1"
        lantern = Item("lantern", "lantern_1", "A lantern", emits_light=True)
        player.inventory = [lantern]

        online_sessions = {"sid1": {"player": player}}
        game_state = Mock()

        self.assertTrue(room_is_visible(room, online_sessions, game_state))


class GetDarkRoomDescriptionTest(unittest.TestCase):
    """Test get_dark_room_description function."""

    def test_get_dark_room_description_includes_room_name(self):
        """Test get_dark_room_description includes room name."""
        room = Room("cellar", "Dark Cellar", "A dark cellar", is_dark=True)

        description = get_dark_room_description(room)

        self.assertIn("Dark Cellar", description)

    def test_get_dark_room_description_includes_darkness_message(self):
        """Test get_dark_room_description includes darkness message."""
        room = Room("dungeon", "Dark Dungeon", "A dark dungeon", is_dark=True)

        description = get_dark_room_description(room)

        self.assertIn("The room is too dark to see anything", description)

    def test_get_dark_room_description_does_not_include_exits(self):
        """Test get_dark_room_description does not list exits."""
        room = Room(
            "room1",
            "Dark Room",
            "A dark room",
            exits={"north": "room2", "south": "room3"},
            is_dark=True,
        )

        description = get_dark_room_description(room)

        self.assertNotIn("north", description)
        self.assertNotIn("south", description)

    def test_get_dark_room_description_does_not_include_full_description(self):
        """Test get_dark_room_description doesn't include full room description."""
        room = Room(
            "room1",
            "Dark Room",
            "A detailed description of the room with many features.",
            is_dark=True,
        )

        description = get_dark_room_description(room)

        self.assertNotIn("A detailed description", description)
        self.assertNotIn("many features", description)

    def test_get_dark_room_description_format(self):
        """Test get_dark_room_description has correct format."""
        room = Room("cellar", "Dark Cellar", "A dark cellar", is_dark=True)

        description = get_dark_room_description(room)

        # Should have room name followed by darkness message
        lines = description.split("\n")
        self.assertEqual(lines[0], "Dark Cellar")
        self.assertEqual(lines[1], "The room is too dark to see anything.")


if __name__ == "__main__":
    unittest.main()
