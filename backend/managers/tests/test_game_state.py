"""
Comprehensive tests for GameState manager.

Tests cover:
- Room management in GameState
- Player room tracking and movement
- Navigation validation and edge cases
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Room import Room
from models.Player import Player
from managers.game_state import GameState


class GameStateRoomManagementTest(unittest.TestCase):
    """Test GameState management of rooms."""

    def setUp(self):
        """Set up test game state."""
        self.game_state = GameState()

    def test_add_room_adds_to_rooms_dict(self):
        """Test adding rooms to game state."""
        room = Room("room1", "First Room", "A room")

        self.game_state.add_room(room)

        self.assertIn("room1", self.game_state.rooms)
        self.assertEqual(self.game_state.rooms["room1"], room)

    def test_add_room_multiple_times(self):
        """Test adding multiple rooms to game state."""
        room1 = Room("room1", "Room 1", "First room")
        room2 = Room("room2", "Room 2", "Second room")
        room3 = Room("room3", "Room 3", "Third room")

        self.game_state.add_room(room1)
        self.game_state.add_room(room2)
        self.game_state.add_room(room3)

        self.assertEqual(len(self.game_state.rooms), 3)

    def test_get_room_returns_room(self):
        """Test retrieving rooms from game state."""
        room = Room("test", "Test Room", "A test room")
        self.game_state.add_room(room)

        retrieved = self.game_state.get_room("test")

        self.assertEqual(retrieved, room)

    def test_get_room_nonexistent_returns_none(self):
        """Test retrieving a room that doesn't exist."""
        retrieved = self.game_state.get_room("nonexistent")

        self.assertIsNone(retrieved)

    def test_get_room_supports_graph_navigation(self):
        """Test navigating a connected graph of rooms."""
        # Create connected rooms
        room1 = Room("r1", "Room 1", "First room", exits={"east": "r2"})
        room2 = Room("r2", "Room 2", "Second room", exits={"west": "r1", "north": "r3"})
        room3 = Room("r3", "Room 3", "Third room", exits={"south": "r2"})

        self.game_state.add_room(room1)
        self.game_state.add_room(room2)
        self.game_state.add_room(room3)

        # Navigate from room1 to room2
        current = self.game_state.get_room("r1")
        self.assertEqual(current.room_id, "r1")

        next_room_id = current.exits["east"]
        current = self.game_state.get_room(next_room_id)
        self.assertEqual(current.room_id, "r2")

        # Navigate from room2 to room3
        next_room_id = current.exits["north"]
        current = self.game_state.get_room(next_room_id)
        self.assertEqual(current.room_id, "r3")


class PlayerRoomTrackingTest(unittest.TestCase):
    """Test player room tracking and movement."""

    def setUp(self):
        """Set up test player and rooms."""
        self.player = Player("Traveler")
        self.game_state = GameState()

        self.room1 = Room("r1", "Start", "Starting room", exits={"north": "r2"})
        self.room2 = Room("r2", "Destination", "End room", exits={"south": "r1"})

        self.game_state.add_room(self.room1)
        self.game_state.add_room(self.room2)

    def test_current_room_property_initialized(self):
        """Test that new player can have initial room."""
        # Player is initialized with a spawn_room
        self.assertIsNotNone(self.player.current_room)

    def test_set_current_room_updates_room(self):
        """Test setting player's current room."""
        self.player.set_current_room("r1")

        self.assertEqual(self.player.current_room, "r1")

    def test_set_current_room_enables_movement(self):
        """Test player moving between connected rooms."""
        self.player.set_current_room("r1")
        self.assertEqual(self.player.current_room, "r1")

        # Move to room2
        current_room = self.game_state.get_room(self.player.current_room)
        next_room_id = current_room.exits["north"]
        self.player.set_current_room(next_room_id)

        self.assertEqual(self.player.current_room, "r2")

    def test_add_visited_adds_to_set(self):
        """Test tracking rooms the player has visited."""
        self.player.set_current_room("r1")
        self.player.add_visited("r1")

        self.player.set_current_room("r2")
        self.player.add_visited("r2")

        self.assertIn("r1", self.player.visited)
        self.assertIn("r2", self.player.visited)
        self.assertEqual(len(self.player.visited), 2)

    def test_add_visited_prevents_duplicates(self):
        """Test that visited rooms set doesn't have duplicates."""
        self.player.add_visited("r1")
        self.player.add_visited("r1")
        self.player.add_visited("r1")

        self.assertEqual(len(self.player.visited), 1)


class NavigationValidationTest(unittest.TestCase):
    """Test navigation validation and edge cases."""

    def setUp(self):
        """Set up test rooms."""
        self.game_state = GameState()
        self.room = Room("locked_room", "Locked Room", "A locked room")
        self.game_state.add_room(self.room)

    def test_invalid_exit_direction(self):
        """Test attempting to use an exit that doesn't exist."""
        self.assertNotIn("north", self.room.exits)

    def test_get_room_nonexistent_exit_returns_none(self):
        """Test exit pointing to a room that doesn't exist."""
        self.room.exits["north"] = "nonexistent_room"

        next_room = self.game_state.get_room("nonexistent_room")

        self.assertIsNone(next_room)

    def test_get_room_supports_circular_navigation(self):
        """Test circular room connections."""
        room1 = Room("r1", "Room 1", "First", exits={"east": "r2"})
        room2 = Room("r2", "Room 2", "Second", exits={"west": "r1"})

        self.game_state.add_room(room1)
        self.game_state.add_room(room2)

        # Go east then west should return to start
        current = self.game_state.get_room("r1")
        current = self.game_state.get_room(current.exits["east"])
        self.assertEqual(current.room_id, "r2")

        current = self.game_state.get_room(current.exits["west"])
        self.assertEqual(current.room_id, "r1")


if __name__ == "__main__":
    unittest.main()
