"""
Comprehensive tests for StatefulItem class.

Tests cover:
- Stateful item creation with states
- State descriptions and transitions
- Item interactions and linking
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.StatefulItem import StatefulItem


class StatefulItemTest(unittest.TestCase):
    """Test StatefulItem with state management."""

    def test___init___with_state(self):
        """Test creating a stateful item."""
        item = StatefulItem("Door", "door_1", "A wooden door, closed", state="closed")

        self.assertEqual(item.state, "closed")
        self.assertIn("closed", item.state_descriptions)

    def test_add_state_description_adds_to_dict(self):
        """Test adding multiple state descriptions."""
        item = StatefulItem("Lamp", "lamp_1", "An unlit lamp", state="unlit")
        item.add_state_description("lit", "A brightly burning lamp")

        self.assertIn("unlit", item.state_descriptions)
        self.assertIn("lit", item.state_descriptions)

    def test_set_state_updates_description(self):
        """Test that changing state updates description."""
        item = StatefulItem("Door", "door_1", "A closed door", state="closed")
        item.add_state_description("open", "An open door")

        success = item.set_state("open")

        self.assertTrue(success)
        self.assertEqual(item.state, "open")
        self.assertEqual(item.description, "An open door")

    def test_set_state_invalid_returns_false(self):
        """Test that setting invalid state returns False."""
        item = StatefulItem("Switch", "switch_1", "A switch", state="off")

        success = item.set_state("on")  # 'on' state not defined

        self.assertFalse(success)
        self.assertEqual(item.state, "off")  # State unchanged

    def test_add_interaction_adds_to_dict(self):
        """Test adding interactions to stateful items."""
        item = StatefulItem("Chest", "chest_1", "A locked chest", state="locked")
        item.add_interaction(
            verb="unlock",
            required_instrument="key",
            target_state="unlocked",
            message="You unlock the chest with the key.",
        )

        self.assertIn("unlock", item.interactions)
        interaction = item.interactions["unlock"][0]
        self.assertEqual(interaction["required_instrument"], "key")
        self.assertEqual(interaction["target_state"], "unlocked")

    def test_link_item_adds_to_linked_items(self):
        """Test linking stateful items together."""
        door1 = StatefulItem("Door", "door_north", "A door", state="closed")
        door1.link_item("door_south")

        self.assertIn("door_south", door1.linked_items)

    def test_get_state_returns_current_state(self):
        """Test get_state returns the current state."""
        item = StatefulItem("Door", "door_1", "A closed door", state="closed")

        self.assertEqual(item.get_state(), "closed")

    def test_to_dict_includes_state_data(self):
        """Test to_dict includes state information."""
        item = StatefulItem("Door", "door_1", "A closed door", state="closed")
        item.add_state_description("open", "An open door")
        item.add_interaction("open", target_state="open")
        item.room_id = "room_1"
        item.link_item("door_2")

        data = item.to_dict()

        self.assertEqual(data["state"], "closed")
        self.assertIn("state_descriptions", data)
        self.assertIn("interactions", data)
        self.assertEqual(data["room_id"], "room_1")
        self.assertIn("door_2", data["linked_items"])

    def test_from_dict_reconstructs_stateful_item(self):
        """Test from_dict creates StatefulItem from dictionary."""
        data = {
            "name": "Door",
            "id": "door_1",
            "description": "A closed door",
            "weight": 50,
            "value": 10,
            "takeable": False,
            "state": "closed",
            "state_descriptions": {"closed": "A closed door", "open": "An open door"},
            "interactions": {"open": [{"target_state": "open"}]},
            "room_id": "room_1",
            "linked_items": ["door_2"],
        }

        item = StatefulItem.from_dict(data)

        self.assertEqual(item.state, "closed")
        self.assertEqual(item.state_descriptions, data["state_descriptions"])
        self.assertEqual(item.interactions, data["interactions"])
        self.assertEqual(item.room_id, "room_1")
        self.assertIn("door_2", item.linked_items)


if __name__ == "__main__":
    unittest.main()
