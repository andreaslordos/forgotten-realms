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


if __name__ == "__main__":
    unittest.main()
