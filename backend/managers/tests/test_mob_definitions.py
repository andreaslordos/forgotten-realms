"""
Comprehensive tests for mob_definitions module.

Tests cover:
- get_mob_definitions returns dict
- All expected mob types exist
- Mob definitions have required fields
- Mob stats are correct types
- Loot table structure
- Specific mob characteristics
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

    def test_get_mob_definitions_returns_all_expected_mobs(self):
        """Test get_mob_definitions returns all expected mob types."""
        expected_mobs = [
            "village_merchant",
            "goblin_scout",
            "dire_wolf",
            "brittle_skeleton",
            "elder_sage",
            "guard_captain"
        ]

        for mob_id in expected_mobs:
            self.assertIn(mob_id, self.mob_defs)

    def test_get_mob_definitions_returns_six_mobs(self):
        """Test get_mob_definitions returns exactly 6 mob types."""
        self.assertEqual(len(self.mob_defs), 6)

    def test_all_mob_definitions_have_required_fields(self):
        """Test all mob definitions have all required fields."""
        required_fields = [
            "name", "description", "strength", "dexterity", "max_stamina",
            "damage", "aggressive", "aggro_delay_min", "aggro_delay_max",
            "patrol_rooms", "movement_interval", "loot_table", "instant_death",
            "point_value", "pronouns"
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
            self.assertIsInstance(mob_def["name"], str, f"{mob_id} name is not a string")

    def test_mob_descriptions_are_strings(self):
        """Test all mob descriptions are strings."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(mob_def["description"], str, f"{mob_id} description is not a string")

    def test_mob_stats_are_numbers(self):
        """Test all mob combat stats are numbers."""
        numeric_fields = ["strength", "dexterity", "max_stamina", "damage", "point_value"]

        for mob_id, mob_def in self.mob_defs.items():
            for field in numeric_fields:
                self.assertIsInstance(mob_def[field], (int, float), f"{mob_id} {field} is not a number")

    def test_mob_aggressive_is_boolean(self):
        """Test aggressive field is boolean."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(mob_def["aggressive"], bool, f"{mob_id} aggressive is not a boolean")

    def test_mob_instant_death_is_boolean(self):
        """Test instant_death field is boolean."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(mob_def["instant_death"], bool, f"{mob_id} instant_death is not a boolean")

    def test_mob_patrol_rooms_is_list(self):
        """Test patrol_rooms field is a list."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(mob_def["patrol_rooms"], list, f"{mob_id} patrol_rooms is not a list")

    def test_mob_loot_table_is_list(self):
        """Test loot_table field is a list."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(mob_def["loot_table"], list, f"{mob_id} loot_table is not a list")

    def test_mob_pronouns_are_strings(self):
        """Test pronouns field is a string."""
        for mob_id, mob_def in self.mob_defs.items():
            self.assertIsInstance(mob_def["pronouns"], str, f"{mob_id} pronouns is not a string")


class MobDefinitionsLootTableTest(unittest.TestCase):
    """Test loot table structure."""

    def setUp(self):
        """Set up mob definitions for tests."""
        self.mob_defs = get_mob_definitions()

    def test_loot_table_entries_have_item_field(self):
        """Test all loot table entries have 'item' field."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                self.assertIn("item", loot_entry, f"{mob_id} loot_table[{idx}] missing 'item' field")

    def test_loot_table_entries_have_chance_field(self):
        """Test all loot table entries have 'chance' field."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                self.assertIn("chance", loot_entry, f"{mob_id} loot_table[{idx}] missing 'chance' field")

    def test_loot_table_items_are_item_objects(self):
        """Test all loot table items are Item or Weapon objects."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                item = loot_entry["item"]
                self.assertTrue(
                    isinstance(item, (Item, Weapon)),
                    f"{mob_id} loot_table[{idx}] item is not an Item or Weapon"
                )

    def test_loot_table_chances_are_numbers(self):
        """Test all loot table chances are numbers."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                chance = loot_entry["chance"]
                self.assertIsInstance(
                    chance, (int, float),
                    f"{mob_id} loot_table[{idx}] chance is not a number"
                )

    def test_loot_table_chances_are_valid_probabilities(self):
        """Test all loot table chances are between 0 and 1."""
        for mob_id, mob_def in self.mob_defs.items():
            for idx, loot_entry in enumerate(mob_def["loot_table"]):
                chance = loot_entry["chance"]
                self.assertGreaterEqual(chance, 0, f"{mob_id} loot_table[{idx}] chance < 0")
                self.assertLessEqual(chance, 1, f"{mob_id} loot_table[{idx}] chance > 1")


class VillageMerchantTest(unittest.TestCase):
    """Test village_merchant specific characteristics."""

    def setUp(self):
        """Set up village_merchant definition."""
        self.merchant = get_mob_definitions()["village_merchant"]

    def test_village_merchant_is_not_aggressive(self):
        """Test village_merchant is not aggressive."""
        self.assertFalse(self.merchant["aggressive"])

    def test_village_merchant_has_zero_aggro_delay(self):
        """Test village_merchant has zero aggro delay."""
        self.assertEqual(self.merchant["aggro_delay_min"], 0)
        self.assertEqual(self.merchant["aggro_delay_max"], 0)

    def test_village_merchant_is_stationary(self):
        """Test village_merchant has no patrol rooms."""
        self.assertEqual(self.merchant["patrol_rooms"], [])

    def test_village_merchant_has_gold_coin_loot(self):
        """Test village_merchant has gold coins in loot table."""
        has_gold = any(entry["item"].name == "gold coin" for entry in self.merchant["loot_table"])
        self.assertTrue(has_gold)

    def test_village_merchant_does_not_have_instant_death(self):
        """Test village_merchant does not have instant death."""
        self.assertFalse(self.merchant["instant_death"])


class GoblinScoutTest(unittest.TestCase):
    """Test goblin_scout specific characteristics."""

    def setUp(self):
        """Set up goblin_scout definition."""
        self.goblin = get_mob_definitions()["goblin_scout"]

    def test_goblin_scout_is_aggressive(self):
        """Test goblin_scout is aggressive."""
        self.assertTrue(self.goblin["aggressive"])

    def test_goblin_scout_has_delayed_aggro(self):
        """Test goblin_scout has aggro delay between 3-8 ticks."""
        self.assertEqual(self.goblin["aggro_delay_min"], 3)
        self.assertEqual(self.goblin["aggro_delay_max"], 8)

    def test_goblin_scout_patrols_multiple_rooms(self):
        """Test goblin_scout patrols multiple rooms."""
        self.assertGreater(len(self.goblin["patrol_rooms"]), 0)
        self.assertIn("forest_clearing", self.goblin["patrol_rooms"])

    def test_goblin_scout_has_varied_loot(self):
        """Test goblin_scout has multiple loot items."""
        self.assertGreaterEqual(len(self.goblin["loot_table"]), 2)

    def test_goblin_scout_does_not_have_instant_death(self):
        """Test goblin_scout does not have instant death."""
        self.assertFalse(self.goblin["instant_death"])


class DireWolfTest(unittest.TestCase):
    """Test dire_wolf specific characteristics."""

    def setUp(self):
        """Set up dire_wolf definition."""
        self.wolf = get_mob_definitions()["dire_wolf"]

    def test_dire_wolf_is_aggressive(self):
        """Test dire_wolf is aggressive."""
        self.assertTrue(self.wolf["aggressive"])

    def test_dire_wolf_has_instant_aggro(self):
        """Test dire_wolf has instant aggro (no delay)."""
        self.assertEqual(self.wolf["aggro_delay_min"], 0)
        self.assertEqual(self.wolf["aggro_delay_max"], 0)

    def test_dire_wolf_has_fast_movement(self):
        """Test dire_wolf has fast movement interval."""
        self.assertLessEqual(self.wolf["movement_interval"], 5)

    def test_dire_wolf_has_high_damage(self):
        """Test dire_wolf has high damage."""
        self.assertGreaterEqual(self.wolf["damage"], 10)

    def test_dire_wolf_drops_wolf_pelt(self):
        """Test dire_wolf has wolf pelt in loot table."""
        has_pelt = any(entry["item"].name == "wolf pelt" for entry in self.wolf["loot_table"])
        self.assertTrue(has_pelt)


class BrittleSkeletonTest(unittest.TestCase):
    """Test brittle_skeleton specific characteristics."""

    def setUp(self):
        """Set up brittle_skeleton definition."""
        self.skeleton = get_mob_definitions()["brittle_skeleton"]

    def test_brittle_skeleton_has_instant_death(self):
        """Test brittle_skeleton has instant death enabled."""
        self.assertTrue(self.skeleton["instant_death"])

    def test_brittle_skeleton_is_aggressive(self):
        """Test brittle_skeleton is aggressive."""
        self.assertTrue(self.skeleton["aggressive"])

    def test_brittle_skeleton_is_stationary(self):
        """Test brittle_skeleton has no patrol rooms."""
        self.assertEqual(self.skeleton["patrol_rooms"], [])

    def test_brittle_skeleton_has_rare_ancient_key_drop(self):
        """Test brittle_skeleton has ancient key with low drop chance."""
        key_entries = [e for e in self.skeleton["loot_table"] if e["item"].name == "ancient key"]
        self.assertEqual(len(key_entries), 1)
        self.assertLess(key_entries[0]["chance"], 0.2)


class ElderSageTest(unittest.TestCase):
    """Test elder_sage specific characteristics."""

    def setUp(self):
        """Set up elder_sage definition."""
        self.elder = get_mob_definitions()["elder_sage"]

    def test_elder_sage_is_not_aggressive(self):
        """Test elder_sage is not aggressive."""
        self.assertFalse(self.elder["aggressive"])

    def test_elder_sage_patrols(self):
        """Test elder_sage patrols multiple rooms."""
        self.assertGreater(len(self.elder["patrol_rooms"]), 0)
        self.assertIn("elders_cottage", self.elder["patrol_rooms"])

    def test_elder_sage_has_slow_movement(self):
        """Test elder_sage has slow movement interval."""
        self.assertGreaterEqual(self.elder["movement_interval"], 15)

    def test_elder_sage_gives_no_points(self):
        """Test elder_sage gives 0 points (peaceful NPC)."""
        self.assertEqual(self.elder["point_value"], 0)

    def test_elder_sage_always_drops_ancient_key(self):
        """Test elder_sage always drops ancient key."""
        key_entries = [e for e in self.elder["loot_table"] if e["item"].name == "ancient key"]
        self.assertEqual(len(key_entries), 1)
        self.assertEqual(key_entries[0]["chance"], 1.0)


class GuardCaptainTest(unittest.TestCase):
    """Test guard_captain specific characteristics."""

    def setUp(self):
        """Set up guard_captain definition."""
        self.captain = get_mob_definitions()["guard_captain"]

    def test_guard_captain_is_not_aggressive(self):
        """Test guard_captain is not aggressive (only attacks if provoked)."""
        self.assertFalse(self.captain["aggressive"])

    def test_guard_captain_has_high_stats(self):
        """Test guard_captain has high combat stats."""
        self.assertGreaterEqual(self.captain["strength"], 40)
        self.assertGreaterEqual(self.captain["max_stamina"], 100)

    def test_guard_captain_has_high_damage(self):
        """Test guard_captain has high damage."""
        self.assertGreaterEqual(self.captain["damage"], 15)

    def test_guard_captain_patrols_key_areas(self):
        """Test guard_captain patrols important areas."""
        self.assertIn("spawn", self.captain["patrol_rooms"])
        self.assertIn("marketplace", self.captain["patrol_rooms"])

    def test_guard_captain_drops_multiple_gold_coins(self):
        """Test guard_captain can drop multiple gold coins."""
        gold_entries = [e for e in self.captain["loot_table"] if e["item"].name == "gold coin"]
        self.assertGreaterEqual(len(gold_entries), 2)

    def test_guard_captain_gives_high_points(self):
        """Test guard_captain gives high point value."""
        self.assertGreaterEqual(self.captain["point_value"], 150)


if __name__ == "__main__":
    unittest.main()
