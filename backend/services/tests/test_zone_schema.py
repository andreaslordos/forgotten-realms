# backend/services/tests/test_zone_schema.py
"""Tests for pocket-dimension zone spec validation and room building."""

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.StatefulItem import StatefulItem
from services.zone_schema import spec_to_rooms, validate_zone_spec

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


class ValidateZoneSpecValidFixtureTest(unittest.TestCase):
    """Test validate_zone_spec accepts the shipped fallback zone."""

    def test_validate_zone_spec_accepts_fallback_fixture(self):
        """Test the shipped fallback zone validates cleanly (guards the file)."""
        # Arrange
        spec = load_fixture()

        # Act
        errors = validate_zone_spec(spec, PREFIX)

        # Assert
        self.assertEqual(errors, [])


class ValidateZoneSpecViolationsTest(unittest.TestCase):
    """Test each validation rule rejects a mutated copy of the fixture."""

    def setUp(self):
        """Load a deep copy of the valid fixture to mutate per test."""
        self.spec = copy.deepcopy(load_fixture())

    def _errors(self, existing_room_ids=None):
        return validate_zone_spec(self.spec, PREFIX, existing_room_ids)

    def _assert_error_containing(self, fragment, existing_room_ids=None):
        errors = self._errors(existing_room_ids)
        self.assertTrue(
            any(fragment in e for e in errors),
            f"expected an error containing {fragment!r}, got {errors!r}",
        )

    def test_validate_zone_spec_rejects_too_few_rooms(self):
        """Test fewer than MIN_ROOMS rooms is a structural error."""
        # Arrange
        self.spec["rooms"] = self.spec["rooms"][:3]

        # Act / Assert
        self._assert_error_containing("must have 4-10 rooms")

    def test_validate_zone_spec_rejects_duplicate_room_ids(self):
        """Test two rooms with the same id are rejected."""
        # Arrange
        self.spec["rooms"][1]["id"] = self.spec["rooms"][0]["id"]

        # Act / Assert
        self._assert_error_containing("duplicate room ids")

    def test_validate_zone_spec_rejects_invalid_room_id(self):
        """Test a room id outside the lowercase pattern is rejected."""
        # Arrange
        self.spec["rooms"][3]["id"] = "Bad-ID"

        # Act / Assert
        self._assert_error_containing("invalid room id")

    def test_validate_zone_spec_rejects_exit_to_unknown_room(self):
        """Test an exit pointing outside the zone is rejected."""
        # Arrange
        self.spec["rooms"][0]["exits"]["down"] = "abyss"

        # Act / Assert
        self._assert_error_containing("exit to unknown room 'abyss'")

    def test_validate_zone_spec_rejects_nonstandard_direction(self):
        """Test an exit direction outside DIRECTION_VECTORS is rejected."""
        # Arrange
        self.spec["rooms"][0]["exits"]["warp"] = "nave"

        # Act / Assert
        self._assert_error_containing("nonstandard direction 'warp'")

    def test_validate_zone_spec_rejects_entry_room_not_in_zone(self):
        """Test entry_room_id must name a room in the zone."""
        # Arrange
        self.spec["entry_room_id"] = "void"

        # Act / Assert
        self._assert_error_containing("entry_room_id is not a room in the zone")

    def test_validate_zone_spec_rejects_mob_in_unknown_room(self):
        """Test a mob placed in a room outside the zone is rejected."""
        # Arrange
        self.spec["mobs"][0]["room_id"] = "void"

        # Act / Assert
        self._assert_error_containing("mob placed in unknown room 'void'")

    def test_validate_zone_spec_rejects_disallowed_mob_template(self):
        """Test a quest-NPC template like 'priest' is not allowed."""
        # Arrange
        self.spec["mobs"][0]["template_id"] = "priest"

        # Act / Assert
        self._assert_error_containing("mob template 'priest' not allowed")

    def test_validate_zone_spec_rejects_custom_mob_stat_outside_limits(self):
        """Test a custom mob stat outside CUSTOM_MOB_LIMITS is rejected."""
        # Arrange
        self.spec["mobs"][1]["custom"]["strength"] = 999

        # Act / Assert
        self._assert_error_containing("strength outside")

    def test_validate_zone_spec_rejects_too_many_aggressive_mobs(self):
        """Test more than MAX_AGGRESSIVE_MOBS aggressive mobs is rejected."""
        # Arrange: fixture already has one aggressive custom mob; add two
        # aggressive templates for a total of three.
        self.spec["mobs"].append({"room_id": "gallery", "template_id": "wolf"})
        self.spec["mobs"].append({"room_id": "nave", "template_id": "ghoul"})

        # Act / Assert
        self._assert_error_containing("too many aggressive mobs")

    def test_validate_zone_spec_rejects_item_value_over_budget(self):
        """Test total item value above MAX_TOTAL_ITEM_VALUE is rejected."""
        # Arrange
        self.spec["items"][0]["value"] = 200

        # Act / Assert
        self._assert_error_containing("exceeds budget")

    def test_validate_zone_spec_rejects_unplayable_puzzle_verb(self):
        """Test a trigger_verb outside ALLOWED_PUZZLE_VERBS is rejected."""
        # Arrange
        self.spec["puzzle"]["trigger_verb"] = "juggle"

        # Act / Assert
        self._assert_error_containing("puzzle trigger_verb 'juggle'")

    def test_validate_zone_spec_rejects_non_reciprocal_exit(self):
        """Test dropping one half of a reciprocal pair is rejected."""
        # Arrange: threshold->east->gallery removed; gallery->west remains.
        del self.spec["rooms"][0]["exits"]["east"]

        # Act / Assert
        self._assert_error_containing("non-reciprocal exit")

    def test_validate_zone_spec_rejects_coords_disagreeing_with_exits(self):
        """Test declared coords must match the exit-derived layout."""
        # Arrange: gallery is east of threshold, so it must sit at [1, 0, 0].
        self.spec["rooms"][3]["coords"] = [2, 0, 0]

        # Act / Assert
        self._assert_error_containing("disagree with exits")

    def test_validate_zone_spec_rejects_two_rooms_sharing_coords(self):
        """Test two rooms declaring identical coords is rejected."""
        # Arrange: give the ossuary the gallery's coords.
        self.spec["rooms"][4]["coords"] = list(self.spec["rooms"][3]["coords"])

        # Act / Assert
        self._assert_error_containing("two rooms share the same coords")

    def test_validate_zone_spec_rejects_collision_with_existing_world(self):
        """Test a namespaced room id already in the world is rejected."""
        # Arrange
        existing = {"pd_t_threshold"}

        # Act / Assert
        self._assert_error_containing(
            "room id collision with existing world: pd_t_threshold",
            existing_room_ids=existing,
        )


class SpecToRoomsTest(unittest.TestCase):
    """Test spec_to_rooms builds namespaced rooms, items and the puzzle."""

    def setUp(self):
        """Build rooms from a deep copy of the valid fixture."""
        self.spec = copy.deepcopy(load_fixture())
        self.rooms = spec_to_rooms(self.spec, PREFIX)

    def test_spec_to_rooms_namespaces_all_room_ids(self):
        """Test every room id gains the zone prefix."""
        # Assert
        self.assertEqual(
            set(self.rooms.keys()),
            {
                "pd_t_threshold",
                "pd_t_nave",
                "pd_t_reliquary",
                "pd_t_gallery",
                "pd_t_ossuary",
            },
        )

    def test_spec_to_rooms_namespaces_exit_targets(self):
        """Test exits point at namespaced room ids."""
        # Assert
        threshold = self.rooms["pd_t_threshold"]
        self.assertEqual(threshold.exits["north"], "pd_t_nave")
        self.assertEqual(threshold.exits["east"], "pd_t_gallery")
        self.assertEqual(threshold.exits["west"], "pd_t_ossuary")

    def test_spec_to_rooms_omits_blocked_exit_statically(self):
        """Test the puzzle's blocked exit is not wired into the nave."""
        # Assert
        nave = self.rooms["pd_t_nave"]
        self.assertNotIn("north", nave.exits)
        self.assertEqual(nave.exits, {"south": "pd_t_threshold"})

    def test_spec_to_rooms_puzzle_interaction_adds_blocked_exit(self):
        """Test the puzzle item carries the blocked exit as a latent add_exit."""
        # Arrange
        nave = self.rooms["pd_t_nave"]
        puzzle_items = [item for item in nave.items if isinstance(item, StatefulItem)]

        # Assert
        self.assertEqual(len(puzzle_items), 1)
        puzzle = puzzle_items[0]
        self.assertEqual(puzzle.id, "pd_t_puzzle")
        self.assertEqual(puzzle.get_state(), "dormant")
        ring = puzzle.interactions["ring"][0]
        self.assertEqual(ring["add_exit"], ("north", "pd_t_reliquary"))
        self.assertEqual(ring["from_state"], "dormant")
        self.assertEqual(ring["target_state"], "triggered")

    def test_spec_to_rooms_places_items_in_rooms(self):
        """Test declared items land in their namespaced rooms."""
        # Assert
        reliquary_names = [i.name for i in self.rooms["pd_t_reliquary"].items]
        gallery_names = [i.name for i in self.rooms["pd_t_gallery"].items]
        self.assertIn("glass psalm", reliquary_names)
        self.assertIn("clouded pearl", gallery_names)

    def test_spec_to_rooms_honors_is_dark(self):
        """Test a room declared dark builds as a dark room."""
        # Arrange
        spec = copy.deepcopy(load_fixture())
        spec["rooms"][4]["is_dark"] = True

        # Act
        rooms = spec_to_rooms(spec, PREFIX)

        # Assert
        self.assertTrue(rooms["pd_t_ossuary"].is_dark)
        self.assertFalse(rooms["pd_t_threshold"].is_dark)

    def test_spec_to_rooms_marks_all_rooms_indoor(self):
        """Test pocket dimension rooms are never outdoors (no sky)."""
        # Assert
        for room in self.rooms.values():
            self.assertFalse(room.is_outdoor)


if __name__ == "__main__":
    unittest.main()
