"""
Comprehensive tests for utils module (commands).

Tests cover:
- get_player_inventory with regular items
- get_player_inventory with container items
- get_player_inventory with empty inventory
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.utils import get_player_inventory
from tests.test_helpers import create_mock_player, create_mock_item


class GetPlayerInventoryTest(unittest.TestCase):
    """Test get_player_inventory functionality."""

    def test_get_player_inventory_returns_item_names(self):
        """Test get_player_inventory returns space-separated item names."""
        # Arrange
        item1 = create_mock_item(name="sword")
        item2 = create_mock_item(name="shield")
        item3 = create_mock_item(name="potion")
        player = create_mock_player(inventory=[item1, item2, item3])

        # Act
        result = get_player_inventory(player)

        # Assert
        self.assertIn("sword", result)
        self.assertIn("shield", result)
        self.assertIn("potion", result)

    def test_get_player_inventory_returns_empty_string_for_empty_inventory(self):
        """Test get_player_inventory returns empty string for empty inventory."""
        # Arrange
        player = create_mock_player(inventory=[])

        # Act
        result = get_player_inventory(player)

        # Assert
        self.assertEqual(result, "")

    def test_get_player_inventory_shows_container_contents(self):
        """Test get_player_inventory shows contents of container items."""
        # Arrange
        from models.ContainerItem import ContainerItem

        # Create a regular item
        item1 = create_mock_item(name="sword")

        # Create a mock container item
        container = Mock(spec=ContainerItem)
        container.name = "backpack"
        container.get_contained = Mock(return_value="Contents: gold coin, map")

        player = create_mock_player(inventory=[item1, container])

        # Act
        result = get_player_inventory(player)

        # Assert
        self.assertIn("sword", result)
        self.assertIn("backpack", result)
        self.assertIn("Contents: gold coin, map", result)
        container.get_contained.assert_called_once()

    def test_get_player_inventory_handles_multiple_containers(self):
        """Test get_player_inventory handles multiple container items."""
        # Arrange
        from models.ContainerItem import ContainerItem

        container1 = Mock(spec=ContainerItem)
        container1.name = "backpack"
        container1.get_contained = Mock(return_value="Contents: gold coin")

        container2 = Mock(spec=ContainerItem)
        container2.name = "pouch"
        container2.get_contained = Mock(return_value="Contents: key")

        player = create_mock_player(inventory=[container1, container2])

        # Act
        result = get_player_inventory(player)

        # Assert
        self.assertIn("backpack", result)
        self.assertIn("pouch", result)
        self.assertIn("Contents: gold coin", result)
        self.assertIn("Contents: key", result)

    def test_get_player_inventory_formats_output_correctly(self):
        """Test get_player_inventory formats output with items on same line."""
        # Arrange
        item1 = create_mock_item(name="sword")
        item2 = create_mock_item(name="shield")
        player = create_mock_player(inventory=[item1, item2])

        # Act
        result = get_player_inventory(player)

        # Assert
        # Items should be space-separated
        self.assertEqual(result, "sword shield")

    def test_get_player_inventory_single_item(self):
        """Test get_player_inventory handles single item."""
        # Arrange
        item = create_mock_item(name="sword")
        player = create_mock_player(inventory=[item])

        # Act
        result = get_player_inventory(player)

        # Assert
        self.assertEqual(result, "sword")


if __name__ == "__main__":
    unittest.main()
