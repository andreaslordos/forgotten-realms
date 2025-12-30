"""
Tests for mob_definitions module.

Tests cover:
- get_mob_definitions returns dict with mobs
- All mob definitions have required fields
- Mob field types are correct
- Loot table structure is valid
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.mob_definitions import get_mob_definitions
from models.Item import Item
from models.Weapon import Weapon


class MobDefinitionsStructureTest(unittest.TestCase):
    """Test mob definitions structure."""

    def setUp(self):
        """Set up mob definitions for tests."""
        self.mob_defs = get_mob_definitions()

    def test_get_mob_definitions_returns_dict(self):
        """Test get_mob_definitions returns a dictionary."""
        self.assertIsInstance(self.mob_defs, dict)

    def test_get_mob_definitions_returns_at_least_one_mob(self):
        """Test get_mob_definitions returns at least one mob type."""
        self.assertGreater(len(self.mob_defs), 0)

    def test_all_mob_definitions_have_required_fields(self):
        """Test all mob definitions have all required fields."""
        required_fields = [
            "name",
            "description",
            "strength",
            "dexterity",
            "max_stamina",
            "damage",
            "aggressive",
            "aggro_delay_min",
            "aggro_delay_max",
            "patrol_rooms",
            "movement_interval",
            "loot_table",
            "instant_death",
            "point_value",
            "pronouns",
        ]

        for mob_id, mob_def in self.mob_defs.items():
            for field in required_fields:
                self.assertIn(field, mob_def, f"{mob_id} missing field: {field}")


class MobDefinitionsFieldTypesTest(unittest.TestCase):
    """Test mob definition field types."""

    def setUp(self):
        """Set up mob definitions for tests."""
        self.mob_defs = get_mob_definitions()

    def test_mob_names_are_strings(self):
        """Test all mob names are strings."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(
                mob_def["name"], str, f"{mob_id} name is not a string"
            )

    def test_mob_descriptions_are_strings(self):
        """Test all mob descriptions are strings."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(
                mob_def["description"], str, f"{mob_id} description is not a string"
            )

    def test_mob_stats_are_numbers(self):
        """Test all mob combat stats are numbers."""
        numeric_fields = [
            "strength",
            "dexterity",
            "max_stamina",
            "damage",
            "point_value",
        ]

        for mob_id, mob_def in self.mob_defs.items():
            for field in numeric_fields:
                self.assertIsInstance(
                    mob_def[field], (int, float), f"{mob_id} {field} is not a number"
                )

    def test_mob_aggressive_is_boolean(self):
        """Test aggressive field is boolean."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(
                mob_def["aggressive"], bool, f"{mob_id} aggressive is not a boolean"
            )

    def test_mob_instant_death_is_boolean(self):
        """Test instant_death field is boolean."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(
                mob_def["instant_death"],
                bool,
                f"{mob_id} instant_death is not a boolean",
            )

    def test_mob_patrol_rooms_is_list(self):
        """Test patrol_rooms field is a list."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(
                mob_def["patrol_rooms"], list, f"{mob_id} patrol_rooms is not a list"
            )

    def test_mob_loot_table_is_list(self):
        """Test loot_table field is a list."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(
                mob_def["loot_table"], list, f"{mob_id} loot_table is not a list"
            )

    def test_mob_pronouns_are_strings(self):
        """Test pronouns field is a string."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(
                mob_def["pronouns"], str, f"{mob_id} pronouns is not a string"
            )


class MobDefinitionsLootTableTest(unittest.TestCase):
    """Test loot table structure."""

    def setUp(self):
        """Set up mob definitions for tests."""
        self.mob_defs = get_mob_definitions()

    def test_loot_table_entries_have_item_field(self):
        """Test all loot table entries have 'item' field."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                self.assertIn(
                    "item",
                    loot_entry,
                    f"{mob_id} loot_table[{idx}] missing 'item' field",
                )

    def test_loot_table_entries_have_chance_field(self):
        """Test all loot table entries have 'chance' field."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                self.assertIn(
                    "chance",
                    loot_entry,
                    f"{mob_id} loot_table[{idx}] missing 'chance' field",
                )

    def test_loot_table_items_are_item_objects(self):
        """Test all loot table items are Item or Weapon objects."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                item = loot_entry["item"]
                self.assertTrue(
                    isinstance(item, (Item, Weapon)),
                    f"{mob_id} loot_table[{idx}] item is not an Item or Weapon",
                )

    def test_loot_table_chances_are_numbers(self):
        """Test all loot table chances are numbers."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                chance = loot_entry["chance"]
                self.assertIsInstance(
                    chance,
                    (int, float),
                    f"{mob_id} loot_table[{idx}] chance is not a number",
                )

    def test_loot_table_chances_are_valid_probabilities(self):
        """Test all loot table chances are between 0 and 1."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                chance = loot_entry["chance"]
                self.assertGreaterEqual(
                    chance, 0, f"{mob_id} loot_table[{idx}] chance < 0"
                )
                self.assertLessEqual(
                    chance, 1, f"{mob_id} loot_table[{idx}] chance > 1"
                )


if __name__ == "__main__":
    unittest.main()
