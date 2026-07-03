"""
Comprehensive tests for the Consumable item class.

Tests cover:
- Consumable initialization and attributes
- Serialization/deserialization round trips
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Consumable import EFFECT_CURE_ALL, EFFECT_HEAL, Consumable
from models.Item import Item


class ConsumableInitializationTest(unittest.TestCase):
    """Test Consumable initialization and attributes."""

    def test___init___with_all_parameters(self):
        """Test creating a consumable with all parameters."""
        # Arrange & Act
        potion = Consumable(
            name="healing draught",
            id="potion_heal_1",
            description="A warm red draught.",
            effect=EFFECT_HEAL,
            magnitude=25,
            weight=1,
            value=30,
            takeable=True,
            synonyms=["potion", "draught"],
        )

        # Assert
        self.assertEqual(potion.name, "healing draught")
        self.assertEqual(potion.id, "potion_heal_1")
        self.assertEqual(potion.description, "A warm red draught.")
        self.assertEqual(potion.effect, EFFECT_HEAL)
        self.assertEqual(potion.magnitude, 25)
        self.assertEqual(potion.weight, 1)
        self.assertEqual(potion.value, 30)
        self.assertTrue(potion.takeable)
        self.assertEqual(potion.synonyms, ["potion", "draught"])

    def test___init___with_defaults(self):
        """Test creating a consumable with default values."""
        # Arrange & Act
        potion = Consumable("water", "water_1", "Plain water.")

        # Assert
        self.assertEqual(potion.effect, EFFECT_HEAL)
        self.assertEqual(potion.magnitude, 0)
        self.assertEqual(potion.weight, 1)
        self.assertEqual(potion.value, 0)
        self.assertTrue(potion.takeable)

    def test___init___accepts_cure_all_effect(self):
        """Test creating a cure-all consumable."""
        # Arrange & Act
        tonic = Consumable(
            "bitter tonic",
            "tonic_1",
            "A bitter cleansing tonic.",
            effect=EFFECT_CURE_ALL,
        )

        # Assert
        self.assertEqual(tonic.effect, EFFECT_CURE_ALL)

    def test___init___is_item_subclass(self):
        """Test consumables inherit from Item."""
        # Arrange & Act
        potion = Consumable("water", "water_1", "Plain water.")

        # Assert
        self.assertIsInstance(potion, Item)

    def test_matches_name_uses_synonyms(self):
        """Test consumables match against inherited synonyms."""
        # Arrange
        potion = Consumable(
            "healing draught",
            "potion_heal_1",
            "A warm red draught.",
            synonyms=["potion"],
        )

        # Act & Assert
        self.assertTrue(potion.matches_name("potion"))
        self.assertTrue(potion.matches_name("draught"))
        self.assertFalse(potion.matches_name("sword"))


class ConsumableSerializationTest(unittest.TestCase):
    """Test Consumable serialization and deserialization."""

    def test_to_dict_sets_item_type_consumable(self):
        """Test to_dict tags the payload as a consumable."""
        # Arrange
        potion = Consumable("water", "water_1", "Plain water.")

        # Act
        data = potion.to_dict()

        # Assert
        self.assertEqual(data["item_type"], "consumable")

    def test_to_dict_includes_effect_and_magnitude(self):
        """Test to_dict serializes effect and magnitude."""
        # Arrange
        potion = Consumable(
            "healing draught",
            "potion_heal_1",
            "A warm red draught.",
            effect=EFFECT_HEAL,
            magnitude=25,
        )

        # Act
        data = potion.to_dict()

        # Assert
        self.assertEqual(data["effect"], EFFECT_HEAL)
        self.assertEqual(data["magnitude"], 25)

    def test_to_dict_includes_base_item_fields(self):
        """Test to_dict still carries the base Item fields."""
        # Arrange
        potion = Consumable(
            "healing draught",
            "potion_heal_1",
            "A warm red draught.",
            weight=2,
            value=30,
        )

        # Act
        data = potion.to_dict()

        # Assert
        self.assertEqual(data["name"], "healing draught")
        self.assertEqual(data["id"], "potion_heal_1")
        self.assertEqual(data["weight"], 2)
        self.assertEqual(data["value"], 30)

    def test_from_dict_creates_consumable(self):
        """Test from_dict builds a Consumable from a dictionary."""
        # Arrange
        data = {
            "name": "bitter tonic",
            "id": "tonic_1",
            "description": "A bitter cleansing tonic.",
            "effect": EFFECT_CURE_ALL,
            "magnitude": 0,
            "weight": 1,
            "value": 40,
            "takeable": True,
        }

        # Act
        tonic = Consumable.from_dict(data)

        # Assert
        self.assertIsInstance(tonic, Consumable)
        self.assertEqual(tonic.effect, EFFECT_CURE_ALL)
        self.assertEqual(tonic.value, 40)

    def test_from_dict_defaults_effect_and_magnitude(self):
        """Test from_dict tolerates missing effect/magnitude keys."""
        # Arrange
        data = {
            "name": "water",
            "id": "water_1",
            "description": "Plain water.",
        }

        # Act
        potion = Consumable.from_dict(data)

        # Assert
        self.assertEqual(potion.effect, EFFECT_HEAL)
        self.assertEqual(potion.magnitude, 0)

    def test_to_dict_from_dict_round_trip(self):
        """Test serializing and deserializing preserves all fields."""
        # Arrange
        original = Consumable(
            name="healing draught",
            id="potion_heal_1",
            description="A warm red draught.",
            effect=EFFECT_HEAL,
            magnitude=25,
            weight=2,
            value=30,
            synonyms=["potion"],
        )

        # Act
        reconstructed = Consumable.from_dict(original.to_dict())

        # Assert
        self.assertEqual(reconstructed.name, original.name)
        self.assertEqual(reconstructed.id, original.id)
        self.assertEqual(reconstructed.description, original.description)
        self.assertEqual(reconstructed.effect, original.effect)
        self.assertEqual(reconstructed.magnitude, original.magnitude)
        self.assertEqual(reconstructed.weight, original.weight)
        self.assertEqual(reconstructed.value, original.value)
        self.assertEqual(reconstructed.synonyms, original.synonyms)


if __name__ == "__main__":
    unittest.main()
