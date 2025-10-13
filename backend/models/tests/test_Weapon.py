"""
Comprehensive tests for Weapon class.

Tests cover:
- Weapon initialization with combat attributes
- Weapon requirements and restrictions
- Weapon serialization/deserialization
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Weapon import Weapon
from models.Player import Player


class WeaponInitializationTest(unittest.TestCase):
    """Test Weapon class initialization and attributes."""

    def test___init___with_defaults(self):
        """Test creating a weapon with default combat values."""
        weapon = Weapon("Dagger", "dagger_1", "A sharp dagger")

        self.assertEqual(weapon.name, "Dagger")
        self.assertEqual(weapon.damage, 5)  # Default damage
        self.assertEqual(weapon.min_level, 0)
        self.assertEqual(weapon.min_strength, 0)
        self.assertEqual(weapon.min_dexterity, 0)
        self.assertEqual(weapon.weapon_type, "melee")

    def test___init___with_requirements(self):
        """Test creating a weapon with stat requirements."""
        weapon = Weapon(
            "Longsword",
            "sword_long_1",
            "A heavy longsword",
            weight=5,
            damage=25,
            min_strength=15,
            min_dexterity=10
        )

        self.assertEqual(weapon.damage, 25)
        self.assertEqual(weapon.min_strength, 15)
        self.assertEqual(weapon.min_dexterity, 10)

    def test___init___inherits_item_properties(self):
        """Test that weapon inherits Item properties."""
        weapon = Weapon("Axe", "axe_1", "A heavy axe", weight=8, value=30)

        self.assertEqual(weapon.weight, 8)
        self.assertEqual(weapon.value, 30)
        self.assertTrue(weapon.takeable)


class WeaponRequirementsTest(unittest.TestCase):
    """Test weapon usage requirements and restrictions."""

    def setUp(self):
        """Set up test player and weapons."""
        self.player = Player("TestHero")
        # Manually set stats for testing
        self.player.strength = 10
        self.player.dexterity = 10

    def test_can_use_returns_true_for_basic_weapon(self):
        """Test player can use weapon with no requirements."""
        weapon = Weapon("Stick", "stick_1", "A wooden stick", damage=3)
        can_use, message = weapon.can_use(self.player)

        self.assertTrue(can_use)
        self.assertEqual(message, "")

    def test_can_use_returns_false_insufficient_strength(self):
        """Test player cannot use weapon due to insufficient strength."""
        weapon = Weapon(
            "Warhammer",
            "hammer_1",
            "A massive warhammer",
            damage=40,
            min_strength=20
        )
        can_use, message = weapon.can_use(self.player)

        self.assertFalse(can_use)
        self.assertIn("strength", message.lower())
        self.assertIn("20", message)

    def test_can_use_returns_false_insufficient_dexterity(self):
        """Test player cannot use weapon due to insufficient dexterity."""
        weapon = Weapon(
            "Rapier",
            "rapier_1",
            "A nimble rapier",
            damage=15,
            min_dexterity=15
        )
        can_use, message = weapon.can_use(self.player)

        self.assertFalse(can_use)
        self.assertIn("dexterity", message.lower())
        self.assertIn("15", message)

    def test_can_use_returns_true_when_requirements_met(self):
        """Test player can use weapon when meeting all requirements."""
        self.player.strength = 15
        self.player.dexterity = 12

        weapon = Weapon(
            "Sword",
            "sword_1",
            "A balanced sword",
            damage=20,
            min_strength=12,
            min_dexterity=10
        )
        can_use, message = weapon.can_use(self.player)

        self.assertTrue(can_use)
        self.assertEqual(message, "")


class WeaponSerializationTest(unittest.TestCase):
    """Test weapon serialization and deserialization."""

    def test_to_dict_includes_weapon_attributes(self):
        """Test converting weapon to dictionary."""
        weapon = Weapon(
            "Greatsword",
            "sword_great_1",
            "A massive greatsword",
            weight=10,
            value=100,
            damage=35,
            min_strength=18,
            min_dexterity=8
        )
        weapon_dict = weapon.to_dict()

        self.assertEqual(weapon_dict["name"], "Greatsword")
        self.assertEqual(weapon_dict["damage"], 35)
        self.assertEqual(weapon_dict["min_strength"], 18)
        self.assertEqual(weapon_dict["min_dexterity"], 8)
        self.assertEqual(weapon_dict["item_type"], "weapon")

    def test_from_dict_creates_weapon(self):
        """Test creating weapon from dictionary."""
        data = {
            "name": "Spear",
            "id": "spear_1",
            "description": "A long spear",
            "weight": 4,
            "value": 40,
            "damage": 18,
            "min_strength": 10,
            "min_dexterity": 12,
            "weapon_type": "melee"
        }
        weapon = Weapon.from_dict(data)

        self.assertEqual(weapon.name, "Spear")
        self.assertEqual(weapon.damage, 18)
        self.assertEqual(weapon.min_strength, 10)
        self.assertEqual(weapon.weapon_type, "melee")

    def test_to_dict_from_dict_round_trip(self):
        """Test serializing and deserializing a weapon."""
        original = Weapon(
            "Bow",
            "bow_1",
            "A hunting bow",
            damage=22,
            min_dexterity=14
        )
        serialized = original.to_dict()
        reconstructed = Weapon.from_dict(serialized)

        self.assertEqual(reconstructed.name, original.name)
        self.assertEqual(reconstructed.damage, original.damage)
        self.assertEqual(reconstructed.min_dexterity, original.min_dexterity)


if __name__ == "__main__":
    unittest.main()
