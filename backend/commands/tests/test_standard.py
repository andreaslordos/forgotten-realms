"""
Comprehensive tests for standard commands module.

Tests cover:
- handle_look, handle_inventory, handle_exits
- handle_get, handle_drop
- handle_score, handle_help, handle_info
- handle_levels, handle_users, handle_quit
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.standard import (
    handle_look,
    handle_inventory,
    handle_exits,
    handle_get,
    handle_drop,
    handle_score,
    handle_help,
    handle_info,
    handle_levels,
    handle_users,
    handle_quit,
    handle_diagnostic,
)
from models.Item import Item
from models.Room import Room
from models.StatefulItem import StatefulItem


class HandleLookTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_look functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []
        self.player.visited = set()

        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        # Mock mob_manager attribute on utils
        self.utils.mob_manager = None

        self.current_room = Room(
            room_id="test_room",
            name="Test Room",
            description="A test room for testing.",
            exits={"north": "north_room", "south": "south_room"},
        )
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_look_returns_string(self):
        """Test look command returns a string description."""
        cmd = {"verb": "look"}

        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Just verify it returns a string (full integration test would be complex)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    async def test_handle_look_at_item_in_inventory(self):
        """Test looking at an item in player's inventory."""
        item = Item(name="bronze key", id="key_1", description="A shiny key")
        self.player.inventory = [item]

        cmd = {"verb": "look", "subject": "key", "subject_object": item}

        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("shiny key", result)

    async def test_handle_look_at_item_in_room(self):
        """Test looking at an item in the room."""
        item = Item(name="torch", id="torch_1", description="A burning torch")
        self.current_room.add_item(item)
        self.current_room.get_items = Mock(return_value=[item])

        cmd = {"verb": "look", "subject": "torch", "subject_object": item}

        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("torch", result.lower())

    async def test_handle_look_at_player(self):
        """Test looking at another player in the room."""
        other_player = Mock()
        other_player.name = "OtherPlayer"
        other_player.level = "Warrior"
        other_player.current_room = "test_room"

        cmd = {"verb": "look", "subject": "other", "subject_object": other_player}

        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("OtherPlayer", result)
        self.assertIn("Warrior", result)

    async def test_handle_look_search_by_name_in_inventory(self):
        """Test looking at item by name search in inventory."""
        item = Item(name="silver sword", id="sword_1", description="A gleaming blade")
        self.player.inventory = [item]

        cmd = {"verb": "look", "subject": "sword"}

        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("gleaming blade", result)

    async def test_handle_look_search_by_name_in_room(self):
        """Test looking at item by name search in room."""
        item = Item(name="wooden barrel", id="barrel_1", description="A sturdy barrel")
        self.current_room.add_item(item)
        self.current_room.get_items = Mock(return_value=[item])

        cmd = {"verb": "look", "subject": "barrel"}

        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("barrel", result.lower())

    async def test_handle_look_search_for_player_by_name(self):
        """Test looking at another player by name search."""
        other_player = Mock()
        other_player.name = "Bob"
        other_player.level = "Mage"
        other_player.current_room = "test_room"

        self.online_sessions["session1"] = {"player": other_player}

        cmd = {"verb": "look", "subject": "bob"}

        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Bob", result)
        self.assertIn("Mage", result)

    async def test_handle_look_item_not_found(self):
        """Test looking at non-existent item."""
        cmd = {"verb": "look", "subject": "nonexistent"}

        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't see", result.lower())


class HandleLookInteractionTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_look with custom interactions."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.inventory = []
        self.player.visited = set()

        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.mob_manager = None

        self.current_room = Room(
            room_id="test_room",
            name="Test Room",
            description="A test room.",
            exits={"north": "north_room"},
        )
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_look_shows_examine_interaction_for_room_item(self):
        """Test look shows custom examine interaction message for item in room."""
        # Arrange
        pedestal = StatefulItem(
            name="pedestal",
            id="pedestal_1",
            description="An ornate stone pedestal.",
            takeable=False,
        )
        pedestal.add_interaction(
            verb="examine",
            message="Three dials are set into the pedestal's base.",
        )
        self.current_room.add_item(pedestal)
        self.current_room.get_items = Mock(return_value=[pedestal])

        cmd = {"verb": "examine", "subject": "pedestal", "subject_object": pedestal}

        # Act
        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert - should show interaction message, not default description
        self.assertIn("Three dials", result)
        self.assertNotIn("ornate stone pedestal", result)

    async def test_handle_look_shows_look_interaction_for_room_item(self):
        """Test look shows custom look interaction message for item in room."""
        # Arrange
        statue = StatefulItem(
            name="statue",
            id="statue_1",
            description="A stone statue.",
            takeable=False,
        )
        statue.add_interaction(
            verb="look",
            message="The statue's eyes seem to follow you.",
        )
        self.current_room.add_item(statue)
        self.current_room.get_items = Mock(return_value=[statue])

        cmd = {"verb": "look", "subject": "statue", "subject_object": statue}

        # Act
        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert
        self.assertIn("eyes seem to follow you", result)
        self.assertNotIn("stone statue", result)

    async def test_handle_look_shows_examine_interaction_for_inventory_item(self):
        """Test look shows custom examine interaction for item in inventory."""
        # Arrange
        scroll = StatefulItem(
            name="scroll",
            id="scroll_1",
            description="A rolled up scroll.",
        )
        scroll.add_interaction(
            verb="examine",
            message="Ancient runes cover the scroll's surface.",
        )
        self.player.inventory = [scroll]

        cmd = {"verb": "examine", "subject": "scroll", "subject_object": scroll}

        # Act
        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert
        self.assertIn("Ancient runes", result)
        self.assertNotIn("rolled up scroll", result)

    async def test_handle_look_falls_back_to_description_without_interaction(self):
        """Test look falls back to description when no interaction defined."""
        # Arrange
        item = StatefulItem(
            name="rock",
            id="rock_1",
            description="Just a plain rock.",
            takeable=False,
        )
        # No interaction added
        self.current_room.add_item(item)
        self.current_room.get_items = Mock(return_value=[item])

        cmd = {"verb": "look", "subject": "rock", "subject_object": item}

        # Act
        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert - should show default description
        self.assertIn("plain rock", result)

    async def test_handle_look_respects_from_state_on_interaction(self):
        """Test look respects from_state condition on interactions."""
        # Arrange
        lever = StatefulItem(
            name="lever",
            id="lever_1",
            description="A rusty lever.",
            state="down",
        )
        lever.add_interaction(
            verb="examine",
            from_state="up",
            message="The lever is pulled up, revealing a hidden mechanism.",
        )
        lever.add_interaction(
            verb="examine",
            from_state="down",
            message="The lever points downward.",
        )
        self.current_room.add_item(lever)
        self.current_room.get_items = Mock(return_value=[lever])

        cmd = {"verb": "examine", "subject": "lever", "subject_object": lever}

        # Act
        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert - should show "down" state message since lever is in "down" state
        self.assertIn("points downward", result)
        self.assertNotIn("hidden mechanism", result)

    async def test_handle_look_name_search_shows_interaction(self):
        """Test look by name search also checks for custom interactions."""
        # Arrange
        altar = StatefulItem(
            name="stone altar",
            id="altar_1",
            description="A weathered altar.",
            takeable=False,
        )
        altar.add_interaction(
            verb="examine",
            message="Blood stains mark the altar's surface.",
        )
        self.current_room.add_item(altar)
        self.current_room.get_items = Mock(return_value=[altar])

        # No subject_object, just subject string - simulates name search
        cmd = {"verb": "examine", "subject": "altar"}

        # Act
        result = await handle_look(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert
        self.assertIn("Blood stains", result)


class HandleInventoryTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_inventory functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

    async def test_handle_inventory_shows_empty_inventory(self):
        """Test inventory command with no items."""
        cmd = {"verb": "inventory"}

        result = await handle_inventory(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("aren't carrying anything", result.lower())

    async def test_handle_inventory_lists_items(self):
        """Test inventory command lists all carried items."""
        item1 = Item(name="bronze key", id="key_1", description="A key")
        item2 = Item(name="torch", id="torch_1", description="A torch")
        self.player.inventory = [item1, item2]

        cmd = {"verb": "inventory"}

        result = await handle_inventory(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("bronze key", result)
        self.assertIn("torch", result)


class HandleExitsTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_exits functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.current_room = "test_room"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

        self.current_room = Room(
            room_id="test_room",
            name="Test Room",
            description="A test room",
            exits={"north": "north_room", "east": "east_room"},
        )
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_exits_lists_all_exits(self):
        """Test exits command lists all available exits."""
        cmd = {"verb": "exits"}

        result = await handle_exits(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("north", result)
        self.assertIn("east", result)

    async def test_handle_exits_no_exits(self):
        """Test exits command when room has no exits."""
        self.current_room.exits = {}

        cmd = {"verb": "exits"}

        result = await handle_exits(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("No exits", result)

    async def test_handle_exits_dark_room(self):
        """Test exits command when room is dark."""
        self.current_room.is_dark = True
        self.current_room.exits = {"north": "north_room", "east": "east_room"}

        cmd = {"verb": "exits"}

        result = await handle_exits(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("It's too dark to see any exits.", result)

    async def test_handle_exits_dark_room_with_light_source(self):
        """Test exits command shows exits when player has light in dark room."""
        self.current_room.is_dark = True
        self.current_room.exits = {"north": "north_room"}

        # Set up player with light source in online_sessions
        self.player.has_light_source = Mock(return_value=True)
        self.online_sessions["test_sid"] = {"player": self.player}

        # Mock the destination room
        north_room = Mock()
        north_room.name = "North Room"
        self.game_state.get_room.side_effect = lambda room_id: (
            self.current_room if room_id == "test_room" else north_room
        )

        cmd = {"verb": "exits"}

        result = await handle_exits(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should show exits since player has light
        self.assertIn("north", result)
        self.assertIn("North Room", result)
        self.assertNotIn("too dark", result)

    async def test_handle_exits_shows_swamp_for_outdoor_room(self):
        """Test exits shows swamp as virtual exit for outdoor rooms."""
        self.current_room.is_outdoor = True
        self.current_room.swamp_direction = "south"
        self.current_room.exits = {"south": "south_room", "north": "north_room"}

        # Mock destination rooms
        south_room = Mock()
        south_room.name = "South Room"
        north_room = Mock()
        north_room.name = "North Room"
        self.game_state.get_room.side_effect = lambda room_id: {
            "test_room": self.current_room,
            "south_room": south_room,
            "north_room": north_room,
        }.get(room_id)

        cmd = {"verb": "exits"}

        result = await handle_exits(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("swamp", result)
        self.assertIn("South Room", result)

    async def test_handle_exits_no_swamp_for_indoor_room(self):
        """Test exits does not show swamp for indoor rooms."""
        self.current_room.is_outdoor = False
        self.current_room.exits = {"north": "north_room"}

        north_room = Mock()
        north_room.name = "North Room"
        self.game_state.get_room.side_effect = lambda room_id: (
            self.current_room if room_id == "test_room" else north_room
        )

        cmd = {"verb": "exits"}

        result = await handle_exits(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertNotIn("swamp", result)

    async def test_handle_exits_no_swamp_at_lake(self):
        """Test exits does not show swamp when already at lake."""
        lake_room = Room(
            room_id="lake",
            name="Lake Zarovich",
            description="A dark lake",
            exits={"south": "camp"},
            is_outdoor=True,
        )
        self.player.current_room = "lake"
        self.game_state.get_room.return_value = lake_room

        cmd = {"verb": "exits"}

        result = await handle_exits(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertNotIn("swamp", result)


class HandleGetTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_get functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.current_room = "test_room"
        self.player.inventory = []
        self.player.add_item = Mock(return_value=(True, "Item taken."))

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

        self.current_room = Room(
            room_id="test_room", name="Test Room", description="A test room"
        )
        self.current_room.get_items = Mock(return_value=[])
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_get_picks_up_single_item(self):
        """Test get command picks up single item."""
        item = Item(name="bronze key", id="key_1", description="A key", takeable=True)
        self.current_room.add_item(item)
        self.current_room.get_items.return_value = [item]

        cmd = {"verb": "get", "subject": "key", "subject_object": item}

        await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.player.add_item.assert_called_once_with(item)

    async def test_handle_get_all_picks_up_all_takeable_items(self):
        """Test 'get all' picks up all takeable items."""
        item1 = Item(name="key", id="key_1", description="A key", takeable=True)
        item2 = Item(name="torch", id="torch_1", description="A torch", takeable=True)
        item3 = Item(name="tree", id="tree_1", description="A tree", takeable=False)
        self.current_room.add_item(item1)
        self.current_room.add_item(item2)
        self.current_room.add_item(item3)
        self.current_room.get_items.return_value = [item1, item2, item3]

        cmd = {"verb": "get", "subject": "all"}

        await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should pick up item1 and item2, but not item3
        self.assertEqual(self.player.add_item.call_count, 2)

    async def test_handle_get_missing_subject(self):
        """Test get command without specifying an item."""
        cmd = {"verb": "get"}

        result = await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Specify", result)

    async def test_handle_get_from_container(self):
        """Test get from container redirects to handle_get_from."""
        from unittest.mock import patch

        cmd = {
            "verb": "get",
            "subject": "key",
            "instrument": "chest",
            "preposition": "from",
            "from_container": True,
        }

        with patch(
            "commands.container.handle_get_from", new_callable=AsyncMock
        ) as mock_get_from:
            mock_get_from.return_value = "Got item from chest"

            await handle_get(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            mock_get_from.assert_called_once()

    async def test_handle_get_treasure(self):
        """Test 'get treasure' picks up only valuable items."""
        item1 = Item(
            name="gold coin", id="coin_1", description="A coin", takeable=True, value=10
        )
        item2 = Item(
            name="torch", id="torch_1", description="A torch", takeable=True, value=0
        )
        item3 = Item(
            name="gem", id="gem_1", description="A gem", takeable=True, value=50
        )
        self.current_room.get_items.return_value = [item1, item2, item3]

        cmd = {"verb": "get", "subject": "treasure"}

        await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should pick up item1 and item3, but not item2
        self.assertEqual(self.player.add_item.call_count, 2)

    async def test_handle_get_all_with_hidden_items(self):
        """Test 'get all' removes items from hidden_items list."""
        item = Item(name="key", id="hidden_key_1", description="A key", takeable=True)
        self.current_room.hidden_items = {"hidden_key_1"}
        self.current_room.remove_hidden_item = Mock()
        self.current_room.get_items.return_value = [item]

        cmd = {"verb": "get", "subject": "all"}

        await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.current_room.remove_hidden_item.assert_called_once_with("hidden_key_1")

    async def test_handle_get_non_takeable_item(self):
        """Test getting a non-takeable item."""
        item = Item(name="tree", id="tree_1", description="A tree", takeable=False)
        self.current_room.get_items.return_value = [item]

        cmd = {"verb": "get", "subject": "tree", "subject_object": item}

        result = await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("can't take", result.lower())

    async def test_handle_get_item_bound_to_inventory(self):
        """Test getting item when bound object is already in inventory."""
        item = Item(name="key", id="key_1", description="A key", takeable=True)
        self.player.inventory = [item]

        # Parser bound to inventory item, but there's another in room
        room_item = Item(name="key", id="key_2", description="A key", takeable=True)
        self.current_room.get_items.return_value = [room_item]

        cmd = {"verb": "get", "subject": "key", "subject_object": item}

        await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should pick up room_item since inventory item is ignored
        self.player.add_item.assert_called_once()

    async def test_handle_get_item_by_name_search(self):
        """Test getting item by exact name match."""
        item = Item(name="key", id="key_1", description="A key", takeable=True)
        self.current_room.get_items.return_value = [item]

        cmd = {"verb": "get", "subject": "key"}

        await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.player.add_item.assert_called_once_with(item)

    async def test_handle_get_item_not_found(self):
        """Test getting non-existent item."""
        self.current_room.get_items.return_value = []

        cmd = {"verb": "get", "subject": "nonexistent"}

        result = await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't see", result.lower())

    async def test_handle_get_specific_item_with_hidden(self):
        """Test getting specific item removes from hidden_items."""
        item = Item(name="secret", id="secret_1", description="Secret", takeable=True)
        self.current_room.hidden_items = {"secret_1"}
        self.current_room.remove_hidden_item = Mock()
        self.current_room.get_items.return_value = [item]

        cmd = {"verb": "get", "subject": "secret", "subject_object": item}

        await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.current_room.remove_hidden_item.assert_called_once_with("secret_1")

    async def test_handle_get_all_inventory_full(self):
        """Test 'get all' returns capacity error when inventory is full."""
        item = Item(name="key", id="key_1", description="A key", takeable=True)
        self.current_room.add_item(item)
        self.current_room.get_items.return_value = [item]
        self.player.add_item = Mock(
            return_value=(False, "You are carrying too many items.")
        )

        cmd = {"verb": "get", "subject": "all"}

        result = await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "You are carrying too many items.")

    async def test_handle_get_all_item_too_heavy(self):
        """Test 'get all' returns weight error when item is too heavy."""
        item = Item(name="boulder", id="boulder_1", description="Heavy", takeable=True)
        self.current_room.add_item(item)
        self.current_room.get_items.return_value = [item]
        self.player.add_item = Mock(
            return_value=(False, "This item is too heavy to carry.")
        )

        cmd = {"verb": "get", "subject": "all"}

        result = await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "This item is too heavy to carry.")

    async def test_handle_get_all_empty_room(self):
        """Test 'get all' returns 'Nothing to take' when room is empty."""
        self.current_room.get_items.return_value = []

        cmd = {"verb": "get", "subject": "all"}

        result = await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "Nothing to take.")

    async def test_handle_get_treasure_inventory_full(self):
        """Test 'get treasure' returns capacity error when inventory is full."""
        item = Item(
            name="gold coin", id="coin_1", description="A coin", takeable=True, value=10
        )
        self.current_room.add_item(item)
        self.current_room.get_items.return_value = [item]
        self.player.add_item = Mock(
            return_value=(False, "You are carrying too many items.")
        )

        cmd = {"verb": "get", "subject": "treasure"}

        result = await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "You are carrying too many items.")

    async def test_handle_get_treasure_no_treasure(self):
        """Test 'get treasure' returns message when no treasure in room."""
        item = Item(
            name="stick", id="stick_1", description="A stick", takeable=True, value=0
        )
        self.current_room.add_item(item)
        self.current_room.get_items.return_value = [item]

        cmd = {"verb": "get", "subject": "treasure"}

        result = await handle_get(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "No treasure to take.")


class HandleDropTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_drop functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.current_room = "test_room"
        self.player.inventory = []
        self.player.remove_item = Mock()

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

        self.current_room = Room(
            room_id="test_room", name="Test Room", description="A test room"
        )
        self.game_state.get_room.return_value = self.current_room

    async def test_handle_drop_drops_single_item(self):
        """Test drop command drops single item."""
        item = Item(name="bronze key", id="key_1", description="A key")
        self.player.inventory = [item]

        cmd = {"verb": "drop", "subject": "key", "subject_object": item}

        await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.player.remove_item.assert_called_once_with(item)
        self.assertIn(item, self.current_room.items)

    async def test_handle_drop_all_drops_all_items(self):
        """Test 'drop all' drops all items in inventory."""
        item1 = Item(name="key", id="key_1", description="A key")
        item2 = Item(name="torch", id="torch_1", description="A torch")
        self.player.inventory = [item1, item2]

        cmd = {"verb": "drop", "subject": "all"}

        await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(self.player.remove_item.call_count, 2)

    async def test_handle_drop_missing_subject(self):
        """Test drop command without specifying an item."""
        cmd = {"verb": "drop"}

        result = await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Specify", result)

    async def test_handle_drop_treasure(self):
        """Test 'drop treasure' drops only valuable items."""
        item1 = Item(name="gold coin", id="coin_1", description="A coin", value=10)
        item2 = Item(name="torch", id="torch_1", description="A torch", value=0)
        item3 = Item(name="gem", id="gem_1", description="A gem", value=50)
        self.player.inventory = [item1, item2, item3]

        cmd = {"verb": "drop", "subject": "treasure"}

        await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should drop item1 and item3, but not item2
        self.assertEqual(self.player.remove_item.call_count, 2)

    async def test_handle_drop_treasure_when_none(self):
        """Test 'drop treasure' when player has no treasure."""
        item = Item(name="torch", id="torch_1", description="A torch", value=0)
        self.player.inventory = [item]

        cmd = {"verb": "drop", "subject": "treasure"}

        result = await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("no treasure", result.lower())

    async def test_handle_drop_all_when_empty(self):
        """Test 'drop all' when inventory is empty."""
        self.player.inventory = []

        cmd = {"verb": "drop", "subject": "all"}

        result = await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("aren't carrying", result.lower())

    async def test_handle_drop_without_subject_object(self):
        """Test drop without subject_object shows error."""
        item = Item(name="key", id="key_1", description="A key")
        self.player.inventory = [item]

        cmd = {"verb": "drop", "subject": "sword"}

        result = await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't have", result.lower())

    async def test_handle_drop_without_subject_object_empty_inventory(self):
        """Test drop without subject_object when inventory is empty."""
        self.player.inventory = []

        cmd = {"verb": "drop", "subject": "key"}

        result = await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("aren't carrying", result.lower())

    async def test_handle_drop_item_not_in_inventory(self):
        """Test dropping item not in inventory."""
        item = Item(name="key", id="key_1", description="A key")
        # Item not in inventory

        cmd = {"verb": "drop", "subject": "key", "subject_object": item}

        result = await handle_drop(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't have", result.lower())


class HandleScoreTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_score functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.points = 500
        self.player.level = "Novice"
        self.player.carrying_capacity_num = 20
        self.player.stamina = 100
        self.player.max_stamina = 100
        self.player.strength = 10
        self.player.dexterity = 10
        self.player.inventory = []

        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

    async def test_handle_score_shows_player_stats(self):
        """Test score command shows player statistics."""
        cmd = {"verb": "score"}

        result = await handle_score(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("500", result)
        self.assertIn("Novice", result)


class HandleHelpTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_help functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

    async def test_handle_help_shows_help_text(self):
        """Test help command shows help text."""
        cmd = {"verb": "help"}

        result = await handle_help(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("command", result.lower())

    async def test_handle_help_specific_command(self):
        """Test help for a specific command."""
        from commands.registry import command_registry
        from unittest.mock import patch

        cmd = {"verb": "help", "subject": "look"}

        with patch.object(
            command_registry, "get_help", return_value="Help for look command"
        ):
            await handle_help(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            command_registry.get_help.assert_called_once_with("look")


class HandleInfoTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_info functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

    async def test_handle_info_shows_game_info(self):
        """Test info command shows game information."""
        cmd = {"verb": "info"}

        result = await handle_info(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class HandleLevelsTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_levels functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

    async def test_handle_levels_shows_level_requirements(self):
        """Test levels command shows level requirements."""
        cmd = {"verb": "levels"}

        result = await handle_levels(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertTrue(any(word in result.lower() for word in ["level", "point"]))


class HandleUsersTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_users functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = AsyncMock()
        self.utils = Mock()

    async def test_handle_users_lists_online_players(self):
        """Test users command lists online players."""
        player1 = Mock()
        player1.name = "Player1"
        player1.level = "Novice"
        player2 = Mock()
        player2.name = "Player2"
        player2.level = "Acolyte"

        online_sessions = {
            "session1": {"player": player1},
            "session2": {"player": player2},
        }

        cmd = {"verb": "users"}

        result = await handle_users(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Player1", result)
        self.assertIn("Player2", result)

    async def test_handle_users_empty_sessions(self):
        """Test users command when no sessions (shouldn't happen)."""
        online_sessions = {}

        cmd = {"verb": "users"}

        result = await handle_users(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("How is this possible", result)


class HandleQuitTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_quit functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

    async def test_handle_quit_returns_quit_string(self):
        """Test quit command returns 'quit' string."""
        cmd = {"verb": "quit"}

        result = await handle_quit(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "quit")


class HandleDiagnosticTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_diagnostic functionality."""

    def setUp(self):
        """Set up mocks for tests."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "test_room"
        self.player.points = 500
        self.player.level = "Novice"
        self.player.inventory = []
        self.player.strength = 10
        self.player.dexterity = 10
        self.player.stamina = 100
        self.player.max_stamina = 100

        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()

    async def test_handle_diagnostic_shows_stats(self):
        """Test diagnostic command shows game statistics."""
        room = Room(room_id="test_room", name="Test", description="Test")
        self.game_state.get_room.return_value = room
        self.utils.mob_manager = None

        cmd = {"verb": "diagnostic"}

        result = await handle_diagnostic(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    async def test_handle_diagnostic_with_stateful_items(self):
        """Test diagnostic with stateful items in room."""
        from models.StatefulItem import StatefulItem

        room = Room(room_id="test_room", name="Test", description="Test")
        stateful_item = StatefulItem(
            name="Door", id="door_1", description="A door", state="closed"
        )
        stateful_item.add_interaction("open", target_state="open")
        room.add_item(stateful_item)
        self.game_state.get_room.return_value = room

        cmd = {"verb": "diagnostic"}

        result = await handle_diagnostic(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("State:", result)
        self.assertIn("closed", result)
        self.assertIn("Has interactions:", result)

    async def test_handle_diagnostic_with_container_items(self):
        """Test diagnostic with container items in inventory."""
        from models.ContainerItem import ContainerItem

        container = ContainerItem(
            name="chest", id="chest_1", description="A chest", state="closed"
        )
        container.add_interaction("open", target_state="open")
        container.add_interaction("close", target_state="closed")
        self.player.inventory = [container]

        room = Room(room_id="test_room", name="Test", description="Test")
        self.game_state.get_room.return_value = room

        cmd = {"verb": "diagnostic"}

        result = await handle_diagnostic(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Is container:", result)
        self.assertIn("Has interactions:", result)
        self.assertIn("open", result)
        self.assertIn("close", result)

    async def test_handle_diagnostic_with_non_list_interactions(self):
        """Test diagnostic with malformed interactions (not a list)."""
        from models.StatefulItem import StatefulItem

        room = Room(room_id="test_room", name="Test", description="Test")
        item = StatefulItem(
            name="Item", id="item_1", description="An item", state="default"
        )
        # Manually set malformed interactions
        item.interactions = {"verb": "not_a_list"}
        room.add_item(item)
        self.game_state.get_room.return_value = room

        cmd = {"verb": "diagnostic"}

        result = await handle_diagnostic(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Is a list: NO", result)

    async def test_handle_diagnostic_with_non_dict_interaction(self):
        """Test diagnostic with interaction that is not a dict."""
        from models.StatefulItem import StatefulItem

        room = Room(room_id="test_room", name="Test", description="Test")
        item = StatefulItem(
            name="Item", id="item_1", description="An item", state="default"
        )
        # Manually set malformed interaction within list
        item.interactions = {"verb": ["not_a_dict"]}
        room.add_item(item)
        self.game_state.get_room.return_value = room

        cmd = {"verb": "diagnostic"}

        result = await handle_diagnostic(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Is a dictionary: NO", result)


if __name__ == "__main__":
    unittest.main()
