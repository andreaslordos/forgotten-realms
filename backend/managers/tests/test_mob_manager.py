"""
Comprehensive tests for MobManager module - CRITICAL.

Tests cover:
- MobManager initialization
- Loading mob definitions
- Spawning mobs from templates
- Removing mobs
- Getting mobs (by ID, in room, all)
- Ticking mobs (AI, movement, aggression)
- Movement processing
- Aggression processing
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.test_base import BaseAsyncTest
from tests.test_helpers import (
    create_mock_player,
    create_mock_game_state,
    create_mock_room,
)
from managers.mob_manager import MobManager
from models.Mobile import Mobile


class MobManagerInitializationTest(unittest.TestCase):
    """Test MobManager initialization."""

    def test___init___initializes_empty_mobs_dict(self):
        """Test __init__ initializes empty mobs dictionary."""
        manager = MobManager()
        self.assertEqual(manager.mobs, {})

    def test___init___initializes_empty_mob_definitions_dict(self):
        """Test __init__ initializes empty mob_definitions dictionary."""
        manager = MobManager()
        self.assertEqual(manager.mob_definitions, {})

    def test___init___initializes_global_tick_counter_to_zero(self):
        """Test __init__ sets global_tick_counter to 0."""
        manager = MobManager()
        self.assertEqual(manager.global_tick_counter, 0)


class MobManagerLoadDefinitionsTest(unittest.TestCase):
    """Test MobManager.load_mob_definitions functionality."""

    def test_load_mob_definitions_stores_definitions(self):
        """Test load_mob_definitions stores definitions."""
        manager = MobManager()
        definitions = {
            "goblin": {"name": "goblin", "strength": 20},
            "wolf": {"name": "wolf", "strength": 30},
        }

        manager.load_mob_definitions(definitions)

        self.assertEqual(manager.mob_definitions, definitions)

    def test_load_mob_definitions_replaces_existing_definitions(self):
        """Test load_mob_definitions replaces existing definitions."""
        manager = MobManager()
        old_defs = {"old_mob": {"name": "old"}}
        new_defs = {"new_mob": {"name": "new"}}

        manager.load_mob_definitions(old_defs)
        manager.load_mob_definitions(new_defs)

        self.assertEqual(manager.mob_definitions, new_defs)
        self.assertNotIn("old_mob", manager.mob_definitions)

    def test_load_mob_definitions_accepts_empty_dict(self):
        """Test load_mob_definitions accepts empty dictionary."""
        manager = MobManager()

        manager.load_mob_definitions({})

        self.assertEqual(manager.mob_definitions, {})


class MobManagerSpawnMobTest(unittest.TestCase):
    """Test MobManager.spawn_mob functionality."""

    def setUp(self):
        """Set up manager and template for tests."""
        self.manager = MobManager()
        self.template = {
            "name": "goblin",
            "description": "A small goblin",
            "strength": 25,
            "dexterity": 30,
            "max_stamina": 60,
            "damage": 7,
            "aggressive": True,
            "aggro_delay_min": 3,
            "aggro_delay_max": 8,
            "patrol_rooms": ["room1", "room2"],
            "movement_interval": 8,
            "loot_table": [],
            "instant_death": False,
            "point_value": 50,
            "pronouns": "it",
        }
        self.manager.load_mob_definitions({"goblin": self.template})

    def test_spawn_mob_returns_mobile_instance(self):
        """Test spawn_mob returns Mobile instance."""
        mob = self.manager.spawn_mob("goblin", "room1")

        self.assertIsInstance(mob, Mobile)

    def test_spawn_mob_sets_mob_name_from_template(self):
        """Test spawn_mob sets mob name from template."""
        mob = self.manager.spawn_mob("goblin", "room1")

        self.assertEqual(mob.name, "goblin")

    def test_spawn_mob_sets_mob_stats_from_template(self):
        """Test spawn_mob sets mob stats from template."""
        mob = self.manager.spawn_mob("goblin", "room1")

        self.assertEqual(mob.strength, 25)
        self.assertEqual(mob.dexterity, 30)
        self.assertEqual(mob.max_stamina, 60)
        self.assertEqual(mob.damage, 7)

    def test_spawn_mob_sets_mob_behavior_from_template(self):
        """Test spawn_mob sets mob behavior from template."""
        mob = self.manager.spawn_mob("goblin", "room1")

        self.assertTrue(mob.aggressive)
        self.assertEqual(mob.aggro_delay_min, 3)
        self.assertEqual(mob.aggro_delay_max, 8)

    def test_spawn_mob_sets_current_room(self):
        """Test spawn_mob sets current_room to spawn room."""
        mob = self.manager.spawn_mob("goblin", "test_room")

        self.assertEqual(mob.current_room, "test_room")

    def test_spawn_mob_generates_unique_id(self):
        """Test spawn_mob generates unique ID."""
        mob1 = self.manager.spawn_mob("goblin", "room1")
        mob2 = self.manager.spawn_mob("goblin", "room1")

        self.assertNotEqual(mob1.id, mob2.id)

    def test_spawn_mob_adds_to_manager_tracking(self):
        """Test spawn_mob adds mob to manager's mobs dict."""
        mob = self.manager.spawn_mob("goblin", "room1")

        self.assertIn(mob.id, self.manager.mobs)
        self.assertEqual(self.manager.mobs[mob.id], mob)

    def test_spawn_mob_initializes_aggro_delay(self):
        """Test spawn_mob initializes aggro delay counter."""
        mob = self.manager.spawn_mob("goblin", "room1")

        self.assertIsNotNone(mob.aggro_tick_counter)
        self.assertGreaterEqual(mob.aggro_tick_counter, 0)

    def test_spawn_mob_adds_to_room_when_game_state_provided(self):
        """Test spawn_mob adds mob to room when game_state provided."""
        mock_room = create_mock_room("room1")
        mock_game_state = create_mock_game_state(rooms={"room1": mock_room})

        mob = self.manager.spawn_mob("goblin", "room1", game_state=mock_game_state)

        mock_room.add_item.assert_called_once_with(mob)

    def test_spawn_mob_returns_none_for_invalid_definition(self):
        """Test spawn_mob returns None for invalid definition ID."""
        mob = self.manager.spawn_mob("nonexistent", "room1")

        self.assertIsNone(mob)

    def test_spawn_mob_does_not_add_to_tracking_when_definition_invalid(self):
        """Test spawn_mob doesn't add to tracking when definition invalid."""
        initial_count = len(self.manager.mobs)

        self.manager.spawn_mob("nonexistent", "room1")

        self.assertEqual(len(self.manager.mobs), initial_count)

    def test_spawn_mob_uses_default_values_for_missing_fields(self):
        """Test spawn_mob uses default values for missing template fields."""
        minimal_template = {"name": "simple_mob"}
        self.manager.load_mob_definitions({"simple": minimal_template})

        mob = self.manager.spawn_mob("simple", "room1")

        self.assertEqual(mob.strength, 20)  # Default
        self.assertEqual(mob.dexterity, 20)  # Default
        self.assertFalse(mob.aggressive)  # Default


class MobManagerRemoveMobTest(unittest.TestCase):
    """Test MobManager.remove_mob functionality."""

    def setUp(self):
        """Set up manager with spawned mob."""
        self.manager = MobManager()
        template = {"name": "goblin", "strength": 25, "loot_table": []}
        self.manager.load_mob_definitions({"goblin": template})
        self.mob = self.manager.spawn_mob("goblin", "room1")
        self.mob_id = self.mob.id

    def test_remove_mob_removes_from_tracking(self):
        """Test remove_mob removes mob from mobs dict."""
        result = self.manager.remove_mob(self.mob_id)

        self.assertTrue(result)
        self.assertNotIn(self.mob_id, self.manager.mobs)

    def test_remove_mob_returns_false_for_nonexistent_mob(self):
        """Test remove_mob returns False for nonexistent mob."""
        result = self.manager.remove_mob("nonexistent_id")

        self.assertFalse(result)

    def test_remove_mob_removes_from_room_when_game_state_provided(self):
        """Test remove_mob removes mob from room when game_state provided."""
        mock_room = create_mock_room("room1")
        mock_game_state = create_mock_game_state(rooms={"room1": mock_room})

        self.manager.remove_mob(self.mob_id, game_state=mock_game_state)

        mock_room.remove_item.assert_called_once_with(self.mob)

    def test_remove_mob_handles_missing_room_gracefully(self):
        """Test remove_mob handles missing room gracefully."""
        mock_game_state = create_mock_game_state(rooms={})

        result = self.manager.remove_mob(self.mob_id, game_state=mock_game_state)

        self.assertTrue(result)


class MobManagerGetMobsTest(unittest.TestCase):
    """Test MobManager mob retrieval methods."""

    def setUp(self):
        """Set up manager with multiple mobs."""
        self.manager = MobManager()
        template = {"name": "goblin", "strength": 25, "loot_table": []}
        self.manager.load_mob_definitions({"goblin": template})

        self.mob1 = self.manager.spawn_mob("goblin", "room1")
        self.mob2 = self.manager.spawn_mob("goblin", "room2")
        self.mob3 = self.manager.spawn_mob("goblin", "room1")

    def test_get_mob_returns_mob_by_id(self):
        """Test get_mob returns mob by ID."""
        mob = self.manager.get_mob(self.mob1.id)

        self.assertEqual(mob, self.mob1)

    def test_get_mob_returns_none_for_invalid_id(self):
        """Test get_mob returns None for invalid ID."""
        mob = self.manager.get_mob("invalid_id")

        self.assertIsNone(mob)

    def test_get_mobs_in_room_returns_all_mobs_in_room(self):
        """Test get_mobs_in_room returns all mobs in specified room."""
        mobs = self.manager.get_mobs_in_room("room1")

        self.assertEqual(len(mobs), 2)
        self.assertIn(self.mob1, mobs)
        self.assertIn(self.mob3, mobs)

    def test_get_mobs_in_room_excludes_other_rooms(self):
        """Test get_mobs_in_room excludes mobs from other rooms."""
        mobs = self.manager.get_mobs_in_room("room1")

        self.assertNotIn(self.mob2, mobs)

    def test_get_mobs_in_room_excludes_dead_mobs(self):
        """Test get_mobs_in_room excludes dead mobs."""
        self.mob1.state = "dead"

        mobs = self.manager.get_mobs_in_room("room1")

        self.assertEqual(len(mobs), 1)
        self.assertIn(self.mob3, mobs)
        self.assertNotIn(self.mob1, mobs)

    def test_get_mobs_in_room_returns_empty_list_for_empty_room(self):
        """Test get_mobs_in_room returns empty list for room with no mobs."""
        mobs = self.manager.get_mobs_in_room("empty_room")

        self.assertEqual(mobs, [])

    def test_get_all_mobs_returns_all_mobs(self):
        """Test get_all_mobs returns all mobs."""
        mobs = self.manager.get_all_mobs()

        self.assertEqual(len(mobs), 3)
        self.assertIn(self.mob1, mobs)
        self.assertIn(self.mob2, mobs)
        self.assertIn(self.mob3, mobs)

    def test_get_all_mobs_includes_dead_mobs(self):
        """Test get_all_mobs includes dead mobs."""
        self.mob1.state = "dead"

        mobs = self.manager.get_all_mobs()

        self.assertEqual(len(mobs), 3)
        self.assertIn(self.mob1, mobs)


class MobManagerTickAllMobsTest(BaseAsyncTest):
    """Test MobManager.tick_all_mobs functionality."""

    def setUp(self):
        """Set up manager and mocks."""
        super().setUp()
        self.manager = MobManager()
        template = {
            "name": "goblin",
            "strength": 25,
            "aggressive": True,
            "patrol_rooms": ["room1", "room2"],
            "movement_interval": 5,
            "loot_table": [],
        }
        self.manager.load_mob_definitions({"goblin": template})
        self.mob = self.manager.spawn_mob("goblin", "room1")

        self.mock_player_manager = Mock()
        self.mock_game_state = create_mock_game_state()
        self.mock_utils = AsyncMock()

    @patch("commands.combat.is_in_combat")
    async def test_tick_all_mobs_increments_global_tick_counter(
        self, mock_is_in_combat
    ):
        """Test tick_all_mobs increments global tick counter."""
        mock_is_in_combat.return_value = False
        initial_tick = self.manager.global_tick_counter

        await self.manager.tick_all_mobs(
            self.mock_sio,
            {},
            self.mock_player_manager,
            self.mock_game_state,
            self.mock_utils,
        )

        self.assertEqual(self.manager.global_tick_counter, initial_tick + 1)

    @patch("commands.combat.is_in_combat")
    async def test_tick_all_mobs_ticks_aggro_counter(self, mock_is_in_combat):
        """Test tick_all_mobs ticks aggro counter for mobs."""
        mock_is_in_combat.return_value = False
        self.mob.aggro_tick_counter = 5

        await self.manager.tick_all_mobs(
            self.mock_sio,
            {},
            self.mock_player_manager,
            self.mock_game_state,
            self.mock_utils,
        )

        self.assertEqual(self.mob.aggro_tick_counter, 4)

    @patch("commands.combat.is_in_combat")
    async def test_tick_all_mobs_skips_dead_mobs(self, mock_is_in_combat):
        """Test tick_all_mobs skips dead mobs."""
        mock_is_in_combat.return_value = False
        self.mob.state = "dead"
        self.mob.aggro_tick_counter = 5

        await self.manager.tick_all_mobs(
            self.mock_sio,
            {},
            self.mock_player_manager,
            self.mock_game_state,
            self.mock_utils,
        )

        # Aggro counter should not be decremented
        self.assertEqual(self.mob.aggro_tick_counter, 5)

    @patch("commands.combat.is_in_combat")
    async def test_tick_all_mobs_skips_mobs_in_combat(self, mock_is_in_combat):
        """Test tick_all_mobs skips movement for mobs in combat."""
        mock_is_in_combat.return_value = True

        with patch.object(self.manager, "_process_mob_movement") as mock_movement:
            await self.manager.tick_all_mobs(
                self.mock_sio,
                {},
                self.mock_player_manager,
                self.mock_game_state,
                self.mock_utils,
            )

            mock_movement.assert_not_called()


class MobManagerProcessMovementTest(BaseAsyncTest):
    """Test MobManager._process_mob_movement functionality."""

    def setUp(self):
        """Set up manager and mocks."""
        super().setUp()
        self.manager = MobManager()
        template = {
            "name": "goblin",
            "patrol_rooms": ["room1", "room2"],
            "loot_table": [],
        }
        self.manager.load_mob_definitions({"goblin": template})

        self.mock_room1 = create_mock_room("room1")
        self.mock_room2 = create_mock_room("room2")
        self.mock_game_state = create_mock_game_state(
            rooms={"room1": self.mock_room1, "room2": self.mock_room2}
        )
        self.mock_utils = AsyncMock()
        self.mock_utils.send_message = AsyncMock()

    async def test_process_mob_movement_removes_mob_from_old_room(self):
        """Test _process_mob_movement removes mob from old room."""
        mob = self.manager.spawn_mob("goblin", "room1")
        mob.current_patrol_index = 0

        await self.manager._process_mob_movement(
            mob, self.mock_game_state, {}, self.mock_sio, self.mock_utils
        )

        self.mock_room1.remove_item.assert_called_once_with(mob)

    async def test_process_mob_movement_adds_mob_to_new_room(self):
        """Test _process_mob_movement adds mob to new room."""
        mob = self.manager.spawn_mob("goblin", "room1")
        mob.current_patrol_index = 0

        await self.manager._process_mob_movement(
            mob, self.mock_game_state, {}, self.mock_sio, self.mock_utils
        )

        self.mock_room2.add_item.assert_called_once_with(mob)

    async def test_process_mob_movement_updates_mob_current_room(self):
        """Test _process_mob_movement updates mob's current_room."""
        mob = self.manager.spawn_mob("goblin", "room1")
        mob.current_patrol_index = 0

        await self.manager._process_mob_movement(
            mob, self.mock_game_state, {}, self.mock_sio, self.mock_utils
        )

        self.assertEqual(mob.current_room, "room2")

    async def test_process_mob_movement_notifies_players_in_old_room(self):
        """Test _process_mob_movement notifies players in old room."""
        mob = self.manager.spawn_mob("goblin", "room1")
        mob.current_patrol_index = 0

        player = create_mock_player(location="room1")
        player.current_room = "room1"
        online_sessions = {"sid1": {"player": player}}

        await self.manager._process_mob_movement(
            mob, self.mock_game_state, online_sessions, self.mock_sio, self.mock_utils
        )

        self.mock_utils.send_message.assert_any_call(
            self.mock_sio, "sid1", "Goblin leaves."
        )

    async def test_process_mob_movement_notifies_players_in_new_room(self):
        """Test _process_mob_movement notifies players in new room."""
        mob = self.manager.spawn_mob("goblin", "room1")
        mob.current_patrol_index = 0

        player = create_mock_player(location="room2")
        player.current_room = "room2"
        online_sessions = {"sid1": {"player": player}}

        await self.manager._process_mob_movement(
            mob, self.mock_game_state, online_sessions, self.mock_sio, self.mock_utils
        )

        self.mock_utils.send_message.assert_any_call(
            self.mock_sio, "sid1", "Goblin arrives."
        )

    async def test_process_mob_movement_does_nothing_if_room_unchanged(self):
        """Test _process_mob_movement does nothing if mob stays in same room."""
        mob = self.manager.spawn_mob("goblin", "room1")
        mob.choose_next_room = Mock(return_value="room1")  # Stay in same room

        await self.manager._process_mob_movement(
            mob, self.mock_game_state, {}, self.mock_sio, self.mock_utils
        )

        self.mock_room1.remove_item.assert_not_called()

    async def test_process_mob_movement_resets_aggro_when_entering_room_with_player(
        self,
    ):
        """Test aggressive mob resets aggro delay when moving into room with player."""
        # Arrange - create aggressive mob with counter at 0 (ready to attack)
        mob = self.manager.spawn_mob("goblin", "room1")
        mob.aggressive = True
        mob.aggro_delay_min = 2  # Set delay range so reset works
        mob.aggro_delay_max = 4
        mob.aggro_tick_counter = 0  # Ready to attack
        mob.current_patrol_index = 0

        player = create_mock_player(location="room2")
        player.current_room = "room2"
        online_sessions = {"sid1": {"player": player}}

        # Act - mob moves into room with player
        await self.manager._process_mob_movement(
            mob, self.mock_game_state, online_sessions, self.mock_sio, self.mock_utils
        )

        # Assert - aggro delay should be reset (counter > 0)
        self.assertIsNotNone(mob.aggro_tick_counter)
        self.assertGreater(mob.aggro_tick_counter, 0)

    async def test_process_mob_movement_no_aggro_reset_for_non_aggressive_mob(self):
        """Test non-aggressive mob doesn't reset aggro when moving into room with player."""
        # Arrange - create non-aggressive mob
        mob = self.manager.spawn_mob("goblin", "room1")
        mob.aggressive = False
        mob.aggro_tick_counter = None
        mob.current_patrol_index = 0

        player = create_mock_player(location="room2")
        player.current_room = "room2"
        online_sessions = {"sid1": {"player": player}}

        # Act - mob moves into room with player
        await self.manager._process_mob_movement(
            mob, self.mock_game_state, online_sessions, self.mock_sio, self.mock_utils
        )

        # Assert - aggro counter should still be None (non-aggressive)
        self.assertIsNone(mob.aggro_tick_counter)


class MobManagerProcessAggressionTest(BaseAsyncTest):
    """Test MobManager._process_mob_aggression functionality."""

    def setUp(self):
        """Set up manager and mocks."""
        super().setUp()
        self.manager = MobManager()
        template = {"name": "goblin", "aggressive": True, "loot_table": []}
        self.manager.load_mob_definitions({"goblin": template})
        self.mob = self.manager.spawn_mob("goblin", "room1")

        self.mock_player_manager = Mock()
        self.mock_game_state = create_mock_game_state()
        self.mock_utils = AsyncMock()

    @patch("commands.combat.mob_initiate_attack", new_callable=AsyncMock)
    async def test_process_mob_aggression_initiates_attack_on_player_in_room(
        self, mock_initiate
    ):
        """Test _process_mob_aggression initiates attack on player."""
        player = create_mock_player(location="room1")
        player.current_room = "room1"
        online_sessions = {"sid1": {"player": player}}

        await self.manager._process_mob_aggression(
            self.mob,
            online_sessions,
            self.mock_player_manager,
            self.mock_game_state,
            self.mock_sio,
            self.mock_utils,
        )

        mock_initiate.assert_called_once_with(
            self.mob,
            player,
            "sid1",
            self.mock_player_manager,
            self.mock_game_state,
            online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

    @patch("commands.combat.mob_initiate_attack", new_callable=AsyncMock)
    async def test_process_mob_aggression_does_nothing_if_no_player_in_room(
        self, mock_initiate
    ):
        """Test _process_mob_aggression does nothing if no player in room."""
        player = create_mock_player(location="room2")
        player.current_room = "room2"
        online_sessions = {"sid1": {"player": player}}

        await self.manager._process_mob_aggression(
            self.mob,
            online_sessions,
            self.mock_player_manager,
            self.mock_game_state,
            self.mock_sio,
            self.mock_utils,
        )

        mock_initiate.assert_not_called()

    @patch("commands.combat.mob_initiate_attack", new_callable=AsyncMock)
    async def test_process_mob_aggression_handles_empty_sessions(self, mock_initiate):
        """Test _process_mob_aggression handles empty online_sessions."""
        await self.manager._process_mob_aggression(
            self.mob,
            {},
            self.mock_player_manager,
            self.mock_game_state,
            self.mock_sio,
            self.mock_utils,
        )

        mock_initiate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
