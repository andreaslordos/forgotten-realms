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
            exits=exits,
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

        def condition(game_state):
            return False

        self.room.add_hidden_item(self.hidden_item, condition)

        self.assertIn("key_1", self.room.hidden_items)

    def test_get_items_hides_items_when_condition_false(self):
        """Test that hidden items are not visible when condition is false."""

        def condition(game_state):
            return False

        self.room.add_hidden_item(self.hidden_item, condition)

        # Create a dummy game state
        game_state = GameState()

        visible_items = self.room.get_items(game_state)

        self.assertNotIn(self.hidden_item, visible_items)

    def test_get_items_shows_items_when_condition_true(self):
        """Test that hidden items become visible when condition is true."""

        def condition(game_state):
            return True

        self.room.add_hidden_item(self.hidden_item, condition)

        game_state = GameState()

        visible_items = self.room.get_items(game_state)

        self.assertIn(self.hidden_item, visible_items)

    def test_get_items_evaluates_state_based_condition(self):
        """Test hidden item with condition based on game state."""

        # Item appears only if a flag is set in game state
        def condition(gs):
            return hasattr(gs, "door_opened") and gs.door_opened

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

        def condition(gs):
            return True

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
            "west": "room_w",
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
            "out": "courtyard",
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
            "items": [],
        }

        room = Room.from_dict(data)

        self.assertEqual(room.room_id, "r1")
        self.assertEqual(room.name, "Library")
        self.assertEqual(room.description, "A dusty library")
        self.assertEqual(room.exits["west"], "hallway")

    def test_to_dict_from_dict_round_trip(self):
        """Test complete serialization cycle."""
        original = Room(
            "test", "Test Room", "A test room", exits={"north": "n", "south": "s"}
        )

        serialized = original.to_dict()
        reconstructed = Room.from_dict(serialized)

        self.assertEqual(reconstructed.room_id, original.room_id)
        self.assertEqual(reconstructed.name, original.name)
        self.assertEqual(reconstructed.description, original.description)
        self.assertEqual(reconstructed.exits, original.exits)


class RoomDarknessTest(unittest.TestCase):
    """Test room darkness property."""

    def test___init___defaults_is_dark_to_false(self):
        """Test room defaults to not dark."""
        room = Room("room1", "Test Room", "A test room")

        self.assertFalse(room.is_dark)

    def test___init___accepts_is_dark_parameter(self):
        """Test creating a dark room."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)

        self.assertTrue(room.is_dark)

    def test_to_dict_includes_is_dark(self):
        """Test serialization includes is_dark property."""
        room = Room("room1", "Dark Room", "A dark room", is_dark=True)
        room_dict = room.to_dict()

        self.assertIn("is_dark", room_dict)
        self.assertTrue(room_dict["is_dark"])

    def test_from_dict_restores_is_dark(self):
        """Test deserialization restores is_dark property."""
        data = {
            "room_id": "cellar",
            "name": "Dark Cellar",
            "description": "A dark cellar",
            "exits": {},
            "items": [],
            "is_dark": True,
        }

        room = Room.from_dict(data)

        self.assertTrue(room.is_dark)

    def test_to_dict_from_dict_round_trip_with_is_dark(self):
        """Test serialization cycle preserves is_dark."""
        original = Room("dungeon", "Dark Dungeon", "A dark dungeon", is_dark=True)

        serialized = original.to_dict()
        reconstructed = Room.from_dict(serialized)

        self.assertEqual(reconstructed.is_dark, original.is_dark)


class RoomOutdoorTest(unittest.TestCase):
    """Test room outdoor and swamp direction properties."""

    def test___init___defaults_is_outdoor_to_false(self):
        """Test room defaults to indoor."""
        room = Room("room1", "Test Room", "A test room")

        self.assertFalse(room.is_outdoor)

    def test___init___accepts_is_outdoor_parameter(self):
        """Test creating an outdoor room."""
        room = Room("square", "Village Square", "A square", is_outdoor=True)

        self.assertTrue(room.is_outdoor)

    def test___init___defaults_swamp_direction_to_none(self):
        """Test swamp_direction defaults to None."""
        room = Room("room1", "Test Room", "A test room")

        self.assertIsNone(room.swamp_direction)

    def test_swamp_direction_can_be_set(self):
        """Test swamp_direction can be assigned."""
        room = Room("square", "Village Square", "A square", is_outdoor=True)
        room.swamp_direction = "south"

        self.assertEqual(room.swamp_direction, "south")

    def test_to_dict_includes_is_outdoor(self):
        """Test serialization includes is_outdoor property."""
        room = Room("square", "Village Square", "A square", is_outdoor=True)
        room_dict = room.to_dict()

        self.assertIn("is_outdoor", room_dict)
        self.assertTrue(room_dict["is_outdoor"])

    def test_to_dict_includes_swamp_direction(self):
        """Test serialization includes swamp_direction property."""
        room = Room("square", "Village Square", "A square", is_outdoor=True)
        room.swamp_direction = "south"
        room_dict = room.to_dict()

        self.assertIn("swamp_direction", room_dict)
        self.assertEqual(room_dict["swamp_direction"], "south")

    def test_from_dict_restores_is_outdoor(self):
        """Test deserialization restores is_outdoor property."""
        data = {
            "room_id": "square",
            "name": "Village Square",
            "description": "A square",
            "exits": {},
            "items": [],
            "is_outdoor": True,
        }

        room = Room.from_dict(data)

        self.assertTrue(room.is_outdoor)

    def test_from_dict_restores_swamp_direction(self):
        """Test deserialization restores swamp_direction property."""
        data = {
            "room_id": "square",
            "name": "Village Square",
            "description": "A square",
            "exits": {},
            "items": [],
            "is_outdoor": True,
            "swamp_direction": "south",
        }

        room = Room.from_dict(data)

        self.assertEqual(room.swamp_direction, "south")

    def test_to_dict_from_dict_round_trip_with_outdoor_properties(self):
        """Test serialization cycle preserves outdoor properties."""
        original = Room("square", "Village Square", "A square", is_outdoor=True)
        original.swamp_direction = "south"

        serialized = original.to_dict()
        reconstructed = Room.from_dict(serialized)

        self.assertEqual(reconstructed.is_outdoor, original.is_outdoor)
        self.assertEqual(reconstructed.swamp_direction, original.swamp_direction)


class RoomSpeechTriggersTest(unittest.TestCase):
    """Test room speech trigger functionality."""

    def test___init___defaults_speech_triggers_to_empty_dict(self) -> None:
        """Test room defaults to no speech triggers."""
        room = Room("room1", "Test Room", "A test room")

        self.assertEqual(room.speech_triggers, {})

    def test_add_speech_trigger_adds_trigger_to_dict(self) -> None:
        """Test adding a speech trigger."""
        room = Room("room1", "Test Room", "A test room")

        room.add_speech_trigger(
            keyword="password",
            message="The door opens!",
        )

        self.assertIn("password", room.speech_triggers)
        self.assertEqual(len(room.speech_triggers["password"]), 1)
        self.assertEqual(
            room.speech_triggers["password"][0]["message"], "The door opens!"
        )

    def test_add_speech_trigger_converts_keyword_to_lowercase(self) -> None:
        """Test that keywords are stored in lowercase."""
        room = Room("room1", "Test Room", "A test room")

        room.add_speech_trigger(keyword="PASSWORD", message="Success!")

        self.assertIn("password", room.speech_triggers)
        self.assertNotIn("PASSWORD", room.speech_triggers)

    def test_add_speech_trigger_with_all_parameters(self) -> None:
        """Test adding trigger with all optional parameters."""

        def mock_effect(
            p: object, gs: object, pm: object, os: object, sio: object, u: object
        ) -> None:
            pass

        def mock_condition(p: object, gs: object) -> bool:
            return True

        room = Room("room1", "Test Room", "A test room")

        room.add_speech_trigger(
            keyword="riddle",
            message="Correct!",
            effect_fn=mock_effect,
            conditional_fn=mock_condition,
            one_time=False,
        )

        trigger = room.speech_triggers["riddle"][0]
        self.assertEqual(trigger["message"], "Correct!")
        self.assertEqual(trigger["effect_fn"], mock_effect)
        self.assertEqual(trigger["conditional_fn"], mock_condition)
        self.assertFalse(trigger["one_time"])
        self.assertFalse(trigger["triggered"])

    def test_add_speech_trigger_defaults_one_time_to_true(self) -> None:
        """Test that one_time defaults to True."""
        room = Room("room1", "Test Room", "A test room")

        room.add_speech_trigger(keyword="word", message="Message")

        self.assertTrue(room.speech_triggers["word"][0]["one_time"])

    def test_add_speech_trigger_initializes_triggered_to_false(self) -> None:
        """Test that triggered starts as False."""
        room = Room("room1", "Test Room", "A test room")

        room.add_speech_trigger(keyword="word", message="Message")

        self.assertFalse(room.speech_triggers["word"][0]["triggered"])

    def test_add_multiple_speech_triggers(self) -> None:
        """Test adding multiple triggers to same room."""
        room = Room("room1", "Test Room", "A test room")

        room.add_speech_trigger(keyword="word1", message="Message 1")
        room.add_speech_trigger(keyword="word2", message="Message 2")

        self.assertEqual(len(room.speech_triggers), 2)
        self.assertIn("word1", room.speech_triggers)
        self.assertIn("word2", room.speech_triggers)

    def test_add_multiple_triggers_for_same_keyword(self) -> None:
        """Test adding multiple triggers for the same keyword with different conditions."""

        def condition_a(p: object, gs: object) -> bool:
            return True

        def condition_b(p: object, gs: object) -> bool:
            return False

        room = Room("room1", "Test Room", "A test room")

        room.add_speech_trigger(
            keyword="lathander",
            message="The mists part!",
            conditional_fn=condition_a,
        )
        room.add_speech_trigger(
            keyword="lathander",
            message="Nothing happens.",
            conditional_fn=condition_b,
        )

        # Should have one keyword with two triggers
        self.assertEqual(len(room.speech_triggers), 1)
        self.assertIn("lathander", room.speech_triggers)
        self.assertEqual(len(room.speech_triggers["lathander"]), 2)

        # Verify both triggers are stored
        self.assertEqual(
            room.speech_triggers["lathander"][0]["message"], "The mists part!"
        )
        self.assertEqual(
            room.speech_triggers["lathander"][1]["message"], "Nothing happens."
        )


if __name__ == "__main__":
    unittest.main()
