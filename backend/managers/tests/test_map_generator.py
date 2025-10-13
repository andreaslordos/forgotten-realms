"""
Comprehensive tests for map_generator module.

Tests cover:
- generate_3x3_grid returns dict
- Correct number of rooms
- Room IDs, names, descriptions
- Room instances
- Exit connections
- Bidirectional exits
- Corner, edge, and center room exits
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.map_generator import generate_3x3_grid
from models.Room import Room


class MapGeneratorStructureTest(unittest.TestCase):
    """Test map_generator structure."""

    def setUp(self):
        """Set up rooms for tests."""
        self.rooms = generate_3x3_grid()

    def test_generate_3x3_grid_returns_dict(self):
        """Test generate_3x3_grid returns a dictionary."""
        self.assertIsInstance(self.rooms, dict)

    def test_generate_3x3_grid_returns_nine_rooms(self):
        """Test generate_3x3_grid returns exactly 9 rooms."""
        self.assertEqual(len(self.rooms), 9)

    def test_generate_3x3_grid_all_values_are_room_objects(self):
        """Test all values in returned dict are Room objects."""
        for room in self.rooms.values():
            self.assertIsInstance(room, Room)

    def test_generate_3x3_grid_has_correct_room_ids(self):
        """Test generate_3x3_grid creates correct room IDs."""
        expected_ids = [
            "room_0_0", "room_0_1", "room_0_2",
            "room_1_0", "room_1_1", "room_1_2",
            "room_2_0", "room_2_1", "room_2_2"
        ]

        for room_id in expected_ids:
            self.assertIn(room_id, self.rooms)

    def test_generate_3x3_grid_room_names_match_positions(self):
        """Test room names match their grid positions."""
        self.assertEqual(self.rooms["room_0_0"].name, "Room (0, 0)")
        self.assertEqual(self.rooms["room_1_2"].name, "Room (1, 2)")
        self.assertEqual(self.rooms["room_2_1"].name, "Room (2, 1)")

    def test_generate_3x3_grid_room_descriptions_match_positions(self):
        """Test room descriptions match their grid positions."""
        self.assertEqual(
            self.rooms["room_0_0"].description,
            "This is the room located at position (0, 0)."
        )
        self.assertEqual(
            self.rooms["room_1_1"].description,
            "This is the room located at position (1, 1)."
        )


class MapGeneratorCornerRoomsTest(unittest.TestCase):
    """Test corner rooms have correct exits."""

    def setUp(self):
        """Set up rooms for tests."""
        self.rooms = generate_3x3_grid()

    def test_top_left_corner_has_two_exits(self):
        """Test top-left corner (0,0) has south and east exits."""
        room = self.rooms["room_0_0"]
        self.assertEqual(len(room.exits), 2)
        self.assertIn("south", room.exits)
        self.assertIn("east", room.exits)
        self.assertNotIn("north", room.exits)
        self.assertNotIn("west", room.exits)

    def test_top_left_corner_exits_point_to_correct_rooms(self):
        """Test top-left corner exits point to correct rooms."""
        room = self.rooms["room_0_0"]
        self.assertEqual(room.exits["south"], "room_1_0")
        self.assertEqual(room.exits["east"], "room_0_1")

    def test_top_right_corner_has_two_exits(self):
        """Test top-right corner (0,2) has south and west exits."""
        room = self.rooms["room_0_2"]
        self.assertEqual(len(room.exits), 2)
        self.assertIn("south", room.exits)
        self.assertIn("west", room.exits)
        self.assertNotIn("north", room.exits)
        self.assertNotIn("east", room.exits)

    def test_top_right_corner_exits_point_to_correct_rooms(self):
        """Test top-right corner exits point to correct rooms."""
        room = self.rooms["room_0_2"]
        self.assertEqual(room.exits["south"], "room_1_2")
        self.assertEqual(room.exits["west"], "room_0_1")

    def test_bottom_left_corner_has_two_exits(self):
        """Test bottom-left corner (2,0) has north and east exits."""
        room = self.rooms["room_2_0"]
        self.assertEqual(len(room.exits), 2)
        self.assertIn("north", room.exits)
        self.assertIn("east", room.exits)
        self.assertNotIn("south", room.exits)
        self.assertNotIn("west", room.exits)

    def test_bottom_left_corner_exits_point_to_correct_rooms(self):
        """Test bottom-left corner exits point to correct rooms."""
        room = self.rooms["room_2_0"]
        self.assertEqual(room.exits["north"], "room_1_0")
        self.assertEqual(room.exits["east"], "room_2_1")

    def test_bottom_right_corner_has_two_exits(self):
        """Test bottom-right corner (2,2) has north and west exits."""
        room = self.rooms["room_2_2"]
        self.assertEqual(len(room.exits), 2)
        self.assertIn("north", room.exits)
        self.assertIn("west", room.exits)
        self.assertNotIn("south", room.exits)
        self.assertNotIn("east", room.exits)

    def test_bottom_right_corner_exits_point_to_correct_rooms(self):
        """Test bottom-right corner exits point to correct rooms."""
        room = self.rooms["room_2_2"]
        self.assertEqual(room.exits["north"], "room_1_2")
        self.assertEqual(room.exits["west"], "room_2_1")


class MapGeneratorEdgeRoomsTest(unittest.TestCase):
    """Test edge rooms have correct exits."""

    def setUp(self):
        """Set up rooms for tests."""
        self.rooms = generate_3x3_grid()

    def test_top_edge_room_has_three_exits(self):
        """Test top edge room (0,1) has three exits."""
        room = self.rooms["room_0_1"]
        self.assertEqual(len(room.exits), 3)
        self.assertIn("south", room.exits)
        self.assertIn("west", room.exits)
        self.assertIn("east", room.exits)
        self.assertNotIn("north", room.exits)

    def test_top_edge_room_exits_point_to_correct_rooms(self):
        """Test top edge room exits point to correct rooms."""
        room = self.rooms["room_0_1"]
        self.assertEqual(room.exits["south"], "room_1_1")
        self.assertEqual(room.exits["west"], "room_0_0")
        self.assertEqual(room.exits["east"], "room_0_2")

    def test_left_edge_room_has_three_exits(self):
        """Test left edge room (1,0) has three exits."""
        room = self.rooms["room_1_0"]
        self.assertEqual(len(room.exits), 3)
        self.assertIn("north", room.exits)
        self.assertIn("south", room.exits)
        self.assertIn("east", room.exits)
        self.assertNotIn("west", room.exits)

    def test_left_edge_room_exits_point_to_correct_rooms(self):
        """Test left edge room exits point to correct rooms."""
        room = self.rooms["room_1_0"]
        self.assertEqual(room.exits["north"], "room_0_0")
        self.assertEqual(room.exits["south"], "room_2_0")
        self.assertEqual(room.exits["east"], "room_1_1")

    def test_right_edge_room_has_three_exits(self):
        """Test right edge room (1,2) has three exits."""
        room = self.rooms["room_1_2"]
        self.assertEqual(len(room.exits), 3)
        self.assertIn("north", room.exits)
        self.assertIn("south", room.exits)
        self.assertIn("west", room.exits)
        self.assertNotIn("east", room.exits)

    def test_right_edge_room_exits_point_to_correct_rooms(self):
        """Test right edge room exits point to correct rooms."""
        room = self.rooms["room_1_2"]
        self.assertEqual(room.exits["north"], "room_0_2")
        self.assertEqual(room.exits["south"], "room_2_2")
        self.assertEqual(room.exits["west"], "room_1_1")

    def test_bottom_edge_room_has_three_exits(self):
        """Test bottom edge room (2,1) has three exits."""
        room = self.rooms["room_2_1"]
        self.assertEqual(len(room.exits), 3)
        self.assertIn("north", room.exits)
        self.assertIn("west", room.exits)
        self.assertIn("east", room.exits)
        self.assertNotIn("south", room.exits)

    def test_bottom_edge_room_exits_point_to_correct_rooms(self):
        """Test bottom edge room exits point to correct rooms."""
        room = self.rooms["room_2_1"]
        self.assertEqual(room.exits["north"], "room_1_1")
        self.assertEqual(room.exits["west"], "room_2_0")
        self.assertEqual(room.exits["east"], "room_2_2")


class MapGeneratorCenterRoomTest(unittest.TestCase):
    """Test center room has correct exits."""

    def setUp(self):
        """Set up rooms for tests."""
        self.rooms = generate_3x3_grid()

    def test_center_room_has_four_exits(self):
        """Test center room (1,1) has all four exits."""
        room = self.rooms["room_1_1"]
        self.assertEqual(len(room.exits), 4)
        self.assertIn("north", room.exits)
        self.assertIn("south", room.exits)
        self.assertIn("east", room.exits)
        self.assertIn("west", room.exits)

    def test_center_room_exits_point_to_correct_rooms(self):
        """Test center room exits point to correct rooms."""
        room = self.rooms["room_1_1"]
        self.assertEqual(room.exits["north"], "room_0_1")
        self.assertEqual(room.exits["south"], "room_2_1")
        self.assertEqual(room.exits["east"], "room_1_2")
        self.assertEqual(room.exits["west"], "room_1_0")


class MapGeneratorBidirectionalExitsTest(unittest.TestCase):
    """Test exits are bidirectional."""

    def setUp(self):
        """Set up rooms for tests."""
        self.rooms = generate_3x3_grid()

    def test_north_south_connections_are_bidirectional(self):
        """Test north-south connections are bidirectional."""
        # If room_0_0 has south exit to room_1_0...
        self.assertEqual(self.rooms["room_0_0"].exits["south"], "room_1_0")
        # Then room_1_0 should have north exit to room_0_0
        self.assertEqual(self.rooms["room_1_0"].exits["north"], "room_0_0")

    def test_east_west_connections_are_bidirectional(self):
        """Test east-west connections are bidirectional."""
        # If room_0_0 has east exit to room_0_1...
        self.assertEqual(self.rooms["room_0_0"].exits["east"], "room_0_1")
        # Then room_0_1 should have west exit to room_0_0
        self.assertEqual(self.rooms["room_0_1"].exits["west"], "room_0_0")

    def test_all_connections_are_bidirectional(self):
        """Test all connections in the grid are bidirectional."""
        for room_id, room in self.rooms.items():
            for direction, target_id in room.exits.items():
                target_room = self.rooms[target_id]

                # Get opposite direction
                opposite = {
                    "north": "south",
                    "south": "north",
                    "east": "west",
                    "west": "east"
                }[direction]

                # Check that target room has exit back to this room
                self.assertIn(opposite, target_room.exits,
                    f"{target_id} missing {opposite} exit back to {room_id}")
                self.assertEqual(target_room.exits[opposite], room_id,
                    f"{target_id}'s {opposite} exit doesn't point back to {room_id}")


if __name__ == "__main__":
    unittest.main()
