"""
Comprehensive tests for player interaction commands.

Tests cover:
- Give command (normal and reversed syntax)
- Steal command (success and failure cases)
- Dexterity-based steal mechanics
- Multi-player scenarios
- Inventory capacity checks
- Message broadcasting
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.player_interaction import handle_give, handle_steal
from models.Player import Player
from models.Item import Item
from models.Room import Room
from models.Mobile import Mobile
from managers.game_state import GameState


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """Base class for async tests."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Player("Alice")
        self.player.current_room = "test_room"

        self.other_player = Player("Bob")
        self.other_player.current_room = "test_room"

        self.remote_player = Player("Charlie")
        self.remote_player.current_room = "other_room"

        # Create game state
        self.game_state = GameState()
        self.room = Room("test_room", "Test Room", "A test room")
        self.game_state.add_room(self.room)

        # Mock player manager
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()

        # Mock sio and utils
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

        # Set up online sessions
        self.online_sessions = {
            "sid1": {"player": self.player},
            "sid2": {"player": self.other_player},
            "sid3": {"player": self.remote_player},
        }

        # Create test items
        self.item1 = Item("Sword", "sword_1", "A sharp sword", weight=5, value=50)
        self.item2 = Item("Gem", "gem_1", "A shiny gem", weight=1, value=100)


class GiveCommandTest(AsyncTestCase):
    """Test give command functionality."""

    async def test_give_item_to_player(self):
        """Test giving an item to another player."""
        self.player.add_item(self.item1)

        cmd = {
            "verb": "give",
            "instrument": "sword",
            "subject": "Bob",
            "reversed_syntax": True,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("given to Bob", result)
        self.assertIn(self.item1, self.other_player.inventory)
        self.assertNotIn(self.item1, self.player.inventory)

    async def test_give_with_normal_syntax(self):
        """Test give with normal syntax (give player item)."""
        self.player.add_item(self.item1)

        cmd = {
            "verb": "give",
            "subject": "Bob",
            "instrument": "sword",
            "reversed_syntax": False,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("given to Bob", result)
        self.assertIn(self.item1, self.other_player.inventory)

    async def test_give_without_item_returns_error(self):
        """Test give without specifying item."""
        cmd = {"verb": "give", "subject": "Bob"}

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "What do you want to give?")

    async def test_give_without_target_returns_error(self):
        """Test give without specifying target."""
        self.player.add_item(self.item1)

        cmd = {"verb": "give", "instrument": "sword", "reversed_syntax": True}

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "To whom do you want to give something?")

    async def test_give_item_not_in_inventory(self):
        """Test giving item player doesn't have."""
        cmd = {
            "verb": "give",
            "instrument": "sword",
            "subject": "Bob",
            "reversed_syntax": True,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't have", result)

    async def test_give_to_player_not_in_room(self):
        """Test giving to player not in same room."""
        self.player.add_item(self.item1)

        cmd = {
            "verb": "give",
            "instrument": "sword",
            "subject": "Charlie",  # In different room
            "reversed_syntax": True,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't see", result)

    async def test_give_when_target_inventory_full(self):
        """Test giving item when target's inventory is full."""
        self.player.add_item(self.item1)

        # Fill up Bob's inventory
        max_items = self.other_player.carrying_capacity_num
        for i in range(max_items):
            filler = Item(f"Item{i}", f"item_{i}", "Filler", weight=0.1)
            self.other_player.add_item(filler)

        cmd = {
            "verb": "give",
            "instrument": "sword",
            "subject": "Bob",
            "reversed_syntax": True,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("cannot carry", result)
        self.assertIn(self.item1, self.player.inventory)  # Still with Alice

    async def test_give_broadcasts_messages(self):
        """Test that give broadcasts to target and others."""
        self.player.add_item(self.item1)

        # Add a third player in same room
        observer = Player("Observer")
        observer.current_room = "test_room"
        self.online_sessions["sid4"] = {"player": observer}

        cmd = {
            "verb": "give",
            "instrument": "sword",
            "subject": "Bob",
            "reversed_syntax": True,
        }

        await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should send message to Bob and Observer
        self.assertEqual(self.utils.send_message.call_count, 2)

    async def test_give_with_bound_objects(self):
        """Test give with pre-bound objects."""
        self.player.add_item(self.item1)

        cmd = {
            "verb": "give",
            "instrument": "sword",
            "instrument_object": self.item1,
            "subject": "Bob",
            "subject_object": self.other_player,
            "reversed_syntax": True,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("given to Bob", result)
        self.assertIn(self.item1, self.other_player.inventory)

    async def test_give_to_mobile_fails(self):
        """Test that giving items to mobiles is not allowed."""
        self.player.add_item(self.item1)

        # Create a mobile in the same room
        elder = Mobile(
            name="Elder",
            id="elder_1",
            description="The village elder",
            current_room="test_room",
        )

        cmd = {
            "verb": "give",
            "instrument": "sword",
            "instrument_object": self.item1,
            "subject": "Elder",
            "subject_object": elder,
            "reversed_syntax": True,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should reject giving to mobile (that doesn't accept items)
        self.assertIn("doesn't want anything from you", result)
        # Item should still be with player
        self.assertIn(self.item1, self.player.inventory)


class StealCommandTest(AsyncTestCase):
    """Test steal command functionality."""

    async def test_steal_requires_target(self):
        """Test steal without target returns error."""
        cmd = {"verb": "steal", "instrument": "sword"}

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "Steal from whom?")

    async def test_steal_requires_item(self):
        """Test steal without item returns error."""
        cmd = {"verb": "steal", "subject": "Bob"}

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "What do you want to steal?")

    async def test_steal_from_player_not_in_room(self):
        """Test stealing from player not in same room."""
        cmd = {
            "verb": "steal",
            "subject": "Charlie",  # In different room
            "instrument": "sword",
        }

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't see", result)

    async def test_steal_item_target_doesnt_have(self):
        """Test stealing item target doesn't have."""
        cmd = {"verb": "steal", "subject": "Bob", "instrument": "sword"}

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("doesn't have", result)

    @patch("random.randint")
    async def test_steal_success(self, mock_randint):
        """Test successful steal attempt."""
        # Force successful steal (roll = 1, will be <= steal_chance)
        mock_randint.return_value = 1

        self.other_player.add_item(self.item1)

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped to become target
            "instrument": "Bob",  # Will be swapped to become item
            "preposition": "from",
        }

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("stolen from Bob", result)
        self.assertIn(self.item1, self.player.inventory)
        self.assertNotIn(self.item1, self.other_player.inventory)

    @patch("random.randint")
    async def test_steal_failure(self, mock_randint):
        """Test failed steal attempt."""
        # Force failed steal (roll = 100, will be > steal_chance)
        mock_randint.return_value = 100

        self.other_player.add_item(self.item1)

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped to become target
            "instrument": "Bob",  # Will be swapped to become item
            "preposition": "from",
        }

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("discovers your attempt", result)
        self.assertNotIn(self.item1, self.player.inventory)
        self.assertIn(self.item1, self.other_player.inventory)

    @patch("random.randint")
    async def test_steal_with_high_dexterity(self, mock_randint):
        """Test steal chance calculation with high dexterity."""
        # Set high dexterity for thief
        self.player.dexterity = 100
        self.other_player.dexterity = 10

        # Roll that should succeed with high dex
        mock_randint.return_value = 80

        self.other_player.add_item(self.item1)

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped to become target
            "instrument": "Bob",  # Will be swapped to become item
            "preposition": "from",
        }

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # With 100 vs 10 dex, steal chance should be very high
        # 100/(100+10) * 100 = ~90.9%, capped at 90%
        # Roll of 80 should succeed
        self.assertIn("stolen", result)

    @patch("random.randint")
    async def test_steal_with_low_dexterity(self, mock_randint):
        """Test steal chance calculation with low dexterity."""
        # Set low dexterity for thief
        self.player.dexterity = 10
        self.other_player.dexterity = 100

        # Roll that would fail with low dex
        mock_randint.return_value = 20

        self.other_player.add_item(self.item1)

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped to become target
            "instrument": "Bob",  # Will be swapped to become item
            "preposition": "from",
        }

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # With 10 vs 100 dex, steal chance should be low
        # 10/(10+100) * 100 = ~9%, but minimum is 10%
        # Roll of 20 should fail
        self.assertIn("discovers", result)

    @patch("random.randint")
    async def test_steal_broadcasts_on_success(self, mock_randint):
        """Test that successful steal broadcasts to all players."""
        mock_randint.return_value = 1

        self.other_player.add_item(self.item1)

        # Add observer
        observer = Player("Observer")
        observer.current_room = "test_room"
        self.online_sessions["sid4"] = {"player": observer}

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped to become target
            "instrument": "Bob",  # Will be swapped to become item
            "preposition": "from",
        }

        await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should send to Bob and Observer
        self.assertEqual(self.utils.send_message.call_count, 2)

    @patch("random.randint")
    async def test_steal_broadcasts_on_failure(self, mock_randint):
        """Test that failed steal broadcasts to all players."""
        mock_randint.return_value = 100

        self.other_player.add_item(self.item1)

        # Add observer
        observer = Player("Observer")
        observer.current_room = "test_room"
        self.online_sessions["sid4"] = {"player": observer}

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped to become target
            "instrument": "Bob",  # Will be swapped to become item
            "preposition": "from",
        }

        await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should send to Bob and Observer
        self.assertEqual(self.utils.send_message.call_count, 2)

    @patch("random.randint")
    async def test_steal_when_thief_inventory_full(self, mock_randint):
        """Test steal fails if thief's inventory is full."""
        mock_randint.return_value = 1

        self.other_player.add_item(self.item1)

        # Fill up Alice's inventory
        max_items = self.player.carrying_capacity_num
        for i in range(max_items):
            filler = Item(f"Item{i}", f"item_{i}", "Filler", weight=0.1)
            self.player.add_item(filler)

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped to become target
            "instrument": "Bob",  # Will be swapped to become item
            "preposition": "from",
        }

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("can't carry", result)
        self.assertIn(self.item1, self.other_player.inventory)

    async def test_steal_with_from_preposition(self):
        """Test steal with 'from' preposition syntax."""
        self.other_player.add_item(self.item1)

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped
            "instrument": "Bob",  # Will be swapped
            "preposition": "from",
        }

        with patch("random.randint", return_value=1):
            result = await handle_steal(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("stolen", result)

    async def test_steal_from_mobile_fails(self):
        """Test that stealing from mobiles is not allowed."""
        # Create a mobile in the same room
        merchant = Mobile(
            name="Merchant",
            id="merchant_1",
            description="A traveling merchant",
            current_room="test_room",
        )

        cmd = {
            "verb": "steal",
            "subject": "Merchant",
            "subject_object": merchant,
            "instrument": "key",
        }

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should reject stealing from mobile
        self.assertIn("cannot steal from", result)


class PlayerInteractionEdgeCasesTest(AsyncTestCase):
    """Test edge cases and special scenarios."""

    async def test_give_to_self_fails(self):
        """Test that you can't find yourself as a target for give."""
        self.player.add_item(self.item1)

        cmd = {
            "verb": "give",
            "instrument": "sword",
            "subject": "Alice",  # Self
            "reversed_syntax": True,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should not find self as target
        self.assertIn("don't see", result)

    async def test_steal_from_self_fails(self):
        """Test that you can't steal from yourself."""
        self.player.add_item(self.item1)

        cmd = {"verb": "steal", "subject": "Alice", "instrument": "sword"}  # Self

        result = await handle_steal(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should not find self as target
        self.assertIn("don't see", result)

    async def test_give_case_insensitive_name_matching(self):
        """Test case-insensitive player name matching."""
        self.player.add_item(self.item1)

        cmd = {
            "verb": "give",
            "instrument": "sword",
            "subject": "bob",  # Lowercase
            "reversed_syntax": True,
        }

        result = await handle_give(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("given to Bob", result)

    async def test_steal_case_insensitive_name_matching(self):
        """Test case-insensitive player name matching for steal."""
        self.other_player.add_item(self.item1)

        cmd = {
            "verb": "steal",
            "subject": "sword",  # Will be swapped to become target
            "instrument": "bob",  # Will be swapped to become item (lowercase)
            "preposition": "from",
        }

        with patch("random.randint", return_value=1):
            result = await handle_steal(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        self.assertIn("stolen", result)


if __name__ == "__main__":
    unittest.main()
