# backend/services/tests/test_zone_injector.py
"""Tests for injecting a validated pocket-dimension zone into the world."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.game_state import GameState
from managers.mob_definitions import get_mob_definitions
from managers.mob_manager import MobManager
from models.Mobile import Mobile
from models.Room import Room
from services.zone_injector import inject_zone

PREFIX = "pd_t_"
FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "fallback_zones"
    / "hollow_reliquary.json"
)


def load_fixture():
    """Load the shipped fallback zone spec from disk."""
    with open(FIXTURE_PATH) as f:
        return json.load(f)


class InjectZoneTest(unittest.TestCase):
    """Test inject_zone materializes a zone behind a door room."""

    def setUp(self):
        """Set up a real world with a door room and a real mob manager."""
        self.spec = copy.deepcopy(load_fixture())
        self.game_state = GameState()
        self.door_room = Room("crypt", "Crypt", "A cold crypt.")
        self.game_state.add_room(self.door_room)
        self.mob_manager = MobManager()
        self.mob_manager.load_mob_definitions(get_mob_definitions())

    def _inject(self, mob_manager="default", **kwargs):
        manager = self.mob_manager if mob_manager == "default" else mob_manager
        return inject_zone(
            self.spec, PREFIX, self.game_state, manager, "crypt", **kwargs
        )

    def test_inject_zone_adds_all_rooms_to_game_state(self):
        """Test every zone room is registered under its namespaced id."""
        # Act
        self._inject()

        # Assert
        for room_spec in self.spec["rooms"]:
            room_id = f"{PREFIX}{room_spec['id']}"
            self.assertIsNotNone(self.game_state.get_room(room_id))

    def test_inject_zone_returns_namespaced_entry_id(self):
        """Test the return value is the namespaced entry room id."""
        # Act
        entry_id = self._inject()

        # Assert
        self.assertEqual(entry_id, "pd_t_threshold")

    def test_inject_zone_wires_door_room_in_exit(self):
        """Test the door room gains an 'in' exit to the entry room."""
        # Act
        self._inject()

        # Assert
        self.assertEqual(self.door_room.exits["in"], "pd_t_threshold")

    def test_inject_zone_wires_exit_room_out_to_door_room(self):
        """Test the zone's exit room gains an 'out' exit back to the door."""
        # Act
        self._inject()

        # Assert
        exit_room = self.game_state.get_room("pd_t_threshold")
        self.assertEqual(exit_room.exits["out"], "crypt")

    def test_inject_zone_honors_custom_door_direction(self):
        """Test a non-default door direction is used for the entry exit."""
        # Act
        self._inject(door_direction="down")

        # Assert
        self.assertEqual(self.door_room.exits["down"], "pd_t_threshold")
        self.assertNotIn("in", self.door_room.exits)

    def test_inject_zone_spawns_template_mobs(self):
        """Test a template mob is spawned into its namespaced room."""
        # Act
        self._inject()

        # Assert
        mobs = self.mob_manager.get_mobs_in_room("pd_t_ossuary")
        self.assertEqual(len(mobs), 1)
        self.assertEqual(mobs[0].name, "skeleton")

    def test_inject_zone_registers_and_spawns_custom_mobs(self):
        """Test a custom mob gets a runtime definition and is spawned."""
        # Act
        self._inject()

        # Assert: the second mob (index 1) is custom.
        self.assertIn("pd_t_mob_1", self.mob_manager.mob_definitions)
        definition = self.mob_manager.mob_definitions["pd_t_mob_1"]
        self.assertEqual(definition["name"], "reliquary warden")
        self.assertTrue(definition["aggressive"])
        mobs = self.mob_manager.get_mobs_in_room("pd_t_reliquary")
        self.assertEqual(len(mobs), 1)
        self.assertEqual(mobs[0].name, "reliquary warden")

    def test_inject_zone_adds_mobs_to_room_items(self):
        """Test spawned mobs appear as items in their rooms."""
        # Act
        self._inject()

        # Assert
        ossuary = self.game_state.get_room("pd_t_ossuary")
        self.assertTrue(any(isinstance(i, Mobile) for i in ossuary.items))

    def test_inject_zone_without_mob_manager_spawns_no_mobs(self):
        """Test mob_manager=None injects rooms but skips all mobs."""
        # Act
        entry_id = self._inject(mob_manager=None)

        # Assert
        self.assertEqual(entry_id, "pd_t_threshold")
        for room_spec in self.spec["rooms"]:
            room = self.game_state.get_room(f"{PREFIX}{room_spec['id']}")
            self.assertFalse(any(isinstance(i, Mobile) for i in room.items))


if __name__ == "__main__":
    unittest.main()
