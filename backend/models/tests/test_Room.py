"""
Comprehensive tests for Room model.

Tests cover:
- Room initialization and attributes
- Item management in rooms
- Hidden items with conditional visibility
- Exit management
- Room serialization/deserialization
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Room import Room
from models.Item import Item
from managers.game_state import GameState


class RoomInitializationTest(unittest.TestCase):
    """Test room creation and basic attributes."""

    def test___init___with_all_parameters(self):
        """Test creating a room with all parameters."""
        exits = {"north": "room2", "east": "room3"}
        room = Room(
            room_id="room1",
            name="Test Chamber",
            description="A dark chamber",
            exits=exits
        )

        self.assertEqual(room.room_id, "room1")
        self.assertEqual(room.name, "Test Chamber")
        self.assertEqual(room.description, "A dark chamber")
        self.assertEqual(room.exits, exits)
        self.assertIsInstance(room.items, list)
        self.assertEqual(len(room.items), 0)

    def test___init___without_exits(self):
        """Test creating a room with no exits."""
        room = Room("room1", "Empty Room", "An empty room")

        self.assertEqual(room.exits, {})

    def test___repr___includes_id_and_exits(self):
        """Test room string representation."""
        room = Room("room1", "Hall", "A grand hall", exits={"south": "room2"})
        repr_str = repr(room)

        self.assertIn("room1", repr_str)
        self.assertIn("exits", repr_str)


class RoomItemManagementTest(unittest.TestCase):
    """Test item management within rooms."""

    def setUp(self):
        """Set up test room and items."""
        self.room = Room("test_room", "Test Room", "A test room")
        self.item1 = Item("Sword", "sword_1", "A sharp sword", weight=5)
        self.item2 = Item("Shield", "shield_1", "A sturdy shield", weight=8)

    def test_add_item_adds_to_items_list(self):
        """Test adding items to a room."""
        self.room.add_item(self.item1)

        self.assertEqual(len(self.room.items), 1)
        self.assertIn(self.item1, self.room.items)

    def test_add_item_multiple_times(self):
        """Test adding multiple items to a room."""
        self.room.add_item(self.item1)
        self.room.add_item(self.item2)

        self.assertEqual(len(self.room.items), 2)
        self.assertIn(self.item1, self.room.items)
        self.assertIn(self.item2, self.room.items)

    def test_remove_item_removes_from_list(self):
        """Test removing items from a room."""
        self.room.add_item(self.item1)
        self.room.add_item(self.item2)

        success = self.room.remove_item(self.item1)

        self.assertTrue(success)
        self.assertEqual(len(self.room.items), 1)
        self.assertNotIn(self.item1, self.room.items)
        self.assertIn(self.item2, self.room.items)

    def test_remove_item_nonexistent_returns_false(self):
        """Test removing an item that's not in the room."""
        success = self.room.remove_item(self.item1)

        self.assertFalse(success)

    def test_get_items_without_game_state(self):
        """Test getting items without game state (only visible items)."""
        self.room.add_item(self.item1)

        items = self.room.get_items()

        self.assertEqual(len(items), 1)
        self.assertIn(self.item1, items)


class RoomHiddenItemsTest(unittest.TestCase):
    """Test hidden items with conditional visibility."""

    def setUp(self):
        """Set up test room and items."""
        self.room = Room("secret_room", "Secret Room", "A room with secrets")
        self.hidden_item = Item("Key", "key_1", "A golden key", weight=0.5)

    def test_add_hidden_item_adds_to_hidden_items_dict(self):
        """Test adding hidden items to a room."""
        condition = lambda game_state: False

        self.room.add_hidden_item(self.hidden_item, condition)

        self.assertIn("key_1", self.room.hidden_items)

    def test_get_items_hides_items_when_condition_false(self):
        """Test that hidden items are not visible when condition is false."""
        condition = lambda game_state: False
        self.room.add_hidden_item(self.hidden_item, condition)

        # Create a dummy game state
        game_state = GameState()

        visible_items = self.room.get_items(game_state)

        self.assertNotIn(self.hidden_item, visible_items)

    def test_get_items_shows_items_when_condition_true(self):
        """Test that hidden items become visible when condition is true."""
        condition = lambda game_state: True
        self.room.add_hidden_item(self.hidden_item, condition)

        game_state = GameState()

        visible_items = self.room.get_items(game_state)

        self.assertIn(self.hidden_item, visible_items)

    def test_get_items_evaluates_state_based_condition(self):
        """Test hidden item with condition based on game state."""
        # Item appears only if a flag is set in game state
        condition = lambda gs: hasattr(gs, 'door_opened') and gs.door_opened

        self.room.add_hidden_item(self.hidden_item, condition)

        game_state = GameState()

        # Initially hidden
        visible_items = self.room.get_items(game_state)
        self.assertNotIn(self.hidden_item, visible_items)

        # After setting flag, item becomes visible
        game_state.door_opened = True
        visible_items = self.room.get_items(game_state)
        self.assertIn(self.hidden_item, visible_items)

    def test_remove_hidden_item_removes_from_dict(self):
        """Test removing hidden items."""
        condition = lambda gs: True
        self.room.add_hidden_item(self.hidden_item, condition)

        success = self.room.remove_hidden_item("key_1")

        self.assertTrue(success)
        self.assertNotIn("key_1", self.room.hidden_items)

    def test_remove_hidden_item_nonexistent_returns_false(self):
        """Test removing a hidden item that doesn't exist."""
        success = self.room.remove_hidden_item("nonexistent")

        self.assertFalse(success)

    def test_get_items_includes_visible_and_hidden(self):
        """Test room with both visible and hidden items."""
        visible_item = Item("Torch", "torch_1", "A burning torch")
        hidden_item = Item("Gem", "gem_1", "A hidden gem")

        self.room.add_item(visible_item)
        self.room.add_hidden_item(hidden_item, lambda gs: True)

        game_state = GameState()
        all_items = self.room.get_items(game_state)

        self.assertEqual(len(all_items), 2)
        self.assertIn(visible_item, all_items)
        self.assertIn(hidden_item, all_items)


class RoomExitsTest(unittest.TestCase):
    """Test room exit management and navigation."""

    def test_room_with_single_exit(self):
        """Test room with one exit."""
        room = Room("room1", "Room 1", "First room", exits={"north": "room2"})

        self.assertEqual(len(room.exits), 1)
        self.assertEqual(room.exits["north"], "room2")

    def test_room_with_multiple_exits(self):
        """Test room with multiple exits."""
        exits = {
            "north": "room_n",
            "south": "room_s",
            "east": "room_e",
            "west": "room_w"
        }
        room = Room("center", "Central Hub", "A crossroads", exits=exits)

        self.assertEqual(len(room.exits), 4)
        self.assertEqual(room.exits["north"], "room_n")
        self.assertEqual(room.exits["south"], "room_s")
        self.assertEqual(room.exits["east"], "room_e")
        self.assertEqual(room.exits["west"], "room_w")

    def test_room_with_special_exits(self):
        """Test room with special direction exits (up, down, in, out)."""
        exits = {
            "up": "tower_top",
            "down": "dungeon",
            "in": "building",
            "out": "courtyard"
        }
        room = Room("tower", "Tower Base", "Base of a tower", exits=exits)

        self.assertEqual(room.exits["up"], "tower_top")
        self.assertEqual(room.exits["down"], "dungeon")

    def test_modify_exits_dynamically(self):
        """Test that exits can be modified at runtime."""
        room = Room("room1", "Room", "A room", exits={"north": "room2"})

        # Add new exit
        room.exits["south"] = "room3"
        self.assertEqual(room.exits["south"], "room3")

        # Remove exit
        del room.exits["north"]
        self.assertNotIn("north", room.exits)


class RoomSerializationTest(unittest.TestCase):
    """Test room serialization and deserialization."""

    def test_to_dict_includes_all_attributes(self):
        """Test converting room to dictionary."""
        exits = {"north": "room2", "east": "room3"}
        room = Room("room1", "Test Room", "A test room", exits=exits)
        room.add_item(Item("Torch", "torch_1", "A torch", weight=1))

        room_dict = room.to_dict()

        self.assertEqual(room_dict["room_id"], "room1")
        self.assertEqual(room_dict["name"], "Test Room")
        self.assertEqual(room_dict["description"], "A test room")
        self.assertEqual(room_dict["exits"], exits)
        self.assertEqual(len(room_dict["items"]), 1)

    def test_from_dict_creates_room(self):
        """Test creating room from dictionary."""
        data = {
            "room_id": "r1",
            "name": "Library",
            "description": "A dusty library",
            "exits": {"west": "hallway"},
            "items": []
        }

        room = Room.from_dict(data)

        self.assertEqual(room.room_id, "r1")
        self.assertEqual(room.name, "Library")
        self.assertEqual(room.description, "A dusty library")
        self.assertEqual(room.exits["west"], "hallway")

    def test_to_dict_from_dict_round_trip(self):
        """Test complete serialization cycle."""
        original = Room(
            "test",
            "Test Room",
            "A test room",
            exits={"north": "n", "south": "s"}
        )

        serialized = original.to_dict()
        reconstructed = Room.from_dict(serialized)

        self.assertEqual(reconstructed.room_id, original.room_id)
        self.assertEqual(reconstructed.name, original.name)
        self.assertEqual(reconstructed.description, original.description)
        self.assertEqual(reconstructed.exits, original.exits)


if __name__ == "__main__":
    unittest.main()
