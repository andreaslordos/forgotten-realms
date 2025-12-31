"""
Tests for village_generator module.

Tests cover:
- compute_swamp_paths function
"""

import sys
import unittest
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.village_generator import compute_swamp_paths
from models.Room import Room


class ComputeSwampPathsTest(unittest.TestCase):
    """Test compute_swamp_paths functionality."""

    def test_compute_swamp_paths_sets_direction_for_outdoor_rooms(self):
        """Test compute_swamp_paths sets swamp_direction on outdoor rooms."""
        rooms: Dict[str, Room] = {
            "lake": Room("lake", "Lake", "A lake", exits={"south": "camp"}),
            "camp": Room(
                "camp", "Camp", "A camp", exits={"north": "lake"}, is_outdoor=True
            ),
        }

        compute_swamp_paths(rooms)

        self.assertEqual(rooms["camp"].swamp_direction, "north")

    def test_compute_swamp_paths_does_not_set_for_indoor_rooms(self):
        """Test compute_swamp_paths does not set swamp_direction on indoor rooms."""
        rooms: Dict[str, Room] = {
            "lake": Room("lake", "Lake", "A lake", exits={"south": "tavern"}),
            "tavern": Room(
                "tavern",
                "Tavern",
                "A tavern",
                exits={"north": "lake"},
                is_outdoor=False,
            ),
        }

        compute_swamp_paths(rooms)

        self.assertIsNone(rooms["tavern"].swamp_direction)

    def test_compute_swamp_paths_handles_chain_of_rooms(self):
        """Test compute_swamp_paths correctly computes paths through multiple rooms."""
        rooms: Dict[str, Room] = {
            "lake": Room("lake", "Lake", "A lake", exits={"south": "camp"}),
            "camp": Room(
                "camp",
                "Camp",
                "A camp",
                exits={"north": "lake", "south": "road"},
                is_outdoor=True,
            ),
            "road": Room(
                "road",
                "Road",
                "A road",
                exits={"north": "camp", "south": "square"},
                is_outdoor=True,
            ),
            "square": Room(
                "square",
                "Square",
                "A square",
                exits={"north": "road"},
                is_outdoor=True,
            ),
        }

        compute_swamp_paths(rooms)

        # Each room should point toward the lake
        self.assertEqual(rooms["camp"].swamp_direction, "north")
        self.assertEqual(rooms["road"].swamp_direction, "north")
        self.assertEqual(rooms["square"].swamp_direction, "north")

    def test_compute_swamp_paths_handles_disconnected_rooms(self):
        """Test compute_swamp_paths handles rooms that can't reach the lake."""
        rooms: Dict[str, Room] = {
            "lake": Room("lake", "Lake", "A lake", exits={"south": "camp"}),
            "camp": Room(
                "camp", "Camp", "A camp", exits={"north": "lake"}, is_outdoor=True
            ),
            "isolated": Room(
                "isolated",
                "Isolated",
                "Isolated area",
                exits={},
                is_outdoor=True,
            ),
        }

        compute_swamp_paths(rooms)

        self.assertEqual(rooms["camp"].swamp_direction, "north")
        self.assertIsNone(rooms["isolated"].swamp_direction)

    def test_compute_swamp_paths_handles_missing_lake(self):
        """Test compute_swamp_paths handles case when lake doesn't exist."""
        rooms: Dict[str, Room] = {
            "square": Room("square", "Square", "A square", exits={}, is_outdoor=True),
        }

        # Should not raise an error
        compute_swamp_paths(rooms)

        self.assertIsNone(rooms["square"].swamp_direction)


if __name__ == "__main__":
    unittest.main()
