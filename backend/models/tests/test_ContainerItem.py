"""
Comprehensive tests for ContainerItem class.

Tests cover:
- Container initialization and capacity
- Adding and removing items
- Weight and value calculations
- Container serialization
- Inventory management
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Item import Item
from models.Weapon import Weapon
from models.ContainerItem import ContainerItem
from models.Player import Player


class ContainerItemTest(unittest.TestCase):
    """Test ContainerItem functionality."""

    def setUp(self):
        """Set up test container and items."""
        self.container = ContainerItem(
            "Bag",
            "bag_1",
            "A leather bag",
            weight=1,
            capacity_limit=5,
            capacity_weight=10
        )
        self.item1 = Item("Coin", "coin_1", "A gold coin", weight=0.1, value=5)
        self.item2 = Item("Gem", "gem_1", "A ruby gem", weight=0.2, value=50)

    def test___init___sets_defaults(self):
        """Test container is properly initialized."""
        self.assertEqual(self.container.capacity_limit, 5)
        self.assertEqual(self.container.capacity_weight, 10)
        self.assertEqual(len(self.container.items), 0)
        self.assertEqual(self.container.state, "open")

    def test_add_item_adds_to_items_list(self):
        """Test adding items to container."""
        success = self.container.add_item(self.item1)

        self.assertTrue(success)
        self.assertEqual(len(self.container.items), 1)
        self.assertIn(self.item1, self.container.items)

    def test_weight_property_includes_contents(self):
        """Test that container weight includes contents."""
        initial_weight = self.container.weight
        self.container.add_item(self.item1)  # 0.1kg
        self.container.add_item(self.item2)  # 0.2kg

        expected_weight = self.container.base_weight + 0.1 + 0.2
        self.assertEqual(self.container.weight, expected_weight)

    def test_remove_item_removes_from_list(self):
        """Test removing items from container."""
        self.container.add_item(self.item1)
        self.container.add_item(self.item2)

        removed = self.container.remove_item("coin_1")

        self.assertEqual(removed, self.item1)
        self.assertEqual(len(self.container.items), 1)
        self.assertNotIn(self.item1, self.container.items)

    def test_remove_item_nonexistent_returns_none(self):
        """Test removing item that's not in container."""
        result = self.container.remove_item("nonexistent")

        self.assertIsNone(result)

    def test_add_item_enforces_capacity_limit(self):
        """Test that item count limit is enforced."""
        container = ContainerItem(
            "Small Bag",
            "bag_small",
            "A tiny bag",
            capacity_limit=2,
            capacity_weight=100
        )

        container.add_item(Item("A", "a", "Item A"))
        container.add_item(Item("B", "b", "Item B"))
        success = container.add_item(Item("C", "c", "Item C"))

        self.assertFalse(success)
        self.assertEqual(len(container.items), 2)

    def test_add_item_enforces_weight_limit(self):
        """Test that weight limit is enforced."""
        container = ContainerItem(
            "Bag",
            "bag_1",
            "A bag",
            capacity_limit=10,
            capacity_weight=5
        )

        heavy_item = Item("Rock", "rock_1", "A heavy rock", weight=6)
        success = container.add_item(heavy_item)

        self.assertFalse(success)
        self.assertEqual(len(container.items), 0)

    def test_add_item_rejects_nested_containers(self):
        """Test that containers cannot be put inside other containers."""
        inner_container = ContainerItem(
            "Box",
            "box_1",
            "A wooden box",
            capacity_limit=3
        )

        success = self.container.add_item(inner_container)

        self.assertFalse(success)
        self.assertEqual(len(self.container.items), 0)

    def test_set_state_changes_container_state(self):
        """Test opening and closing containers."""
        container = ContainerItem(
            "Chest",
            "chest_1",
            "A treasure chest",
            state="closed"
        )

        success = container.set_state("open")

        self.assertTrue(success)
        self.assertEqual(container.state, "open")

    def test_description_property_includes_contents(self):
        """Test that container description reflects contents."""
        self.container.add_item(self.item1)

        description = self.container.description
        self.assertIn("Coin", description)

    def test_get_contained_hides_contents_when_closed(self):
        """Test that closed containers don't reveal contents."""
        container = ContainerItem(
            "Chest",
            "chest_1",
            "A chest",
            state="closed"
        )
        container.add_item(Item("Secret", "secret_1", "A secret item"))

        description = container.get_contained()

        self.assertIn("something", description)
        self.assertNotIn("Secret", description)


class ContainerSerializationTest(unittest.TestCase):
    """Test container serialization with nested items."""

    def test_to_dict_includes_items(self):
        """Test serializing container with items."""
        container = ContainerItem("Bag", "bag_1", "A bag")
        container.add_item(Item("Coin", "coin_1", "A coin", weight=0.1))

        data = container.to_dict()

        self.assertEqual(data["name"], "Bag")
        self.assertEqual(data["capacity_limit"], 10)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["name"], "Coin")

    def test_from_dict_creates_container_with_items(self):
        """Test deserializing container with items."""
        data = {
            "name": "Bag",
            "id": "bag_1",
            "description": "A bag",
            "base_weight": 1,
            "state": "open",
            "capacity_limit": 5,
            "capacity_weight": 20,
            "items": [
                {
                    "name": "Key",
                    "id": "key_1",
                    "description": "A key",
                    "weight": 0.5,
                    "value": 10,
                    "takeable": True
                }
            ]
        }
        container = ContainerItem.from_dict(data)

        self.assertEqual(container.name, "Bag")
        self.assertEqual(len(container.items), 1)
        self.assertEqual(container.items[0].name, "Key")
        # Weight should be base_weight + contained items
        self.assertEqual(container.weight, 1.5)

    def test_to_dict_from_dict_round_trip(self):
        """Test complete serialization cycle with container."""
        original = ContainerItem("Bag", "bag_1", "A bag", weight=2)
        original.add_item(Item("Stone", "stone_1", "A stone", weight=1))
        original.add_item(Item("Stick", "stick_1", "A stick", weight=0.5))

        serialized = original.to_dict()
        reconstructed = ContainerItem.from_dict(serialized)

        self.assertEqual(reconstructed.name, original.name)
        self.assertEqual(len(reconstructed.items), 2)
        self.assertEqual(reconstructed.weight, original.weight)


class InventoryWeightTest(unittest.TestCase):
    """Test inventory weight calculations and management."""

    def test_calculate_total_inventory_weight(self):
        """Test calculating total weight of player inventory."""
        player = Player("Hero")
        player.add_item(Item("Sword", "sword_1", "A sword", weight=5))
        player.add_item(Item("Shield", "shield_1", "A shield", weight=8))
        player.add_item(Item("Potion", "potion_1", "A potion", weight=0.5))

        total_weight = sum(item.weight for item in player.inventory)

        self.assertEqual(total_weight, 13.5)

    def test_container_weight_in_inventory(self):
        """Test that container weight includes its contents."""
        player = Player("Hero")

        bag = ContainerItem("Bag", "bag_1", "A bag", weight=1)
        bag.add_item(Item("Coin", "coin_1", "A coin", weight=0.1))
        bag.add_item(Item("Gem", "gem_1", "A gem", weight=0.2))

        player.add_item(bag)

        # Bag weight should be base_weight + contents = 1 + 0.3 = 1.3
        self.assertEqual(bag.weight, 1.3)


class InventoryValueTest(unittest.TestCase):
    """Test inventory value calculations."""

    def test_calculate_total_inventory_value(self):
        """Test calculating total value of items."""
        items = [
            Item("Gold Coin", "coin_1", "A coin", value=10),
            Item("Ruby", "ruby_1", "A ruby", value=100),
            Item("Diamond", "diamond_1", "A diamond", value=500)
        ]

        total_value = sum(item.value for item in items)

        self.assertEqual(total_value, 610)

    def test_weapon_value(self):
        """Test that weapons have value."""
        weapon = Weapon("Sword", "sword_1", "A sword", value=75, damage=20)

        self.assertEqual(weapon.value, 75)


if __name__ == "__main__":
    unittest.main()
