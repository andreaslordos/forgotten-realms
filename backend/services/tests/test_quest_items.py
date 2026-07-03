# backend/services/tests/test_quest_items.py
"""Tests for the self-healing quest item service."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.game_state import GameState
from models.ContainerItem import ContainerItem
from models.Item import Item
from models.Room import Room
from services.quest_items import (
    clear_quest_item_registry,
    ensure_quest_items,
    register_quest_item,
)


class QuestItemRestorationTest(unittest.TestCase):
    """Test ensure_quest_items restores missing progression items."""

    def setUp(self):
        """Set up a small world with a chest and a quest token."""
        clear_quest_item_registry()
        self.game_state = GameState()
        self.cellar = Room("cellar", "Cellar", "A damp cellar.")
        self.chest = ContainerItem(
            name="chest",
            id="cellar_chest",
            description="An iron-bound chest sits here.",
            weight=50,
            value=0,
            takeable=False,
        )
        self.cellar.add_item(self.chest)
        self.game_state.add_room(self.cellar)

        self.token = Item(
            "token", "mist_token", "A silver token of passage.", weight=1, value=0
        )
        self.online_sessions = {}

    def tearDown(self):
        """Clear registry so tests stay independent."""
        clear_quest_item_registry()

    def _register_token(self, done=False):
        register_quest_item(
            self.token,
            room_id="cellar",
            container_id="cellar_chest",
            done_check=lambda gs: done,
        )

    def test_ensure_quest_items_restores_missing_item_into_container(self):
        """Test a vanished item is recreated inside its source container."""
        # Arrange
        self._register_token()

        # Act
        restored = ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertEqual(restored, ["mist_token"])
        self.assertEqual(len(self.chest.items), 1)
        self.assertEqual(self.chest.items[0].id, "mist_token")

    def test_ensure_quest_items_skips_item_in_room(self):
        """Test no restoration happens while the item sits in a room."""
        # Arrange
        self._register_token()
        self.cellar.add_item(self.token)

        # Act
        restored = ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertEqual(restored, [])

    def test_ensure_quest_items_skips_item_in_container(self):
        """Test no restoration happens while the item is inside a container."""
        # Arrange
        self._register_token()
        self.chest.items.append(self.token)

        # Act
        restored = ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertEqual(restored, [])
        self.assertEqual(len(self.chest.items), 1)

    def test_ensure_quest_items_skips_item_carried_by_player(self):
        """Test no restoration happens while a player carries the item."""

        # Arrange
        class FakePlayer:
            def __init__(self, inventory):
                self.inventory = inventory

        self._register_token()
        sessions = {"sid1": {"player": FakePlayer([self.token])}}

        # Act
        restored = ensure_quest_items(self.game_state, sessions)

        # Assert
        self.assertEqual(restored, [])

    def test_ensure_quest_items_skips_item_hidden_in_room(self):
        """Test hidden (not yet revealed) items count as present."""
        # Arrange
        self._register_token()
        self.cellar.add_hidden_item(self.token, lambda gs: False)

        # Act
        restored = ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertEqual(restored, [])

    def test_ensure_quest_items_skips_when_done(self):
        """Test items whose gate is already passed are not restored."""
        # Arrange
        self._register_token(done=True)

        # Act
        restored = ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertEqual(restored, [])
        self.assertEqual(self.chest.items, [])

    def test_ensure_quest_items_falls_back_to_room_floor(self):
        """Test a missing container drops the replacement on the floor."""
        # Arrange
        self.cellar.remove_item(self.chest)
        self._register_token()

        # Act
        restored = ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertEqual(restored, ["mist_token"])
        self.assertEqual(self.cellar.items[-1].id, "mist_token")

    def test_ensure_quest_items_restores_a_fresh_copy(self):
        """Test the restored item is a copy, not the registered template."""
        # Arrange
        self._register_token()

        # Act
        ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertIsNot(self.chest.items[0], self.token)
        self.assertEqual(self.chest.items[0].name, self.token.name)

    def test_ensure_quest_items_handles_missing_room(self):
        """Test a registration pointing at a nonexistent room is skipped."""
        # Arrange
        register_quest_item(self.token, room_id="nowhere")

        # Act
        restored = ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertEqual(restored, [])

    def test_ensure_quest_items_sees_item_in_carried_container(self):
        """Test an item inside a container in a player's inventory counts."""

        # Arrange: token nested inside a pouch the player carries.
        class FakePlayer:
            def __init__(self, inventory):
                self.inventory = inventory

        pouch = ContainerItem(
            name="pouch",
            id="belt_pouch",
            description="A small leather pouch.",
            weight=1,
            value=0,
            takeable=True,
        )
        pouch.items.append(self.token)
        self._register_token()
        sessions = {"sid1": {"player": FakePlayer([pouch])}}

        # Act
        restored = ensure_quest_items(self.game_state, sessions)

        # Assert: no duplicate minted.
        self.assertEqual(restored, [])

    def test_ensure_quest_items_treats_swamped_item_as_gone(self):
        """Test an item teleported into a treasure sink room is restored."""
        # Arrange: a swamp room pointing at an unreachable sink holding the
        # token — swamped quest items must be restored to their source.
        swamp = Room("bog", "Bog", "A treasure-hungry bog.")
        swamp.treasure_destination = "under_bog"
        sink = Room("under_bog", "Under the Bog", "Lost things gather here.")
        sink.add_item(self.token)
        self.game_state.add_room(swamp)
        self.game_state.add_room(sink)
        self._register_token()

        # Act
        restored = ensure_quest_items(self.game_state, self.online_sessions)

        # Assert
        self.assertEqual(restored, ["mist_token"])
        self.assertEqual(self.chest.items[0].id, "mist_token")


if __name__ == "__main__":
    unittest.main()
