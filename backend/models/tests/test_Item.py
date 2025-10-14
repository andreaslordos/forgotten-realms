"""
Comprehensive tests for base Item class.

Tests cover:
- Item initialization and attributes
- Item serialization/deserialization
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Item import Item


class ItemInitializationTest(unittest.TestCase):
    """Test base Item class initialization and attributes."""

    def test___init___with_all_parameters(self):
        """Test creating an item with all parameters."""
        item = Item(
            name="Rusty Key",
            id="key_rusty_1",
            description="An old rusty key",
            weight=0.5,
            value=10,
            takeable=True,
        )

        self.assertEqual(item.name, "Rusty Key")
        self.assertEqual(item.id, "key_rusty_1")
        self.assertEqual(item.description, "An old rusty key")
        self.assertEqual(item.weight, 0.5)
        self.assertEqual(item.value, 10)
        self.assertTrue(item.takeable)

    def test___init___with_defaults(self):
        """Test creating an item with default values."""
        item = Item("Stone", "stone_1", "A smooth stone")

        self.assertEqual(item.weight, 1)
        self.assertEqual(item.value, 0)
        self.assertTrue(item.takeable)

    def test___init___non_takeable(self):
        """Test creating an item that cannot be picked up."""
        item = Item(
            "Ancient Statue",
            "statue_1",
            "A massive stone statue",
            weight=1000,
            takeable=False,
        )

        self.assertFalse(item.takeable)

    def test___repr___returns_formatted_string(self):
        """Test item string representation."""
        item = Item("Coin", "coin_1", "A gold coin", weight=0.1, value=5)
        repr_str = repr(item)

        self.assertIn("Coin", repr_str)
        self.assertIn("0.1kg", repr_str)
        self.assertIn("5pts", repr_str)


class ItemSerializationTest(unittest.TestCase):
    """Test item serialization and deserialization."""

    def test_to_dict_returns_all_attributes(self):
        """Test converting item to dictionary."""
        item = Item(
            "Torch", "torch_1", "A burning torch", weight=1.5, value=15, takeable=True
        )
        item_dict = item.to_dict()

        self.assertEqual(item_dict["name"], "Torch")
        self.assertEqual(item_dict["id"], "torch_1")
        self.assertEqual(item_dict["description"], "A burning torch")
        self.assertEqual(item_dict["weight"], 1.5)
        self.assertEqual(item_dict["value"], 15)
        self.assertTrue(item_dict["takeable"])

    def test_from_dict_creates_item(self):
        """Test creating item from dictionary."""
        data = {
            "name": "Map",
            "id": "map_1",
            "description": "A treasure map",
            "weight": 0.2,
            "value": 50,
            "takeable": True,
        }
        item = Item.from_dict(data)

        self.assertEqual(item.name, "Map")
        self.assertEqual(item.id, "map_1")
        self.assertEqual(item.description, "A treasure map")
        self.assertEqual(item.weight, 0.2)
        self.assertEqual(item.value, 50)
        self.assertTrue(item.takeable)

    def test_to_dict_from_dict_round_trip(self):
        """Test serializing and deserializing an item."""
        original = Item("Book", "book_1", "An old book", weight=2, value=25)
        serialized = original.to_dict()
        reconstructed = Item.from_dict(serialized)

        self.assertEqual(reconstructed.name, original.name)
        self.assertEqual(reconstructed.id, original.id)
        self.assertEqual(reconstructed.description, original.description)
        self.assertEqual(reconstructed.weight, original.weight)
        self.assertEqual(reconstructed.value, original.value)


class ItemLightEmissionTest(unittest.TestCase):
    """Test item light emission property for darkness system."""

    def test___init___defaults_emits_light_to_false(self):
        """Test item defaults to not emitting light."""
        item = Item("Stick", "stick_1", "A wooden stick")

        self.assertFalse(item.emits_light)

    def test___init___accepts_emits_light_parameter(self):
        """Test creating a light-emitting item."""
        item = Item("Torch", "torch_1", "A burning torch", weight=1, emits_light=True)

        self.assertTrue(item.emits_light)

    def test_to_dict_includes_emits_light(self):
        """Test serialization includes emits_light property."""
        item = Item("Lantern", "lantern_1", "A lit lantern", emits_light=True)
        item_dict = item.to_dict()

        self.assertIn("emits_light", item_dict)
        self.assertTrue(item_dict["emits_light"])

    def test_from_dict_restores_emits_light(self):
        """Test deserialization restores emits_light property."""
        data = {
            "name": "Torch",
            "id": "torch_1",
            "description": "A burning torch",
            "weight": 1,
            "value": 10,
            "takeable": True,
            "emits_light": True,
        }

        item = Item.from_dict(data)

        self.assertTrue(item.emits_light)

    def test_to_dict_from_dict_round_trip_with_emits_light(self):
        """Test serialization cycle preserves emits_light."""
        original = Item("Candle", "candle_1", "A lit candle", emits_light=True)

        serialized = original.to_dict()
        reconstructed = Item.from_dict(serialized)

        self.assertEqual(reconstructed.emits_light, original.emits_light)

    def test_emits_light_can_be_modified_at_runtime(self):
        """Test emits_light property can be changed (for lighting/extinguishing)."""
        item = Item("Torch", "torch_1", "A torch", emits_light=False)

        self.assertFalse(item.emits_light)

        # Light the torch
        item.emits_light = True
        self.assertTrue(item.emits_light)

        # Extinguish the torch
        item.emits_light = False
        self.assertFalse(item.emits_light)


if __name__ == "__main__":
    unittest.main()
