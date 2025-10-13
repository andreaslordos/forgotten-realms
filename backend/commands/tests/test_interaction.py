"""
Comprehensive tests for interaction module.

Tests cover:
- handle_interaction with standard syntax
- handle_interaction with reversed syntax
- State-based interactions
- Instrument requirements
- Exit management (add/remove exits)
- Reciprocal exits
- Item consumption and dropping
- Broadcasting to other players
- Error cases (item not found, wrong state, missing instrument)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, call

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.interaction import handle_interaction, register_interaction_verbs
from models.Item import Item
from models.StatefulItem import StatefulItem


class InteractionHandlerBasicTest(unittest.IsolatedAsyncioTestCase):
    """Test basic interaction functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []
        self.player.remove_item = Mock()

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_to_player = AsyncMock()
        self.utils.broadcast_to_room = AsyncMock()

        self.current_room = Mock()
        self.current_room.room_id = "test_room"
        self.current_room.items = []
        self.current_room.exits = {}
        self.current_room.get_items = Mock(return_value=[])
        self.current_room.add_exit = Mock()
        self.current_room.remove_exit = Mock()
        self.current_room.add_item = Mock()
        self.current_room.remove_item = Mock()
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_interaction_with_stateful_item_in_room(self):
        """Test interaction with stateful item in room."""
        stateful_item = StatefulItem(
            name="wooden door",
            id="door_1",
            description="A sturdy wooden door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A sturdy wooden door")
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")
        self.assertIn("open", result.lower())

    async def test_handle_interaction_with_item_in_inventory(self):
        """Test interaction with item in player's inventory."""
        stateful_item = StatefulItem(
            name="small box",
            id="box_1",
            description="A lockable box",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed box")
        stateful_item.add_state_description("open", "An open box")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the box."
        )
        self.player.inventory = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "box",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")
        self.assertIn("open", result.lower())


class InteractionStateTransitionTest(unittest.IsolatedAsyncioTestCase):
    """Test state-based interaction logic."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_to_player = AsyncMock()
        self.utils.broadcast_to_room = AsyncMock()

        self.current_room = Mock()
        self.current_room.room_id = "test_room"
        self.current_room.items = []
        self.current_room.get_items = Mock(return_value=[])
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_interaction_wrong_state_shows_error(self):
        """Test interaction fails when item is in wrong state."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="open"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        # State should not change
        self.assertEqual(stateful_item.state, "open")
        self.assertIn("can't", result.lower())

    async def test_handle_interaction_changes_state_correctly(self):
        """Test interaction changes state from from_state to target_state."""
        stateful_item = StatefulItem(
            name="valve",
            id="valve_1",
            description="A valve",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed valve")
        stateful_item.add_state_description("open", "An open valve")
        stateful_item.add_interaction(
            verb="turn",
            from_state="closed",
            target_state="open",
            message="You turn the valve open."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "turn",
            "subject": "valve",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")


class InteractionInstrumentTest(unittest.IsolatedAsyncioTestCase):
    """Test instrument requirements and consumption."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []
        self.player.remove_item = Mock()

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_to_player = AsyncMock()
        self.utils.broadcast_to_room = AsyncMock()

        self.current_room = Mock()
        self.current_room.room_id = "test_room"
        self.current_room.items = []
        self.current_room.add_item = Mock()
        self.current_room.get_items = Mock(return_value=[])
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_interaction_requires_instrument(self):
        """Test interaction fails without required instrument."""
        stateful_item = StatefulItem(
            name="lock",
            id="lock_1",
            description="A locked door",
            state="locked"
        )
        stateful_item.add_state_description("locked", "A locked door")
        stateful_item.add_state_description("unlocked", "An unlocked door")
        stateful_item.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="unlocked",
            required_instrument="key",
            message="You unlock the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "unlock",
            "subject": "lock",
            "subject_object": stateful_item,
            "instrument": None
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        # State should not change
        self.assertEqual(stateful_item.state, "locked")
        self.assertIn("need", result.lower())

    async def test_handle_interaction_succeeds_with_correct_instrument(self):
        """Test interaction succeeds when correct instrument is provided."""
        key = Item(name="bronze key", id="key_1", description="A bronze key")
        self.player.inventory = [key]

        stateful_item = StatefulItem(
            name="lock",
            id="lock_1",
            description="A locked door",
            state="locked"
        )
        stateful_item.add_state_description("locked", "A locked door")
        stateful_item.add_state_description("unlocked", "An unlocked door")
        stateful_item.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="unlocked",
            required_instrument="key",
            message="You unlock the door with the key."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "unlock",
            "subject": "lock",
            "subject_object": stateful_item,
            "instrument": "key",
            "instrument_object": key
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "unlocked")
        self.assertIn("unlock", result.lower())

    async def test_handle_interaction_consumes_instrument_when_specified(self):
        """Test interaction consumes instrument when consume_instrument is True."""
        axe = Item(name="rusty axe", id="axe_1", description="An old axe")
        self.player.inventory = [axe]

        stateful_item = StatefulItem(
            name="tree",
            id="tree_1",
            description="A tree",
            state=None
        )
        stateful_item.add_interaction(
            verb="chop",
            required_instrument="axe",
            consume_instrument=True,
            message="You chop down the tree. The axe breaks."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "chop",
            "subject": "tree",
            "subject_object": stateful_item,
            "instrument": "axe",
            "instrument_object": axe
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        # Axe should be removed from inventory
        self.player.remove_item.assert_called_once_with(axe)

    async def test_handle_interaction_drops_instrument_when_specified(self):
        """Test interaction drops instrument to room when drop_instrument is True."""
        torch = Item(name="torch", id="torch_1", description="A burning torch")
        self.player.inventory = [torch]

        stateful_item = StatefulItem(
            name="candle",
            id="candle_1",
            description="An unlit candle",
            state="unlit"
        )
        stateful_item.add_state_description("unlit", "An unlit candle")
        stateful_item.add_state_description("lit", "A lit candle")
        stateful_item.add_interaction(
            verb="light",
            from_state="unlit",
            target_state="lit",
            required_instrument="torch",
            drop_instrument=True,
            message="You light the candle with the torch."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "light",
            "subject": "candle",
            "subject_object": stateful_item,
            "instrument": "torch",
            "instrument_object": torch
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        # Torch should be removed from inventory and added to room
        self.player.remove_item.assert_called_once_with(torch)
        self.current_room.add_item.assert_called_once_with(torch)


class InteractionExitManagementTest(unittest.IsolatedAsyncioTestCase):
    """Test exit manipulation (add/remove exits)."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_to_player = AsyncMock()
        self.utils.broadcast_to_room = AsyncMock()

        self.current_room = Mock()
        self.current_room.room_id = "test_room"
        self.current_room.items = []
        self.current_room.exits = {}
        self.current_room.get_items = Mock(return_value=[])
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_interaction_adds_exit(self):
        """Test interaction adds new exit to room."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the door, revealing a passage north.",
            add_exit=("north", "secret_room")
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertIn("north", self.current_room.exits)
        self.assertEqual(self.current_room.exits["north"], "secret_room")

    async def test_handle_interaction_removes_exit(self):
        """Test interaction removes exit from room."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="open"
        )
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_interaction(
            verb="close",
            from_state="open",
            target_state="closed",
            message="You close the door.",
            remove_exit="north"
        )
        self.current_room.items = [stateful_item]
        self.current_room.exits = {"north": "secret_room"}
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "close",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertNotIn("north", self.current_room.exits)


class InteractionItemRemovalTest(unittest.IsolatedAsyncioTestCase):
    """Test item removal after interaction."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_to_player = AsyncMock()
        self.utils.broadcast_to_room = AsyncMock()

        self.current_room = Mock()
        self.current_room.room_id = "test_room"
        self.current_room.items = []
        self.current_room.remove_item = Mock()
        self.current_room.get_items = Mock(return_value=[])
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_interaction_removes_item_when_specified(self):
        """Test interaction removes item when remove_item is True."""
        stateful_item = StatefulItem(
            name="paper",
            id="paper_1",
            description="A piece of paper",
            state=None
        )
        stateful_item.add_interaction(
            verb="burn",
            message="You burn the paper. It turns to ash.",
            remove_item=True
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "burn",
            "subject": "paper",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.current_room.remove_item.assert_called_once_with(stateful_item)


class InteractionErrorCasesTest(unittest.IsolatedAsyncioTestCase):
    """Test error cases and edge conditions."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_to_player = AsyncMock()
        self.utils.broadcast_to_room = AsyncMock()

        self.current_room = Mock()
        self.current_room.room_id = "test_room"
        self.current_room.items = []
        self.current_room.get_items = Mock(return_value=[])
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_interaction_with_non_stateful_item(self):
        """Test interaction fails with non-stateful item."""
        regular_item = Item(name="rock", id="rock_1", description="A rock")
        self.current_room.items = [regular_item]
        self.current_room.get_items.return_value = [regular_item]

        cmd = {
            "verb": "push",
            "subject": "rock",
            "subject_object": regular_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertIn("can't", result.lower())

    async def test_handle_interaction_with_no_subject_object(self):
        """Test interaction fails when subject_object is None."""
        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": None
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertIn("can't", result.lower())

    async def test_handle_interaction_with_no_matching_verb(self):
        """Test interaction fails when verb not in item's interactions."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state=None
        )
        stateful_item.add_interaction(
            verb="open",
            message="You open the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "push",  # Not in interactions
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertIn("can't", result.lower())

    async def test_handle_interaction_with_no_subject(self):
        """Test interaction fails when no subject provided."""
        cmd = {
            "verb": "open",
            "subject": None,
            "subject_object": None
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertIn("What do you want", result)

    async def test_handle_interaction_with_wrong_instrument(self):
        """Test interaction fails when wrong instrument provided."""
        key = Item(name="bronze sword", id="sword_1", description="A sword")
        self.player.inventory = [key]

        stateful_item = StatefulItem(
            name="lock",
            id="lock_1",
            description="A locked door",
            state="locked"
        )
        stateful_item.add_state_description("locked", "A locked door")
        stateful_item.add_state_description("unlocked", "An unlocked door")
        stateful_item.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="unlocked",
            required_instrument="key",
            message="You unlock the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "unlock",
            "subject": "lock",
            "subject_object": stateful_item,
            "instrument": "sword",
            "instrument_object": key
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "locked")
        self.assertIn("can't", result.lower())

    async def test_handle_interaction_with_conditional_fn_false(self):
        """Test interaction fails when conditional function returns False."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the door.",
            conditional_fn=lambda player, game_state: False  # Always fails
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "closed")
        self.assertIn("can't", result.lower())

    async def test_handle_interaction_with_non_list_interactions(self):
        """Test interaction handles non-list interactions (backward compatibility)."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        # Manually set interactions as non-list
        stateful_item.interactions = {
            "open": {
                "from_state": "closed",
                "target_state": "open",
                "message": "You open the door."
            }
        }
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")
        self.assertIn("open", result.lower())

    async def test_handle_interaction_with_non_dict_interaction_in_list(self):
        """Test interaction skips non-dict interactions in list."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        # Add a valid interaction after a non-dict one
        stateful_item.interactions = {
            "open": [
                "invalid",  # Non-dict, should be skipped
                {
                    "from_state": "closed",
                    "target_state": "open",
                    "message": "You open the door."
                }
            ]
        }
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")
        self.assertIn("open", result.lower())

    async def test_handle_interaction_removes_exit_when_not_present(self):
        """Test interaction handles remove_exit when exit doesn't exist."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="open"
        )
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_interaction(
            verb="close",
            from_state="open",
            target_state="closed",
            message="You close the door.",
            remove_exit="north"  # Exit doesn't exist
        )
        self.current_room.items = [stateful_item]
        self.current_room.exits = {}  # No north exit
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "close",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "closed")

    async def test_handle_interaction_with_reciprocal_exit(self):
        """Test interaction creates reciprocal exit."""
        target_room = Mock()
        target_room.room_id = "target_room"
        target_room.exits = {}
        self.game_state.get_room.side_effect = lambda room_id: self.current_room if room_id == "test_room" else target_room

        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the door.",
            reciprocal_exit=("target_room", "south", "test_room")
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertIn("south", target_room.exits)
        self.assertEqual(target_room.exits["south"], "test_room")

    async def test_handle_interaction_with_show_room_desc(self):
        """Test interaction shows room description when show_room_desc is True."""
        from unittest.mock import patch

        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        # Manually set interaction with show_room_desc
        stateful_item.interactions = {
            "open": [{
                "from_state": "closed",
                "target_state": "open",
                "message": "You open the door.",
                "show_room_desc": True
            }]
        }
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        with patch('commands.interaction.build_look_description', return_value="Room description here"):
            result = await handle_interaction(cmd, self.player, self.game_state,
                                    self.player_manager, self.online_sessions,
                                    self.sio, self.utils)

            self.assertIn("Room description", result)

    async def test_handle_interaction_exception_handling(self):
        """Test interaction handles exceptions gracefully."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        # Create an interaction that will cause an exception
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.interactions = {
            "open": [{
                "from_state": "closed",
                "target_state": "open",
                "message": "You open the door."
            }]
        }
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        # Make set_state raise an exception
        stateful_item.set_state = Mock(side_effect=Exception("Test error"))

        cmd = {
            "verb": "open",
            "subject": "door",
            "subject_object": stateful_item
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertIn("Error processing command", result)


class InteractionReversedSyntaxTest(unittest.IsolatedAsyncioTestCase):
    """Test reversed syntax interactions."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

        self.current_room = Mock()
        self.current_room.room_id = "test_room"
        self.current_room.items = []
        self.current_room.get_items = Mock(return_value=[])
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_interaction_reversed_syntax_with_instrument_obj(self):
        """Test reversed syntax with instrument_obj having interactions."""
        key = Item(name="key", id="key_1", description="A key")
        self.player.inventory = [key]

        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A locked door",
            state="locked"
        )
        stateful_item.add_state_description("locked", "A locked door")
        stateful_item.add_state_description("unlocked", "An unlocked door")
        stateful_item.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="unlocked",
            message="You unlock the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "unlock",
            "subject": "key",
            "subject_object": key,
            "instrument": "door",
            "instrument_object": stateful_item,
            "reversed_syntax": True
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "unlocked")

    async def test_handle_interaction_reversed_syntax_name_search_instrument(self):
        """Test reversed syntax with name-based search using instrument field."""
        key = Item(name="key", id="key_1", description="A key")
        self.player.inventory = [key]

        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A locked door",
            state="locked"
        )
        stateful_item.add_state_description("locked", "A locked door")
        stateful_item.add_state_description("unlocked", "An unlocked door")
        stateful_item.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="unlocked",
            message="You unlock the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "unlock",
            "subject": "key",
            "instrument": "door",
            "reversed_syntax": True
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "unlocked")

    async def test_handle_interaction_reversed_syntax_fallback_to_subject(self):
        """Test reversed syntax fallback to subject when instrument not found."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door",
            "instrument": "nothing",
            "reversed_syntax": True
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")

    async def test_handle_interaction_reversed_syntax_inventory_search(self):
        """Test reversed syntax with inventory search."""
        stateful_item = StatefulItem(
            name="box",
            id="box_1",
            description="A box",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed box")
        stateful_item.add_state_description("open", "An open box")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the box."
        )
        self.player.inventory = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "something",
            "instrument": "box",
            "reversed_syntax": True
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")


class InteractionNameSearchTest(unittest.IsolatedAsyncioTestCase):
    """Test name-based search for items."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

        self.current_room = Mock()
        self.current_room.room_id = "test_room"
        self.current_room.items = []
        self.current_room.get_items = Mock(return_value=[])
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_interaction_standard_syntax_inventory_search(self):
        """Test standard syntax with name-based search in inventory."""
        stateful_item = StatefulItem(
            name="box",
            id="box_1",
            description="A box",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed box")
        stateful_item.add_state_description("open", "An open box")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the box."
        )
        self.player.inventory = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "box"
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")

    async def test_handle_interaction_standard_syntax_room_search(self):
        """Test standard syntax with name-based search in room."""
        stateful_item = StatefulItem(
            name="door",
            id="door_1",
            description="A door",
            state="closed"
        )
        stateful_item.add_state_description("closed", "A closed door")
        stateful_item.add_state_description("open", "An open door")
        stateful_item.add_interaction(
            verb="open",
            from_state="closed",
            target_state="open",
            message="You open the door."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "open",
            "subject": "door"
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "open")

    async def test_handle_interaction_finds_secondary_item_by_name(self):
        """Test finding secondary item by name when primary item found."""
        key = Item(name="bronze key", id="key_1", description="A key")
        self.player.inventory = [key]

        stateful_item = StatefulItem(
            name="lock",
            id="lock_1",
            description="A lock",
            state="locked"
        )
        stateful_item.add_state_description("locked", "A locked lock")
        stateful_item.add_state_description("unlocked", "An unlocked lock")
        stateful_item.add_interaction(
            verb="unlock",
            from_state="locked",
            target_state="unlocked",
            required_instrument="key",
            message="You unlock the lock."
        )
        self.current_room.items = [stateful_item]
        self.current_room.get_items.return_value = [stateful_item]

        cmd = {
            "verb": "unlock",
            "subject": "lock",
            "instrument": "key"
        }

        result = await handle_interaction(cmd, self.player, self.game_state,
                                self.player_manager, self.online_sessions,
                                self.sio, self.utils)

        self.assertEqual(stateful_item.state, "unlocked")


class RegisterInteractionVerbsTest(unittest.TestCase):
    """Test register_interaction_verbs functionality."""

    def test_register_interaction_verbs_runs_without_error(self):
        """Test register_interaction_verbs runs without error."""
        # This function registers verbs as a side effect and returns None
        result = register_interaction_verbs()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
