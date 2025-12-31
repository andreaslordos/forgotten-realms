"""
Comprehensive tests for container commands.

Tests cover:
- Put command (single item, all items, treasure)
- Get from command (single item, all items, treasure)
- Open command
- Close command
- Empty command
- Container capacity and weight limits
- Nested container prevention
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.container import (
    handle_put,
    handle_get_from,
    handle_open,
    handle_close,
    handle_empty,
)
from models.Player import Player
from models.Item import Item
from models.ContainerItem import ContainerItem
from models.Room import Room
from managers.game_state import GameState


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """Base class for async tests."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Player("TestPlayer")
        self.player.current_room = "test_room"

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
        self.online_sessions = {}

        # Create test items
        self.item1 = Item("Gem", "gem_1", "A shiny gem", weight=1, value=50)
        self.item2 = Item("Coin", "coin_1", "A gold coin", weight=0.5, value=25)
        self.item3 = Item("Rock", "rock_1", "A plain rock", weight=5, value=0)

        # Create test container
        self.bag = ContainerItem(
            "Bag",
            "bag_1",
            "A leather bag",
            weight=2,
            value=10,
            capacity_weight=20,
            capacity_limit=5,
        )
        self.bag.set_state("open")


class PutCommandTest(AsyncTestCase):
    """Test put command functionality."""

    async def test_put_item_in_container(self):
        """Test putting a single item into a container."""
        self.player.add_item(self.bag)
        self.player.add_item(self.item1)

        cmd = {"verb": "put", "subject": "gem", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem now inside", result)
        self.assertIn(self.item1, self.bag.items)
        self.assertNotIn(self.item1, self.player.inventory)

    async def test_put_requires_item(self):
        """Test put without item returns error."""
        cmd = {"verb": "put"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "What do you want to put?")

    async def test_put_requires_container(self):
        """Test put without container returns error."""
        self.player.add_item(self.item1)

        cmd = {"verb": "put", "subject": "gem"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("only insert items into objects", result)

    async def test_put_closed_container_fails(self):
        """Test putting item into closed container fails."""
        self.bag.set_state("closed")
        self.player.add_item(self.bag)
        self.player.add_item(self.item1)

        cmd = {"verb": "put", "subject": "gem", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("closed", result.lower())
        self.assertNotIn(self.item1, self.bag.items)

    async def test_put_container_in_container_fails(self):
        """Test nested containers are prevented."""
        self.player.add_item(self.bag)
        small_bag = ContainerItem("Small Bag", "small_bag", "A tiny bag")
        self.player.add_item(small_bag)

        cmd = {"verb": "put", "subject": "small", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Infinite recursion", result)

    async def test_put_all_items(self):
        """Test putting all items into container."""
        self.player.add_item(self.bag)
        self.player.add_item(self.item1)
        self.player.add_item(self.item2)

        cmd = {"verb": "put", "subject": "all", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem now inside", result)
        self.assertIn("Coin now inside", result)
        self.assertEqual(len(self.bag.items), 2)

    async def test_put_treasure_items(self):
        """Test putting treasure (valuable items) into container."""
        self.player.add_item(self.bag)
        self.player.add_item(self.item1)  # value 50
        self.player.add_item(self.item2)  # value 25
        self.player.add_item(self.item3)  # value 0 (not treasure)

        cmd = {"verb": "put", "subject": "treasure", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem", result)
        self.assertIn("Coin", result)
        self.assertEqual(len(self.bag.items), 2)
        self.assertIn(self.item3, self.player.inventory)  # Rock not moved

    async def test_put_respects_capacity_limit(self):
        """Test container capacity limit is enforced."""
        self.bag.capacity_limit = 1  # Only 1 item allowed
        self.player.add_item(self.bag)
        self.player.add_item(self.item1)
        self.player.add_item(self.item2)

        # Put first item
        cmd1 = {"verb": "put", "subject": "gem", "instrument": "bag"}
        await handle_put(
            cmd1,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Try to put second item
        cmd2 = {"verb": "put", "subject": "coin", "instrument": "bag"}
        result = await handle_put(
            cmd2,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("full", result.lower())

    async def test_put_respects_weight_limit(self):
        """Test container weight limit is enforced."""
        self.bag.capacity_weight = 2  # Only 2 weight units allowed
        heavy_item = Item("Boulder", "boulder_1", "A heavy rock", weight=10, value=0)

        self.player.add_item(self.bag)
        self.player.add_item(heavy_item)

        cmd = {"verb": "put", "subject": "boulder", "instrument": "bag"}
        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("heavy", result.lower())


class GetFromCommandTest(AsyncTestCase):
    """Test get from command functionality."""

    async def test_get_item_from_container(self):
        """Test getting a single item from a container."""
        self.bag.add_item(self.item1)
        self.player.add_item(self.bag)

        cmd = {"verb": "get", "subject": "gem", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("removed from", result)
        self.assertIn(self.item1, self.player.inventory)
        self.assertNotIn(self.item1, self.bag.items)

    async def test_get_requires_item(self):
        """Test get without item returns error."""
        cmd = {"verb": "get"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "What do you want to get?")

    async def test_get_requires_container(self):
        """Test get without container returns error."""
        cmd = {"verb": "get", "subject": "gem"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Where do you want to get", result)

    async def test_get_from_closed_container_fails(self):
        """Test getting from closed container fails."""
        self.bag.add_item(self.item1)
        self.bag.set_state("closed")
        self.player.add_item(self.bag)

        cmd = {"verb": "get", "subject": "gem", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("closed", result.lower())

    async def test_get_all_items(self):
        """Test getting all items from container."""
        self.bag.add_item(self.item1)
        self.bag.add_item(self.item2)
        self.player.add_item(self.bag)

        cmd = {"verb": "get", "subject": "all", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem removed", result)
        self.assertIn("Coin removed", result)
        self.assertEqual(len(self.bag.items), 0)

    async def test_get_treasure_items(self):
        """Test getting treasure from container."""
        self.bag.add_item(self.item1)  # value 50
        self.bag.add_item(self.item2)  # value 25
        self.bag.add_item(self.item3)  # value 0 (not treasure)
        self.player.add_item(self.bag)

        cmd = {"verb": "get", "subject": "treasure", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem", result)
        self.assertIn("Coin", result)
        self.assertEqual(len(self.bag.items), 1)  # Rock remains
        self.assertIn(self.item3, self.bag.items)

    async def test_get_from_empty_container(self):
        """Test getting from empty container returns error."""
        self.player.add_item(self.bag)

        cmd = {"verb": "get", "subject": "all", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("empty", result.lower())

    async def test_get_nonexistent_item(self):
        """Test getting item that's not in container."""
        self.bag.add_item(self.item1)
        self.player.add_item(self.bag)

        cmd = {"verb": "get", "subject": "sword", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("no 'sword'", result)


class OpenCloseCommandTest(AsyncTestCase):
    """Test open and close commands."""

    async def test_open_container_in_inventory(self):
        """Test opening a container in inventory."""
        self.bag.set_state("closed")
        self.player.add_item(self.bag)

        cmd = {"verb": "open", "subject": "bag"}

        result = await handle_open(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("open", result)
        self.assertEqual(self.bag.state, "open")

    async def test_open_container_in_room(self):
        """Test opening a container in the room."""
        self.bag.set_state("closed")
        self.room.add_item(self.bag)

        cmd = {"verb": "open", "subject": "bag"}

        result = await handle_open(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("open", result)
        self.assertEqual(self.bag.state, "open")

    async def test_open_already_open_container(self):
        """Test opening already open container."""
        self.bag.set_state("open")
        self.player.add_item(self.bag)

        cmd = {"verb": "open", "subject": "bag"}

        result = await handle_open(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("already open", result)

    async def test_open_requires_subject(self):
        """Test open without subject returns error."""
        cmd = {"verb": "open"}

        result = await handle_open(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "What do you want to open?")

    async def test_close_container(self):
        """Test closing an open container."""
        self.bag.set_state("open")
        self.player.add_item(self.bag)

        cmd = {"verb": "close", "subject": "bag"}

        result = await handle_close(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("close", result)
        self.assertEqual(self.bag.state, "closed")

    async def test_close_already_closed_container(self):
        """Test closing already closed container."""
        self.bag.set_state("closed")
        self.player.add_item(self.bag)

        cmd = {"verb": "close", "subject": "bag"}

        result = await handle_close(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("already closed", result)

    async def test_close_requires_subject(self):
        """Test close without subject returns error."""
        cmd = {"verb": "close"}

        result = await handle_close(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "What do you want to close?")


class EmptyCommandTest(AsyncTestCase):
    """Test empty command functionality."""

    async def test_empty_container(self):
        """Test emptying a container drops items to room."""
        self.bag.add_item(self.item1)
        self.bag.add_item(self.item2)
        self.player.add_item(self.bag)

        cmd = {"verb": "empty", "subject": "bag"}

        result = await handle_empty(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem dropped", result)
        self.assertIn("Coin dropped", result)
        self.assertEqual(len(self.bag.items), 0)
        self.assertIn(self.item1, self.room.items)
        self.assertIn(self.item2, self.room.items)

    async def test_empty_already_empty_container(self):
        """Test emptying an already empty container."""
        self.player.add_item(self.bag)

        cmd = {"verb": "empty", "subject": "bag"}

        result = await handle_empty(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("already empty", result)

    async def test_empty_opens_closed_container(self):
        """Test empty automatically opens closed container."""
        self.bag.add_item(self.item1)
        self.bag.set_state("closed")
        self.player.add_item(self.bag)

        cmd = {"verb": "empty", "subject": "bag"}

        result = await handle_empty(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("dropped", result)
        self.assertEqual(self.bag.state, "open")
        self.assertEqual(len(self.bag.items), 0)

    async def test_empty_requires_subject(self):
        """Test empty without subject returns error."""
        cmd = {"verb": "empty"}

        result = await handle_empty(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("What container", result)

    async def test_empty_nonexistent_container(self):
        """Test emptying container player doesn't have."""
        cmd = {"verb": "empty", "subject": "chest"}

        result = await handle_empty(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't see", result)


class ContainerObjectBindingTest(AsyncTestCase):
    """Test container commands with bound objects."""

    async def test_put_with_bound_objects(self):
        """Test put command with pre-bound objects."""
        self.player.add_item(self.bag)
        self.player.add_item(self.item1)

        cmd = {
            "verb": "put",
            "subject": "gem",
            "subject_object": self.item1,
            "instrument": "bag",
            "instrument_object": self.bag,
        }

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("now inside", result)
        self.assertIn(self.item1, self.bag.items)

    async def test_get_with_bound_objects(self):
        """Test get command with pre-bound objects."""
        self.bag.add_item(self.item1)
        self.player.add_item(self.bag)

        cmd = {
            "verb": "get",
            "subject": "gem",
            "subject_object": self.item1,
            "instrument": "bag",
            "instrument_object": self.bag,
        }

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("removed from", result)
        self.assertIn(self.item1, self.player.inventory)

    async def test_open_with_bound_object(self):
        """Test open command with pre-bound object."""
        self.bag.set_state("closed")
        self.player.add_item(self.bag)

        cmd = {"verb": "open", "subject": "bag", "subject_object": self.bag}

        result = await handle_open(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("open", result)
        self.assertEqual(self.bag.state, "open")


class RoomContainerTest(AsyncTestCase):
    """Test container operations with containers in the room (not in inventory)."""

    async def test_put_item_in_room_container(self):
        """Test putting an item into a container that's in the room."""
        # Container is in room, not inventory
        self.room.add_item(self.bag)
        self.player.add_item(self.item1)

        cmd = {"verb": "put", "subject": "gem", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem now inside", result)
        self.assertIn(self.item1, self.bag.items)
        self.assertNotIn(self.item1, self.player.inventory)

    async def test_put_all_in_room_container(self):
        """Test putting all items into a room container."""
        self.room.add_item(self.bag)
        self.player.add_item(self.item1)
        self.player.add_item(self.item2)

        cmd = {"verb": "put", "subject": "all", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem now inside", result)
        self.assertIn("Coin now inside", result)
        self.assertEqual(len(self.bag.items), 2)

    async def test_put_treasure_in_room_container(self):
        """Test putting treasure into a room container."""
        self.room.add_item(self.bag)
        self.player.add_item(self.item1)  # value 50
        self.player.add_item(self.item3)  # value 0 (not treasure)

        cmd = {"verb": "put", "subject": "treasure", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem", result)
        self.assertIn(self.item1, self.bag.items)
        self.assertIn(self.item3, self.player.inventory)  # Rock not moved

    async def test_put_closed_room_container_fails(self):
        """Test putting item into closed room container fails."""
        self.bag.set_state("closed")
        self.room.add_item(self.bag)
        self.player.add_item(self.item1)

        cmd = {"verb": "put", "subject": "gem", "instrument": "bag"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("closed", result.lower())
        self.assertNotIn(self.item1, self.bag.items)

    async def test_put_no_container_found(self):
        """Test put when container doesn't exist anywhere."""
        self.player.add_item(self.item1)

        cmd = {"verb": "put", "subject": "gem", "instrument": "chest"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Now falls back to interaction system, which returns this message
        # when no interactive item is found
        self.assertIn("can't place", result)

    async def test_get_item_from_room_container(self):
        """Test getting an item from a container in the room."""
        self.bag.add_item(self.item1)
        self.room.add_item(self.bag)

        cmd = {"verb": "get", "subject": "gem", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("removed from", result)
        self.assertIn(self.item1, self.player.inventory)
        self.assertNotIn(self.item1, self.bag.items)

    async def test_get_all_from_room_container(self):
        """Test getting all items from a room container."""
        self.bag.add_item(self.item1)
        self.bag.add_item(self.item2)
        self.room.add_item(self.bag)

        cmd = {"verb": "get", "subject": "all", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem removed", result)
        self.assertIn("Coin removed", result)
        self.assertEqual(len(self.bag.items), 0)

    async def test_get_treasure_from_room_container(self):
        """Test getting treasure from a room container."""
        self.bag.add_item(self.item1)  # value 50
        self.bag.add_item(self.item3)  # value 0 (not treasure)
        self.room.add_item(self.bag)

        cmd = {"verb": "get", "subject": "treasure", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("Gem", result)
        self.assertIn(self.item1, self.player.inventory)
        self.assertIn(self.item3, self.bag.items)  # Rock remains

    async def test_get_from_closed_room_container_fails(self):
        """Test getting from closed room container fails."""
        self.bag.add_item(self.item1)
        self.bag.set_state("closed")
        self.room.add_item(self.bag)

        cmd = {"verb": "get", "subject": "gem", "instrument": "bag"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("closed", result.lower())

    async def test_inventory_container_takes_priority(self):
        """Test that inventory container is used before room container."""
        # Create two bags - one in inventory, one in room
        inventory_bag = ContainerItem(
            "Bag", "bag_inv", "Inventory bag", weight=2, capacity_limit=5
        )
        inventory_bag.set_state("open")

        room_bag = ContainerItem(
            "Bag", "bag_room", "Room bag", weight=2, capacity_limit=5
        )
        room_bag.set_state("open")

        self.player.add_item(inventory_bag)
        self.player.add_item(self.item1)
        self.room.add_item(room_bag)

        cmd = {"verb": "put", "subject": "gem", "instrument": "bag"}

        await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Item should be in inventory bag, not room bag
        self.assertIn(self.item1, inventory_bag.items)
        self.assertNotIn(self.item1, room_bag.items)

    async def test_put_with_bound_room_container(self):
        """Test put with pre-bound room container object."""
        self.room.add_item(self.bag)
        self.player.add_item(self.item1)

        cmd = {
            "verb": "put",
            "subject": "gem",
            "subject_object": self.item1,
            "instrument": "bag",
            "instrument_object": self.bag,
        }

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("now inside", result)
        self.assertIn(self.item1, self.bag.items)

    async def test_get_with_bound_room_container(self):
        """Test get with pre-bound room container object."""
        self.bag.add_item(self.item1)
        self.room.add_item(self.bag)

        cmd = {
            "verb": "get",
            "subject": "gem",
            "subject_object": self.item1,
            "instrument": "bag",
            "instrument_object": self.bag,
        }

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("removed from", result)
        self.assertIn(self.item1, self.player.inventory)


class NoRemovalContainerTest(AsyncTestCase):
    """Test no_removal container functionality (e.g., donation box)."""

    def setUp(self):
        """Set up test fixtures with a no_removal container."""
        super().setUp()
        # Create a donation box that doesn't allow item removal
        self.donation_box = ContainerItem(
            "donation box",
            "donation_box",
            "A box for offerings.",
            weight=5,
            value=0,
            capacity_limit=10,
            capacity_weight=20,
            takeable=False,
            no_removal=True,
            no_removal_message="The priest glares at you. 'Those offerings are sacred!'",
        )
        self.donation_box.set_state("open")
        self.room.add_item(self.donation_box)

    async def test_put_item_in_no_removal_container_succeeds(self):
        """Test putting items into a no_removal container works."""
        self.player.add_item(self.item1)

        cmd = {"verb": "put", "subject": "gem", "instrument": "donation box"}

        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("now inside", result)
        self.assertIn(self.item1, self.donation_box.items)

    async def test_get_from_no_removal_container_fails(self):
        """Test getting items from a no_removal container is blocked."""
        self.donation_box.add_item(self.item1)

        cmd = {"verb": "get", "subject": "gem", "instrument": "donation box"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("priest glares", result)
        self.assertIn(self.item1, self.donation_box.items)
        self.assertNotIn(self.item1, self.player.inventory)

    async def test_get_all_from_no_removal_container_fails(self):
        """Test getting all items from a no_removal container is blocked."""
        self.donation_box.add_item(self.item1)
        self.donation_box.add_item(self.item2)

        cmd = {"verb": "get", "subject": "all", "instrument": "donation box"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("priest glares", result)
        self.assertEqual(len(self.donation_box.items), 2)

    async def test_get_treasure_from_no_removal_container_fails(self):
        """Test getting treasure from a no_removal container is blocked."""
        self.donation_box.add_item(self.item1)  # Has value

        cmd = {"verb": "get", "subject": "treasure", "instrument": "donation box"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("priest glares", result)
        self.assertIn(self.item1, self.donation_box.items)

    async def test_empty_no_removal_container_fails(self):
        """Test emptying a no_removal container is blocked."""
        # First add the container to player inventory so empty can find it
        self.room.items.remove(self.donation_box)
        self.donation_box.takeable = True  # Temporarily make takeable
        self.player.add_item(self.donation_box)
        self.donation_box.add_item(self.item1)

        cmd = {"verb": "empty", "subject": "donation box"}

        result = await handle_empty(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("priest glares", result)
        self.assertIn(self.item1, self.donation_box.items)

    async def test_no_removal_without_custom_message(self):
        """Test no_removal container uses default message when none provided."""
        # Create a container without custom message
        simple_box = ContainerItem(
            "offering bowl",
            "offering_bowl",
            "A simple bowl.",
            no_removal=True,
        )
        simple_box.set_state("open")
        simple_box.add_item(self.item1)
        self.room.add_item(simple_box)

        cmd = {"verb": "get", "subject": "gem", "instrument": "offering bowl"}

        result = await handle_get_from(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("cannot take items", result)

    async def test_no_removal_serialization(self):
        """Test no_removal property is preserved through serialization."""
        # Convert to dict and back
        data = self.donation_box.to_dict()
        restored = ContainerItem.from_dict(data)

        self.assertTrue(restored.no_removal)
        self.assertEqual(
            restored.no_removal_message,
            "The priest glares at you. 'Those offerings are sacred!'",
        )


class PutFallbackToInteractionTest(AsyncTestCase):
    """Test put command fallback to interaction system for StatefulItems."""

    def setUp(self):
        """Set up test fixtures with StatefulItem."""
        super().setUp()
        # Import StatefulItem for this test
        from models.StatefulItem import StatefulItem

        # Create a torch bracket (StatefulItem, not a container)
        self.bracket = StatefulItem(
            name="bracket",
            id="test_bracket",
            description="A torch bracket on the wall.",
            state="empty",
            takeable=False,
        )
        # Add state descriptions for all possible states
        self.bracket.add_state_description("empty", "An empty torch bracket.")
        self.bracket.add_state_description("lit", "A torch burns in the bracket.")
        self.bracket.add_interaction(
            verb="place",
            from_state="empty",
            target_state="lit",
            message="You place a torch in the bracket.",
            required_instrument="torch",
        )
        self.bracket.set_room_id("test_room")
        self.room.add_item(self.bracket)

        # Create a torch for the player
        self.torch = Item("Torch", "torch_1", "A burning torch", weight=1, value=5)
        self.player.add_item(self.torch)

    async def test_put_falls_back_to_interaction_for_stateful_item(self):
        """Test that 'put torch in bracket' works via fallback to interaction."""
        # Arrange
        cmd = {
            "verb": "put",
            "subject": "torch",
            "instrument": "bracket",
            "subject_object": self.torch,
            "instrument_object": self.bracket,
        }

        # Act
        result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert - verify the interaction was triggered
        self.assertIn("place", result.lower())
        self.assertEqual(self.bracket.state, "lit")

    async def test_put_fallback_without_required_instrument(self):
        """Test that put fallback fails when required instrument is missing."""
        # Arrange - player doesn't have torch
        self.player.remove_item(self.torch)
        cmd = {
            "verb": "put",
            "subject": "rock",
            "instrument": "bracket",
            "instrument_object": self.bracket,
        }

        # Act
        _result = await handle_put(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Assert - bracket state should not change
        self.assertEqual(self.bracket.state, "empty")


if __name__ == "__main__":
    unittest.main()
