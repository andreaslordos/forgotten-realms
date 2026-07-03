# backend/tests/test_golden_door_worldgen.py
"""World-generation integration tests for the golden door registry."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.world import generate_world
from services.golden_doors import DOOR_REGISTRY, reset_doors
from services.quest_items import clear_quest_item_registry

EXPECTED_DOORS = {"tunnel", "barrow", "undercrypt"}


class GoldenDoorWorldgenTest(unittest.TestCase):
    """Test generate_world registers exactly the shipped golden doors."""

    def tearDown(self):
        """Clear world-build registries so other tests stay independent."""
        reset_doors()
        clear_quest_item_registry()

    def test_generate_world_registers_expected_doors(self):
        """Test the world build registers exactly the three known doors."""
        # Act
        generate_world(None)

        # Assert
        self.assertEqual(set(DOOR_REGISTRY.keys()), EXPECTED_DOORS)
        for state in DOOR_REGISTRY.values():
            self.assertEqual(state.status, "sealed")

    def test_generate_world_places_door_item_in_each_door_room(self):
        """Test every registered door room contains a 'golden door' item."""
        # Act
        rooms = generate_world(None)

        # Assert
        for door_id, state in DOOR_REGISTRY.items():
            room = rooms[state.room_id]
            item_names = [getattr(item, "name", "") for item in room.items]
            self.assertIn(
                "golden door",
                item_names,
                f"door '{door_id}' room {state.room_id} has no golden door",
            )

    def test_generate_world_twice_does_not_duplicate_registry(self):
        """Test rebuilding the world resets rather than duplicates doors."""
        # Act
        generate_world(None)
        generate_world(None)

        # Assert
        self.assertEqual(set(DOOR_REGISTRY.keys()), EXPECTED_DOORS)
        self.assertEqual(len(DOOR_REGISTRY), 3)


if __name__ == "__main__":
    unittest.main()
