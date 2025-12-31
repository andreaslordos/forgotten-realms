"""
Comprehensive tests for combat module.

Tests cover core combat functionality including:
- Player vs Player combat initiation and resolution
- Player vs Mob combat initiation and resolution
- Combat state management and helper functions
- Weapon requirements and validation
- Flee mechanics and point transfers

Note: This file focuses on testing the main combat flows rather than
exhaustively testing every edge case, to ensure tests are maintainable
and accurate to the current combat.py implementation.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.combat import (
    handle_attack,
    handle_retaliate,
    handle_flee,
    find_player_sid,
    find_player_by_name,
    end_combat,
    is_in_combat,
    check_command_restrictions,
    active_combats,
)
from models.Mobile import Mobile
from models.Weapon import Weapon
from models.Item import Item
from models.Room import Room


class CombatBasicTest(unittest.IsolatedAsyncioTestCase):
    """Test basic combat functionality."""

    def setUp(self):
        """Set up common test fixtures."""
        active_combats.clear()

    def test_is_in_combat_returns_true_when_in_combat(self):
        """Test is_in_combat returns True when player is in combat."""
        active_combats["TestPlayer"] = {"target": Mock()}

        self.assertTrue(is_in_combat("TestPlayer"))

    def test_is_in_combat_returns_false_when_not_in_combat(self):
        """Test is_in_combat returns False when player not in combat."""
        self.assertFalse(is_in_combat("TestPlayer"))

    def test_end_combat_removes_both_players(self):
        """Test end_combat removes combat state for both combatants."""
        active_combats["Player1"] = {"target": Mock()}
        active_combats["Player2"] = {"target": Mock()}

        end_combat("Player1", "Player2")

        self.assertNotIn("Player1", active_combats)
        self.assertNotIn("Player2", active_combats)


class HelperFunctionsTest(unittest.TestCase):
    """Test helper functions for combat system."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"

        self.online_sessions = {"player_sid": {"player": self.player}}

    def test_find_player_sid_by_name(self):
        """Test find_player_sid finds player by name string."""
        result = find_player_sid("TestPlayer", self.online_sessions)

        self.assertEqual(result, "player_sid")

    def test_find_player_sid_by_object(self):
        """Test find_player_sid finds player by player object."""
        result = find_player_sid(self.player, self.online_sessions)

        self.assertEqual(result, "player_sid")

    def test_find_player_sid_returns_none_if_not_found(self):
        """Test find_player_sid returns None if player not found."""
        result = find_player_sid("UnknownPlayer", self.online_sessions)

        self.assertIsNone(result)

    def test_find_player_by_name_finds_player(self):
        """Test find_player_by_name finds player by name."""
        result = find_player_by_name("TestPlayer", self.online_sessions)

        self.assertEqual(result, self.player)

    def test_find_player_by_name_returns_none_if_not_found(self):
        """Test find_player_by_name returns None if player not found."""
        result = find_player_by_name("UnknownPlayer", self.online_sessions)

        self.assertIsNone(result)


class CheckCommandRestrictionsTest(unittest.TestCase):
    """Test check_command_restrictions for combat restrictions."""

    def setUp(self):
        """Set up common test fixtures."""
        active_combats.clear()

        self.player = Mock()
        self.player.name = "TestPlayer"

    def test_allows_unrestricted_commands_during_combat(self):
        """Test unrestricted commands are allowed during combat."""
        active_combats["TestPlayer"] = {"target": Mock()}

        cmd = {"verb": "look"}
        allowed, message = check_command_restrictions(cmd, self.player)

        self.assertTrue(allowed)
        self.assertEqual(message, "")

    def test_blocks_movement_during_combat(self):
        """Test movement commands are blocked during combat."""
        active_combats["TestPlayer"] = {"target": Mock()}

        cmd = {"verb": "north"}
        allowed, message = check_command_restrictions(cmd, self.player)

        self.assertFalse(allowed)
        self.assertIn("combat", message.lower())

    def test_blocks_quit_during_combat(self):
        """Test quit is blocked during combat."""
        active_combats["TestPlayer"] = {"target": Mock()}

        cmd = {"verb": "quit"}
        allowed, message = check_command_restrictions(cmd, self.player)

        self.assertFalse(allowed)
        self.assertIn("combat", message.lower())

    def test_allows_all_commands_when_not_in_combat(self):
        """Test all commands allowed when not in combat."""
        cmd = {"verb": "quit"}
        allowed, message = check_command_restrictions(cmd, self.player)

        self.assertTrue(allowed)
        self.assertEqual(message, "")


class HandleAttackTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_attack command."""

    def setUp(self):
        """Set up common test fixtures."""
        active_combats.clear()

        self.player = Mock()
        self.player.name = "Attacker"
        self.player.current_room = "room1"
        self.player.strength = 20
        self.player.dexterity = 15
        self.player.inventory = []
        self.player.get_effective_dexterity = (
            lambda *args, **kwargs: self.player.dexterity
        )

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()
        # Mock mob_manager to return empty list
        self.utils.mob_manager = Mock()
        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[])

        self.online_sessions = {}

    async def test_attack_with_no_target_returns_error(self):
        """Test attacking with no target returns error message."""
        cmd = {"verb": "attack", "subject": None, "subject_object": None}

        result = await handle_attack(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("who", result.lower())

    async def test_attack_nonexistent_target(self):
        """Test attacking a target that doesn't exist."""
        cmd = {
            "verb": "attack",
            "subject": "NonexistentTarget",
            "subject_object": None,
            "instrument": None,
            "instrument_object": None,
        }

        result = await handle_attack(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should return error message
        self.assertIsInstance(result, str)
        self.assertIn("see", result.lower())

    async def test_attack_when_already_in_combat(self):
        """Test attacking when already in combat returns error."""
        existing_target = Mock()
        existing_target.name = "ExistingTarget"

        active_combats["Attacker"] = {"target": existing_target, "weapon": None}

        cmd = {"verb": "attack", "subject": "NewTarget", "subject_object": None}

        result = await handle_attack(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("already", result.lower())


class HandleRetaliateTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_retaliate command."""

    def setUp(self):
        """Set up common test fixtures."""
        active_combats.clear()

        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "room1"
        self.player.strength = 20
        self.player.dexterity = 15
        self.player.inventory = []
        self.player.get_effective_dexterity = (
            lambda *args, **kwargs: self.player.dexterity
        )

        self.weapon = Weapon(
            name="iron sword",
            id="sword_1",
            description="A sword",
            damage=10,
            weight=5,
            min_strength=10,
            min_dexterity=8,
        )
        self.player.inventory.append(self.weapon)

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()
        # Mock mob_manager to return empty list
        self.utils.mob_manager = Mock()
        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[])

        self.online_sessions = {}

    async def test_retaliate_requires_being_in_combat(self):
        """Test retaliate requires player to be in combat."""
        cmd = {
            "verb": "retaliate",
            "instrument": "sword",
            "instrument_object": self.weapon,
        }

        result = await handle_retaliate(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("not in combat", result.lower())

    async def test_retaliate_requires_weapon(self):
        """Test retaliate requires weapon to be specified."""
        active_combats["TestPlayer"] = {"target": Mock(), "weapon": None}

        cmd = {"verb": "retaliate", "instrument": None, "instrument_object": None}

        result = await handle_retaliate(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("weapon", result.lower())

    async def test_retaliate_switches_weapon(self):
        """Test retaliate successfully switches weapon."""
        opponent = Mock()
        opponent.name = "Opponent"

        active_combats["TestPlayer"] = {
            "target": opponent,
            "target_sid": "opponent_sid",
            "weapon": None,
        }

        cmd = {
            "verb": "retaliate",
            "instrument": "sword",
            "instrument_object": self.weapon,
        }

        result = await handle_retaliate(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Weapon should be updated in combat state
        self.assertEqual(active_combats["TestPlayer"]["weapon"], self.weapon)
        self.assertIn("ready", result.lower())


class HandleFleeTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_flee command."""

    def setUp(self):
        """Set up common test fixtures."""
        active_combats.clear()

        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "room1"
        self.player.points = 100
        self.player.dexterity = 15
        self.player.inventory = []
        self.player.set_current_room = Mock()
        self.player.remove_item = Mock()
        self.player.add_points = Mock(return_value=(False, ""))
        self.player.get_effective_dexterity = (
            lambda *args, **kwargs: self.player.dexterity
        )

        self.opponent = Mock()
        self.opponent.name = "Opponent"
        self.opponent.current_room = "room1"
        self.opponent.dexterity = 15
        self.opponent.stamina = 100
        self.opponent.add_points = Mock()
        self.opponent.get_effective_dexterity = (
            lambda *args, **kwargs: self.opponent.dexterity
        )

        self.room = Room(
            room_id="room1",
            name="Test Room",
            description="A room",
            exits={"north": "room2", "south": "room3"},
        )

        self.new_room = Room(
            room_id="room2", name="New Room", description="Another room"
        )

        active_combats["TestPlayer"] = {
            "target": self.opponent,
            "target_sid": "opponent_sid",
            "weapon": None,
            "is_mob": False,
        }
        active_combats["Opponent"] = {
            "target": self.player,
            "target_sid": "player_sid",
            "weapon": None,
            "is_mob": False,
        }

        self.game_state = Mock()
        self.game_state.get_room = Mock(
            side_effect=lambda x: self.room if x == "room1" else self.new_room
        )

        self.player_manager = Mock()
        self.player_manager.save_players = Mock()

        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        self.online_sessions = {}

    async def test_flee_requires_being_in_combat(self):
        """Test flee requires player to be in combat."""
        active_combats.clear()

        cmd = {"verb": "flee"}

        result = await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("not in combat", result.lower())

    async def test_flee_requires_exits(self):
        """Test flee requires room to have exits."""
        self.room.exits = {}

        cmd = {"verb": "flee"}

        result = await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("nowhere", result.lower())

    async def test_flee_moves_player_and_loses_points(self):
        """Test flee moves player and causes point loss."""
        cmd = {"verb": "flee"}

        await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should move player
        self.player.set_current_room.assert_called()

        # Should lose points
        self.player.add_points.assert_called()
        call_args = self.player.add_points.call_args[0]
        self.assertLess(call_args[0], 0)  # Negative points = loss

    async def test_flee_ends_combat(self):
        """Test flee ends combat for both players."""
        cmd = {"verb": "flee"}

        await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Combat should be ended
        self.assertNotIn("TestPlayer", active_combats)
        self.assertNotIn("Opponent", active_combats)


class MobileTest(unittest.TestCase):
    """Test Mobile (mob) class integration with combat."""

    def test_mobile_creation(self):
        """Test creating a Mobile object."""
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="A goblin",
            strength=15,
            dexterity=10,
            max_stamina=50,
            current_room="room1",
        )

        self.assertEqual(mob.name, "goblin")
        self.assertEqual(mob.id, "goblin_1")
        self.assertEqual(mob.strength, 15)
        self.assertEqual(mob.stamina, 50)
        self.assertEqual(mob.max_stamina, 50)

    def test_mobile_take_damage(self):
        """Test Mobile can take damage."""
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="A goblin",
            max_stamina=50,
            current_room="room1",
        )

        is_dead, remaining = mob.take_damage(20)

        self.assertFalse(is_dead)
        self.assertEqual(remaining, 30)
        self.assertEqual(mob.stamina, 30)

    def test_mobile_dies_when_health_reaches_zero(self):
        """Test Mobile dies when stamina reaches 0."""
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="A goblin",
            max_stamina=50,
            current_room="room1",
        )

        is_dead, remaining = mob.take_damage(60)

        self.assertTrue(is_dead)
        self.assertEqual(remaining, 0)
        self.assertEqual(mob.state, "dead")


class WeaponRequirementsTest(unittest.TestCase):
    """Test weapon requirement checking."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.level = "Novice"
        self.player.strength = 20
        self.player.dexterity = 15

    def test_weapon_can_be_used_when_requirements_met(self):
        """Test weapon can be used when requirements are met."""
        weapon = Weapon(
            name="iron sword",
            id="sword_1",
            description="A sword",
            damage=10,
            min_strength=15,
            min_dexterity=10,
        )

        can_use, reason = weapon.can_use(self.player)

        self.assertTrue(can_use)
        self.assertEqual(reason, "")

    def test_weapon_requires_sufficient_strength(self):
        """Test weapon requires sufficient strength."""
        self.player.strength = 5

        weapon = Weapon(
            name="iron sword",
            id="sword_1",
            description="A sword",
            damage=10,
            min_strength=15,
            min_dexterity=10,
        )

        can_use, reason = weapon.can_use(self.player)

        self.assertFalse(can_use)
        self.assertIn("strength", reason.lower())

    def test_weapon_requires_sufficient_dexterity(self):
        """Test weapon requires sufficient dexterity."""
        self.player.dexterity = 5

        weapon = Weapon(
            name="iron sword",
            id="sword_1",
            description="A sword",
            damage=10,
            min_strength=15,
            min_dexterity=10,
        )

        can_use, reason = weapon.can_use(self.player)

        self.assertFalse(can_use)
        self.assertIn("dexterity", reason.lower())


class ProcessCombatTickTest(unittest.IsolatedAsyncioTestCase):
    """Test process_combat_tick function."""

    async def test_process_combat_tick_with_no_active_combats(self):
        """Test combat tick with no active combats does nothing."""
        from commands.combat import process_combat_tick

        sio = AsyncMock()
        online_sessions = {}
        player_manager = Mock()
        game_state = Mock()
        utils = Mock()
        mob_manager = Mock()

        # Should not raise any errors
        await process_combat_tick(
            sio, online_sessions, player_manager, game_state, utils, mob_manager
        )

        # No assertions needed - just checking it doesn't crash

    async def test_process_combat_tick_with_player_vs_player(self):
        """Test combat tick processes player vs player combat."""
        from commands.combat import process_combat_tick, active_combats

        active_combats.clear()

        player1 = Mock()
        player1.name = "Player1"
        player1.current_room = "room1"
        player1.strength = 50
        player1.dexterity = 50
        player1.stamina = 100
        player1.get_effective_dexterity = lambda *args, **kwargs: player1.dexterity

        player2 = Mock()
        player2.name = "Player2"
        player2.current_room = "room1"
        player2.strength = 40
        player2.dexterity = 40
        player2.stamina = 100
        player2.get_effective_dexterity = lambda *args, **kwargs: player2.dexterity

        active_combats["Player1"] = {
            "target": player2,
            "target_sid": "player2_sid",
            "weapon": None,
            "initiative": True,
            "last_turn": None,
            "is_mob": False,
            "entity": player1,
        }

        active_combats["Player2"] = {
            "target": player1,
            "target_sid": "player1_sid",
            "weapon": None,
            "initiative": False,
            "last_turn": None,
            "is_mob": False,
            "entity": player2,
        }

        sio = AsyncMock()
        online_sessions = {
            "player1_sid": {"player": player1},
            "player2_sid": {"player": player2},
        }
        player_manager = Mock()
        game_state = Mock()
        utils = Mock()
        utils.send_message = AsyncMock()
        utils.send_stats_update = AsyncMock()
        mob_manager = Mock()

        with patch("random.randint", return_value=50):
            with patch("random.uniform", return_value=1.0):
                await process_combat_tick(
                    sio, online_sessions, player_manager, game_state, utils, mob_manager
                )

        # Should have sent messages
        self.assertTrue(utils.send_message.called)


class HandleCombatDisconnectTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_combat_disconnect function."""

    async def test_combat_disconnect_ends_combat(self):
        """Test disconnecting during combat ends the combat."""
        from commands.combat import handle_combat_disconnect, active_combats

        active_combats.clear()

        player1 = Mock()
        player1.name = "Player1"
        player2 = Mock()
        player2.name = "Player2"

        active_combats["Player1"] = {
            "target": player2,
            "target_sid": "player2_sid",
            "is_mob": False,
        }
        active_combats["Player2"] = {
            "target": player1,
            "target_sid": "player1_sid",
            "is_mob": False,
        }

        sio = AsyncMock()
        online_sessions = {}
        player_manager = Mock()
        game_state = Mock()
        utils = Mock()
        utils.send_message = AsyncMock()

        await handle_combat_disconnect(
            "Player1", online_sessions, player_manager, game_state, sio, utils
        )

        # Combat should be ended
        self.assertNotIn("Player1", active_combats)
        self.assertNotIn("Player2", active_combats)


class HandleAttackAdvancedTest(unittest.IsolatedAsyncioTestCase):
    """Test advanced attack scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Attacker"
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.strength = 50
        self.player.dexterity = 50
        self.player.get_effective_dexterity = (
            lambda *args, **kwargs: self.player.dexterity
        )

        self.target = Mock()
        self.target.name = "Target"
        self.target.current_room = "room1"
        self.target.stamina = 100
        self.target.max_stamina = 100
        self.target.dexterity = 40
        self.target.get_effective_dexterity = (
            lambda *args, **kwargs: self.target.dexterity
        )

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_attack_with_sleeping_target(self):
        """Test attacking a sleeping player."""
        from unittest.mock import patch

        target_sid = "target_sid"
        self.online_sessions = {
            "attacker_sid": {"player": self.player},
            target_sid: {"player": self.target, "sleeping": True},
        }

        cmd = {"verb": "attack", "subject": "Target", "subject_object": self.target}

        with patch("commands.combat.wake_player", new_callable=AsyncMock) as mock_wake:
            with patch("commands.combat.process_combat_attack", new_callable=AsyncMock):
                result = await handle_attack(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    self.online_sessions,
                    self.sio,
                    self.utils,
                )

                mock_wake.assert_called_once()
                self.assertIn("attack", result.lower())

    async def test_attack_with_weapon_requirements_not_met(self):
        """Test attacking with a weapon that can't be used."""
        weapon = Mock(spec=Weapon)
        weapon.name = "Heavy Sword"
        weapon.can_use = Mock(return_value=(False, "You're not strong enough!"))
        self.player.inventory = [weapon]

        cmd = {
            "verb": "attack",
            "subject": "Target",
            "subject_object": self.target,
            "instrument": "sword",
            "instrument_object": weapon,
        }

        result = await handle_attack(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("not strong enough", result)

    async def test_attack_with_weapon_found_by_name(self):
        """Test attacking with weapon found by name in inventory."""
        weapon = Item(name="bronze sword", id="sword_1", description="A sword")
        weapon.damage = 10
        self.player.inventory = [weapon]
        self.online_sessions = {
            "attacker_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }

        cmd = {
            "verb": "attack",
            "subject": "Target",
            "subject_object": self.target,
            "instrument": "sword",
        }

        with patch("commands.combat.process_combat_attack", new_callable=AsyncMock):
            result = await handle_attack(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertIn("attack", result.lower())
            self.assertEqual(active_combats[self.player.name]["weapon"], weapon)

    async def test_attack_with_non_weapon_item(self):
        """Test attacking with non-weapon item."""
        non_weapon = Item(name="scroll", id="scroll_1", description="A scroll")
        self.player.inventory = [non_weapon]

        cmd = {
            "verb": "attack",
            "subject": "Target",
            "subject_object": self.target,
            "instrument": "scroll",
        }

        result = await handle_attack(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("not a weapon", result)


class HandleRetaliateAdvancedTest(unittest.IsolatedAsyncioTestCase):
    """Test advanced retaliate scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Player1"
        self.player.inventory = []

        self.target = Mock()
        self.target.name = "Target"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

        active_combats.clear()

    async def test_retaliate_with_non_weapon_fails(self):
        """Test retaliating with non-weapon item fails."""
        non_weapon = Item(name="scroll", id="scroll_1", description="A scroll")
        self.player.inventory = [non_weapon]

        active_combats[self.player.name] = {
            "target": self.target,
            "target_sid": "target_sid",
            "weapon": None,
        }

        cmd = {
            "verb": "retaliate",
            "instrument": "scroll",
            "instrument_object": non_weapon,
        }

        result = await handle_retaliate(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("not a weapon", result)

    async def test_retaliate_weapon_not_found(self):
        """Test retaliate when weapon not in inventory."""
        active_combats[self.player.name] = {
            "target": self.target,
            "target_sid": "target_sid",
            "weapon": None,
        }

        cmd = {"verb": "retaliate", "instrument": "sword"}

        result = await handle_retaliate(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("don't have", result.lower())

    async def test_retaliate_weapon_requirements_not_met(self):
        """Test retaliate with weapon that can't be used."""
        weapon = Mock(spec=Weapon)
        weapon.name = "Heavy Axe"
        weapon.can_use = Mock(return_value=(False, "Too heavy!"))
        self.player.inventory = [weapon]

        active_combats[self.player.name] = {
            "target": self.target,
            "target_sid": "target_sid",
            "weapon": None,
        }

        cmd = {"verb": "retaliate", "instrument": "axe", "instrument_object": weapon}

        result = await handle_retaliate(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("heavy", result.lower())


class HandleFleeAdvancedTest(unittest.IsolatedAsyncioTestCase):
    """Test advanced flee scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Player1"
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.points = 1000
        self.player.add_points = Mock(return_value=(False, "Updated"))
        self.player.remove_item = Mock()
        self.player.set_current_room = Mock()

        self.opponent = Mock()
        self.opponent.name = "Opponent"
        self.opponent.add_points = Mock()

        self.current_room = Mock()
        self.current_room.room_id = "room1"
        self.current_room.exits = {"north": "room2"}
        self.current_room.add_item = Mock()

        self.new_room = Mock()
        self.new_room.room_id = "room2"
        self.new_room.name = "North Room"
        self.new_room.description = "A northern room"
        self.new_room.is_dark = False  # Room is lit by default
        self.new_room.get_items = Mock(return_value=[])  # No items

        self.game_state = Mock()
        self.game_state.get_room = Mock(
            side_effect=lambda rid: (
                self.current_room if rid == "room1" else self.new_room
            )
        )
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_flee_with_specific_direction(self):
        """Test fleeing in a specific direction."""
        active_combats[self.player.name] = {
            "target": self.opponent,
            "target_sid": "opponent_sid",
            "is_mob": False,
        }

        cmd = {"verb": "flee", "subject": "north"}

        result = await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("flee", result.lower())
        self.assertIn("north", result.lower())

    async def test_flee_when_new_room_not_found(self):
        """Test flee when new room doesn't exist."""
        self.game_state.get_room = Mock(
            side_effect=lambda rid: self.current_room if rid == "room1" else None
        )

        active_combats[self.player.name] = {
            "target": self.opponent,
            "target_sid": "opponent_sid",
            "is_mob": False,
        }

        cmd = {"verb": "flee", "subject": "north"}

        result = await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("went wrong", result)

    async def test_flee_notifies_others_in_old_room(self):
        """Test flee notifies other players in the old room."""
        active_combats[self.player.name] = {
            "target": self.opponent,
            "target_sid": "opponent_sid",
            "is_mob": False,
        }

        other_player = Mock()
        other_player.name = "Observer"
        other_player.current_room = "room1"

        self.online_sessions = {
            "player_sid": {"player": self.player},
            "opponent_sid": {"player": self.opponent},
            "observer_sid": {"player": other_player},
        }

        cmd = {"verb": "flee", "subject": "north"}

        await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should notify observer
        self.utils.send_message.assert_any_call(
            self.sio, "observer_sid", unittest.mock.ANY
        )

    async def test_flee_notifies_others_in_new_room(self):
        """Test flee notifies players in the new room."""
        active_combats[self.player.name] = {
            "target": self.opponent,
            "target_sid": "opponent_sid",
            "is_mob": False,
        }

        new_room_player = Mock()
        new_room_player.name = "NewRoomPlayer"
        new_room_player.current_room = "room2"

        self.online_sessions = {"new_room_sid": {"player": new_room_player}}

        cmd = {"verb": "flee"}

        await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should notify new room player
        self.assertTrue(
            any(
                "runs in" in str(call)
                for call in self.utils.send_message.call_args_list
            )
        )

    async def test_flee_into_dark_room_hides_description(self):
        """Test fleeing into a dark room shows darkness message instead of description."""
        active_combats[self.player.name] = {
            "target": self.opponent,
            "target_sid": "opponent_sid",
            "is_mob": False,
        }

        # Make the destination room dark
        self.new_room.is_dark = True

        cmd = {"verb": "flee", "subject": "north"}

        result = await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should show flee message but NOT show room description
        self.assertIn("flee", result.lower())
        self.assertIn("too dark", result.lower())
        self.assertNotIn("New Room", result)

    async def test_flee_into_dark_room_with_light_shows_description(self):
        """Test fleeing into dark room with light source on ground shows full description."""
        from models.Item import Item

        active_combats[self.player.name] = {
            "target": self.opponent,
            "target_sid": "opponent_sid",
            "is_mob": False,
        }

        # Make the destination room dark but with a light source on the ground
        self.new_room.is_dark = True
        torch = Item("torch", "torch_1", "A torch", emits_light=True)
        self.new_room.get_items = Mock(return_value=[torch])  # Light source in room

        cmd = {"verb": "flee", "subject": "north"}

        result = await handle_flee(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should show flee message and room description since there's light in the room
        self.assertIn("flee", result.lower())
        self.assertIn("North Room", result)
        self.assertNotIn("too dark", result.lower())


class ProcessCombatAttackTest(unittest.IsolatedAsyncioTestCase):
    """Test process_combat_attack function."""

    def setUp(self):
        """Set up test fixtures."""

        self.player = Mock()
        self.player.name = "Attacker"
        self.player.strength = 50
        self.player.dexterity = 50
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.get_effective_dexterity = (
            lambda *args, **kwargs: self.player.dexterity
        )

        self.target = Mock()
        self.target.name = "Defender"
        self.target.stamina = 100
        self.target.dexterity = 40
        self.target.current_room = "room1"
        self.target.get_effective_dexterity = (
            lambda *args, **kwargs: self.target.dexterity
        )

        self.weapon = Item(name="sword", id="sword_1", description="A sword")
        self.weapon.damage = 10

        self.game_state = Mock()
        self.player_manager = Mock()
        self.player_manager.save_players = Mock()
        self.online_sessions = {
            "attacker_sid": {"player": self.player},
            "defender_sid": {"player": self.target},
        }
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_process_combat_attack_with_weapon(self):
        """Test combat attack with weapon."""
        from commands.combat import process_combat_attack

        self.player.inventory = [self.weapon]

        with patch("random.randint", return_value=50):
            with patch("random.uniform", return_value=1.0):
                await process_combat_attack(
                    self.player,
                    self.target,
                    self.weapon,
                    "attacker_sid",
                    "defender_sid",
                    self.player_manager,
                    self.game_state,
                    self.online_sessions,
                    self.sio,
                    self.utils,
                )

        # Should send messages
        self.utils.send_message.assert_called()

    async def test_process_combat_attack_weapon_not_in_inventory(self):
        """Test combat attack when weapon is no longer in inventory."""
        from commands.combat import process_combat_attack

        # Weapon not in inventory
        self.player.inventory = []

        with patch("random.randint", return_value=50):
            with patch("random.uniform", return_value=1.0):
                await process_combat_attack(
                    self.player,
                    self.target,
                    self.weapon,
                    "attacker_sid",
                    "defender_sid",
                    self.player_manager,
                    self.game_state,
                    self.online_sessions,
                    self.sio,
                    self.utils,
                )

        # Should still complete
        self.utils.send_message.assert_called()

    async def test_process_combat_attack_miss(self):
        """Test combat attack that misses."""
        from commands.combat import process_combat_attack

        # Force miss with low roll
        with patch("random.randint", return_value=1):
            with patch("random.uniform", return_value=1.0):
                await process_combat_attack(
                    self.player,
                    self.target,
                    None,
                    "attacker_sid",
                    "defender_sid",
                    self.player_manager,
                    self.game_state,
                    self.online_sessions,
                    self.sio,
                    self.utils,
                )

        # Should send messages
        self.assertTrue(self.utils.send_message.called)


class HandlePlayerDefeatTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_player_defeat function."""

    def setUp(self):
        """Set up test fixtures."""

        self.attacker = Mock()
        self.attacker.name = "Winner"
        self.attacker.add_points = Mock(return_value=(False, ""))

        self.defender = Mock()
        self.defender.name = "Loser"
        self.defender.current_room = "room1"
        self.defender.points = 1000
        self.defender.max_stamina = 100
        self.defender.stamina = 100
        self.defender.inventory = []
        self.defender.add_points = Mock(return_value=(False, ""))
        self.defender.remove_item = Mock()
        self.defender.set_current_room = Mock()

        self.current_room = Mock()
        self.current_room.add_item = Mock()

        self.spawn_room = Mock()
        self.spawn_room.name = "Village Center"
        self.spawn_room.description = "The village center"

        self.game_state = Mock()
        self.game_state.get_room = Mock(
            side_effect=lambda rid: (
                self.current_room if rid == "room1" else self.spawn_room
            )
        )

        self.player_manager = Mock()
        self.player_manager.spawn_room = "spawn_room"
        self.player_manager.save_players = Mock()

        self.online_sessions = {
            "attacker_sid": {"player": self.attacker},
            "defender_sid": {"player": self.defender},
        }
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_handle_player_defeat_drops_items(self):
        """Test player defeat drops all items."""
        from commands.combat import handle_player_defeat

        item1 = Item(name="sword", id="sword_1", description="A sword")
        item2 = Item(name="shield", id="shield_1", description="A shield")
        self.defender.inventory = [item1, item2]

        active_combats["Winner"] = {
            "target": self.defender,
            "target_sid": "defender_sid",
            "weapon": None,
        }

        await handle_player_defeat(
            self.attacker,
            self.defender,
            "defender_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should call remove_item for each item
        self.assertEqual(self.defender.remove_item.call_count, 2)
        # Should add items to room
        self.assertEqual(self.current_room.add_item.call_count, 2)

    async def test_handle_player_defeat_transfers_points(self):
        """Test player defeat transfers points to attacker."""
        from commands.combat import handle_player_defeat

        active_combats["Winner"] = {
            "target": self.defender,
            "target_sid": "defender_sid",
            "weapon": None,
        }

        await handle_player_defeat(
            self.attacker,
            self.defender,
            "defender_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Attacker should gain points
        self.attacker.add_points.assert_called()
        # Defender's points are NOT immediately zeroed (happens on respawn)


class HandleMobAttackTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_mob_attack function."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Player1"
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.strength = 50
        self.player.dexterity = 50
        self.player.get_effective_dexterity = (
            lambda *args, **kwargs: self.player.dexterity
        )

        self.mob = Mock(spec=Mobile)
        self.mob.id = "goblin_1"
        self.mob.name = "goblin"
        self.mob.current_room = "room1"
        self.mob.target_player = None
        self.mob.dexterity = 40
        self.mob.get_effective_dexterity = lambda *args, **kwargs: self.mob.dexterity

        self.weapon = Item(name="sword", id="sword_1", description="A sword")
        self.weapon.damage = 10

        self.game_state = Mock()
        self.current_room = Mock()
        self.current_room.room_id = "room1"
        self.game_state.get_room = Mock(return_value=self.current_room)

        self.player_manager = Mock()
        self.mob_manager = Mock()
        self.online_sessions = {"player_sid": {"player": self.player}}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_handle_mob_attack_starts_combat(self):
        """Test attacking mob starts combat."""
        from commands.combat import handle_mob_attack

        with patch(
            "commands.combat.process_mob_combat_attack", new_callable=AsyncMock
        ) as mock_attack:
            await handle_mob_attack(
                self.player,
                self.mob,
                self.weapon,
                "player_sid",
                self.player_manager,
                self.game_state,
                self.online_sessions,
                self.mob_manager,
                self.sio,
                self.utils,
            )

            # Should start combat
            self.assertIn(self.player.name, active_combats)
            self.assertIn(self.mob.id, active_combats)
            self.assertEqual(self.mob.target_player, self.player)
            mock_attack.assert_called_once()


class HandlePlayerDefeatByMobTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_player_defeat_by_mob function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mob = Mock(spec=Mobile)
        self.mob.id = "goblin_1"
        self.mob.name = "goblin"
        self.mob.target_player = None

        self.player = Mock()
        self.player.name = "Player1"
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.points = 500
        self.player.max_stamina = 100
        self.player.stamina = 100
        self.player.add_points = Mock(return_value=(False, ""))
        self.player.remove_item = Mock()
        self.player.set_current_room = Mock()

        self.current_room = Mock()
        self.current_room.add_item = Mock()

        self.spawn_room = Mock()
        self.spawn_room.name = "Village Center"
        self.spawn_room.description = "The spawn room"

        self.game_state = Mock()
        self.game_state.get_room = Mock(
            side_effect=lambda rid: (
                self.current_room if rid == "room1" else self.spawn_room
            )
        )

        self.player_manager = Mock()
        self.player_manager.spawn_room = "spawn_room"
        self.player_manager.save_players = Mock()

        self.online_sessions = {"player_sid": {"player": self.player}}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_handle_player_defeat_by_mob_ends_combat(self):
        """Test player defeat by mob ends combat."""
        from commands.combat import handle_player_defeat_by_mob

        active_combats[self.mob.id] = {"target": self.player}
        active_combats[self.player.name] = {"target": self.mob}

        await handle_player_defeat_by_mob(
            self.mob,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Combat should be ended
        self.assertNotIn(self.mob.id, active_combats)
        self.assertNotIn(self.player.name, active_combats)
        self.assertIsNone(self.mob.target_player)

    async def test_handle_player_defeat_by_mob_awaits_respawn(self):
        """Test player defeat by mob awaits respawn choice."""
        from commands.combat import handle_player_defeat_by_mob

        await handle_player_defeat_by_mob(
            self.mob,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should NOT immediately respawn (awaits player choice)
        self.player.set_current_room.assert_not_called()
        # Should send prompt for respawn choice
        self.utils.send_message.assert_called()


class HandleMobDefeatTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_mob_defeat function."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Player1"
        self.player.add_points = Mock(return_value=(False, ""))

        self.mob = Mock(spec=Mobile)
        self.mob.id = "goblin_1"
        self.mob.name = "goblin"
        self.mob.current_room = "room1"
        self.mob.point_value = 50
        self.mob.target_player = self.player
        self.mob.drop_loot = Mock(return_value=[])

        self.current_room = Mock()
        self.current_room.add_item = Mock()

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.current_room)

        self.player_manager = Mock()
        self.player_manager.save_players = Mock()

        self.mob_manager = Mock()
        self.mob_manager.remove_mob = Mock()

        self.online_sessions = {"player_sid": {"player": self.player}}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_handle_mob_defeat_awards_points(self):
        """Test mob defeat awards points to player."""
        from commands.combat import handle_mob_defeat

        active_combats[self.player.name] = {"target": self.mob}
        active_combats[self.mob.id] = {"target": self.player}

        await handle_mob_defeat(
            self.player,
            self.mob,
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.mob_manager,
            self.sio,
            self.utils,
        )

        # Should award points
        self.player.add_points.assert_called_with(
            50, self.sio, self.online_sessions, send_notification=True
        )

    async def test_handle_mob_defeat_drops_loot(self):
        """Test mob defeat drops loot."""
        from commands.combat import handle_mob_defeat

        loot_item = Item(name="gold coin", id="coin_1", description="A coin")
        self.mob.drop_loot = Mock(return_value=[loot_item])

        active_combats[self.player.name] = {"target": self.mob}
        active_combats[self.mob.id] = {"target": self.player}

        await handle_mob_defeat(
            self.player,
            self.mob,
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.mob_manager,
            self.sio,
            self.utils,
        )

        # Should add loot to room
        self.current_room.add_item.assert_called_with(loot_item)

    async def test_handle_mob_defeat_removes_mob(self):
        """Test mob defeat removes mob from game."""
        from commands.combat import handle_mob_defeat

        active_combats[self.player.name] = {"target": self.mob}
        active_combats[self.mob.id] = {"target": self.player}

        await handle_mob_defeat(
            self.player,
            self.mob,
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.mob_manager,
            self.sio,
            self.utils,
        )

        # Should remove mob
        self.mob_manager.remove_mob.assert_called_with(self.mob.id, self.game_state)


class ProcessMobCombatAttackTest(unittest.IsolatedAsyncioTestCase):
    """Test process_mob_combat_attack function."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Player1"
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.strength = 50
        self.player.dexterity = 50
        self.player.stamina = 100
        self.player.get_effective_dexterity = (
            lambda *args, **kwargs: self.player.dexterity
        )

        self.mob = Mock(spec=Mobile)
        self.mob.id = "goblin_1"
        self.mob.name = "goblin"
        self.mob.damage = 10
        self.mob.dexterity = 40
        self.mob.take_damage = Mock(return_value=(False, 80))
        self.mob.get_effective_dexterity = lambda *args, **kwargs: self.mob.dexterity

        self.weapon = Item(name="sword", id="sword_1", description="A sword")
        self.weapon.damage = 10

        self.game_state = Mock()
        self.player_manager = Mock()
        self.mob_manager = Mock()
        self.online_sessions = {"player_sid": {"player": self.player}}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_process_mob_combat_attack_player_hits_mob(self):
        """Test player hitting mob."""
        from commands.combat import process_mob_combat_attack

        self.player.inventory = [self.weapon]

        with patch("random.randint", return_value=50):
            with patch("random.uniform", return_value=1.0):
                await process_mob_combat_attack(
                    self.player,
                    self.mob,
                    self.weapon,
                    "player_sid",
                    self.player_manager,
                    self.game_state,
                    self.online_sessions,
                    self.mob_manager,
                    self.sio,
                    self.utils,
                )

        # Should deal damage
        self.mob.take_damage.assert_called()
        self.utils.send_message.assert_called()

    async def test_process_mob_combat_attack_mob_hits_player(self):
        """Test mob hitting player."""
        from commands.combat import process_mob_combat_attack

        with patch("random.randint", return_value=50):
            with patch("random.uniform", return_value=1.0):
                await process_mob_combat_attack(
                    self.mob,
                    self.player,
                    None,
                    "player_sid",
                    self.player_manager,
                    self.game_state,
                    self.online_sessions,
                    self.mob_manager,
                    self.sio,
                    self.utils,
                )

        # Should send hit message
        self.utils.send_message.assert_called()

    async def test_process_mob_combat_attack_miss(self):
        """Test combat attack missing."""
        from commands.combat import process_mob_combat_attack

        # Force miss
        with patch("random.randint", return_value=1):
            with patch("random.uniform", return_value=1.0):
                await process_mob_combat_attack(
                    self.player,
                    self.mob,
                    None,
                    "player_sid",
                    self.player_manager,
                    self.game_state,
                    self.online_sessions,
                    self.mob_manager,
                    self.sio,
                    self.utils,
                )

        # Should send message
        self.assertTrue(self.utils.send_message.called)

    async def test_process_mob_combat_attack_weapon_not_in_inventory(self):
        """Test mob combat when weapon not in inventory."""
        from commands.combat import process_mob_combat_attack

        # Weapon not in inventory
        self.player.inventory = []
        active_combats[self.player.name] = {"weapon": self.weapon}

        with patch("random.randint", return_value=50):
            with patch("random.uniform", return_value=1.0):
                await process_mob_combat_attack(
                    self.player,
                    self.mob,
                    self.weapon,
                    "player_sid",
                    self.player_manager,
                    self.game_state,
                    self.online_sessions,
                    self.mob_manager,
                    self.sio,
                    self.utils,
                )

        # Weapon should be set to None in combat
        self.assertIsNone(active_combats[self.player.name]["weapon"])


class MobInitiateAttackTest(unittest.IsolatedAsyncioTestCase):
    """Test mob_initiate_attack function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mob = Mock(spec=Mobile)
        self.mob.id = "goblin_1"
        self.mob.name = "goblin"
        self.mob.target_player = None

        self.player = Mock()
        self.player.name = "Player1"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.online_sessions = {"player_sid": {"player": self.player}}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

        active_combats.clear()

    async def test_mob_initiate_attack_starts_combat(self):
        """Test mob initiating attack starts combat."""
        from commands.combat import mob_initiate_attack

        with patch("commands.combat.process_mob_combat_attack", new_callable=AsyncMock):
            await mob_initiate_attack(
                self.mob,
                self.player,
                "player_sid",
                self.player_manager,
                self.game_state,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        # Should start combat
        self.assertIn(self.mob.id, active_combats)
        self.assertIn(self.player.name, active_combats)
        self.assertEqual(self.mob.target_player, self.player)

    async def test_mob_initiate_attack_skips_if_already_in_combat(self):
        """Test mob doesn't initiate if already in combat."""
        from commands.combat import mob_initiate_attack

        # Already in combat
        active_combats[self.mob.id] = {"target": self.player}

        with patch(
            "commands.combat.process_mob_combat_attack", new_callable=AsyncMock
        ) as mock_attack:
            await mob_initiate_attack(
                self.mob,
                self.player,
                "player_sid",
                self.player_manager,
                self.game_state,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        # Should not process attack
        mock_attack.assert_not_called()


class AdvancedCombatDisconnectTest(unittest.IsolatedAsyncioTestCase):
    """Test advanced combat disconnect scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Player1"
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.points = 1000
        self.player.add_points = Mock(return_value=(False, ""))
        self.player.remove_item = Mock()

        self.opponent = Mock()
        self.opponent.name = "Opponent"
        self.opponent.add_points = Mock(return_value=(False, ""))

        self.current_room = Mock()
        self.current_room.add_item = Mock()

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.current_room)

        self.player_manager = Mock()
        self.player_manager.save_players = Mock()

        self.online_sessions = {
            "player_sid": {"player": self.player},
            "opponent_sid": {"player": self.opponent},
        }
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_combat_disconnect_with_player_object(self):
        """Test disconnect with player object present."""
        from commands.combat import handle_combat_disconnect

        active_combats[self.player.name] = {
            "target": self.opponent,
            "target_sid": "opponent_sid",
        }
        active_combats[self.opponent.name] = {
            "target": self.player,
            "target_sid": "player_sid",
        }

        item = Item(name="sword", id="sword_1", description="A sword")
        self.player.inventory = [item]

        await handle_combat_disconnect(
            self.player.name,
            self.online_sessions,
            self.player_manager,
            self.game_state,
            self.sio,
            self.utils,
        )

        # Should drop items
        self.player.remove_item.assert_called()
        # Should lose points
        self.player.add_points.assert_called()
        # Combat should end
        self.assertNotIn(self.player.name, active_combats)


class AttackFindingPlayerByNameTest(unittest.IsolatedAsyncioTestCase):
    """Test attacking player found by name."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Attacker"
        self.player.current_room = "room1"
        self.player.inventory = []

        self.target = Mock()
        self.target.name = "Target"
        self.target.current_room = "room1"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()
        self.utils.mob_manager = Mock()
        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[])

        self.online_sessions = {
            "attacker_sid": {"player": self.player},
            "target_sid": {"player": self.target},
        }

        active_combats.clear()

    async def test_attack_finds_player_by_name(self):
        """Test attacking player found by name in online_sessions."""
        cmd = {
            "verb": "attack",
            "subject": "Target",
            "subject_object": None,
            "instrument": None,
            "instrument_object": None,
        }

        with patch("commands.combat.process_combat_attack", new_callable=AsyncMock):
            result = await handle_attack(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        # Should start combat
        self.assertIn(self.player.name, active_combats)
        self.assertIn("attack", result.lower())


class AttackMobByNameTest(unittest.IsolatedAsyncioTestCase):
    """Test attacking mob found by name."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Player1"
        self.player.current_room = "room1"
        self.player.inventory = []

        self.mob = Mock(spec=Mobile)
        self.mob.id = "goblin_1"
        self.mob.name = "goblin"
        self.mob.is_mob = True
        self.mob.target_player = None

        self.game_state = Mock()
        self.player_manager = Mock()
        self.mob_manager = Mock()
        self.mob_manager.get_mobs_in_room = Mock(return_value=[self.mob])

        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.mob_manager = self.mob_manager

        self.online_sessions = {"player_sid": {"player": self.player}}

        active_combats.clear()

    async def test_attack_mob_by_name(self):
        """Test attacking mob found by name."""
        cmd = {
            "verb": "attack",
            "subject": "goblin",
            "subject_object": None,
            "instrument": None,
            "instrument_object": None,
        }

        with patch(
            "commands.combat.handle_mob_attack", new_callable=AsyncMock
        ) as mock_mob_attack:
            mock_mob_attack.return_value = "You attack goblin!"

            await handle_attack(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        # Should call handle_mob_attack
        mock_mob_attack.assert_called_once()

    async def test_attack_mob_already_in_combat(self):
        """Test attacking mob when already in combat."""
        active_combats[self.player.name] = {
            "target": Mock(),
            "target_sid": None,
            "is_mob": False,
        }

        cmd = {
            "verb": "attack",
            "subject": "goblin",
            "subject_object": None,
            "instrument": None,
            "instrument_object": None,
        }

        with patch("commands.combat.handle_mob_attack", new_callable=AsyncMock):
            result = await handle_attack(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

        # Should not attack, already in combat
        self.assertIn("already", result.lower())


class RetaliateByWeaponNameTest(unittest.IsolatedAsyncioTestCase):
    """Test retaliate finding weapon by name."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "Player1"
        self.player.inventory = []

        self.weapon = Item(name="iron sword", id="sword_1", description="A sword")
        self.weapon.damage = 10

        self.target = Mock()
        self.target.name = "Target"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

        self.online_sessions = {}

        active_combats.clear()

    async def test_retaliate_finds_weapon_by_name(self):
        """Test retaliate finds weapon by name in inventory."""
        self.player.inventory = [self.weapon]
        active_combats[self.player.name] = {
            "target": self.target,
            "target_sid": "target_sid",
            "weapon": None,
        }

        cmd = {"verb": "retaliate", "instrument": "sword", "instrument_object": None}

        result = await handle_retaliate(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should equip weapon
        self.assertEqual(active_combats[self.player.name]["weapon"], self.weapon)
        self.assertIn("ready", result.lower())


class ResetPlayerPersonaTest(unittest.TestCase):
    """Test reset_player_persona function."""

    def test_reset_player_persona_resets_to_neophyte(self):
        """Test resetting player persona to neophyte state."""
        from commands.combat import reset_player_persona

        player = Mock()
        player.points = 10000
        player.level = "Sorcerer"

        reset_player_persona(player)

        # Should reset to level 0
        self.assertEqual(player.points, 0)
        self.assertEqual(player.level, "Neophyte")
        self.assertEqual(player.current_level_at, 0)
        self.assertEqual(player.next_level_at, 400)


class HandleRespawnChoiceTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_respawn_choice function."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.points = 5000
        self.player.level = "Warrior"
        self.player.max_stamina = 100
        self.player.stamina = 50
        self.player.set_current_room = Mock()
        self.player.visited = set()

        self.game_state = Mock()
        self.spawn_room = Mock()
        self.spawn_room.name = "Village Center"
        self.spawn_room.description = "The center of the village"
        self.spawn_room.room_id = "village_center"
        self.spawn_room.exits = {}
        self.spawn_room.get_items = Mock(return_value=[])
        self.game_state.get_room = Mock(return_value=self.spawn_room)

        self.player_manager = Mock()
        self.player_manager.spawn_room = "village_center"
        self.player_manager.save_players = Mock()

        self.online_sessions = {"player_sid": {"player": self.player}}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()
        self.utils.mob_manager = None

    async def test_respawn_choice_yes_combat_death(self):
        """Test respawn choice 'yes' for combat death."""
        from commands.combat import handle_respawn_choice

        self.online_sessions["player_sid"]["awaiting_respawn"] = True

        result = await handle_respawn_choice(
            self.player,
            "yes",
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            combat_death=True,
        )

        # Should reset persona and respawn
        self.assertEqual(self.player.points, 0)
        self.assertEqual(self.player.level, "Neophyte")
        self.player.set_current_room.assert_called_with("village_center")
        self.assertEqual(self.player.stamina, 45)  # Neophyte level stamina
        self.assertFalse(self.online_sessions["player_sid"]["awaiting_respawn"])
        self.player_manager.save_players.assert_called_once()
        self.utils.send_message.assert_called()
        self.assertIsNotNone(result)

    async def test_respawn_choice_y_combat_death(self):
        """Test respawn choice 'y' (short form) for combat death."""
        from commands.combat import handle_respawn_choice

        self.online_sessions["player_sid"]["awaiting_respawn"] = True

        result = await handle_respawn_choice(
            self.player,
            "y",
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            combat_death=True,
        )

        # Should reset persona
        self.assertEqual(self.player.points, 0)
        self.assertIsNotNone(result)

    async def test_respawn_choice_yes_non_combat_death(self):
        """Test respawn choice 'yes' for non-combat death."""
        from commands.combat import handle_respawn_choice

        initial_points = self.player.points
        initial_level = self.player.level

        result = await handle_respawn_choice(
            self.player,
            "yes",
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            combat_death=False,
        )

        # Should NOT reset persona
        self.assertEqual(self.player.points, initial_points)
        self.assertEqual(self.player.level, initial_level)
        # But should respawn
        self.player.set_current_room.assert_called_with("village_center")
        self.assertIsNotNone(result)

    async def test_respawn_choice_no(self):
        """Test respawn choice 'no' disconnects player."""
        from commands.combat import handle_respawn_choice

        self.online_sessions["player_sid"]["awaiting_respawn"] = True

        result = await handle_respawn_choice(
            self.player,
            "no",
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            combat_death=True,
        )

        # Should disconnect
        self.assertIsNone(result)
        self.assertFalse(self.online_sessions["player_sid"]["awaiting_respawn"])
        # Should send farewell message
        self.utils.send_message.assert_called_with(
            self.sio, "player_sid", "Your persona has been deleted."
        )


class HandleNonCombatDeathTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_non_combat_death function."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.remove_item = Mock()

        self.current_room = Mock()
        self.current_room.add_item = Mock()

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.current_room)

        self.player_manager = Mock()
        self.online_sessions = {"player_sid": {"player": self.player}}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_handle_non_combat_death_sets_flags(self):
        """Test non-combat death sets correct flags."""
        from commands.combat import handle_non_combat_death

        await handle_non_combat_death(
            self.player,
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should set awaiting_respawn flag and put player in limbo
        self.assertTrue(self.online_sessions["player_sid"]["awaiting_respawn"])
        # Should set combat_death to False
        self.assertFalse(self.online_sessions["player_sid"]["combat_death"])
        self.assertIsNone(self.player.current_room)  # Player in limbo

    async def test_handle_non_combat_death_correct_message(self):
        """Test non-combat death sends correct message."""
        from commands.combat import handle_non_combat_death

        await handle_non_combat_death(
            self.player,
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should send "Persona updated" message
        calls = self.utils.send_message.call_args_list
        message_sent = str(calls[0])
        self.assertIn("Persona updated", message_sent)

    async def test_handle_non_combat_death_drops_items(self):
        """Test non-combat death drops all items."""
        from commands.combat import handle_non_combat_death

        item1 = Item(name="sword", id="sword_1", description="A sword")
        item2 = Item(name="shield", id="shield_1", description="A shield")
        self.player.inventory = [item1, item2]

        await handle_non_combat_death(
            self.player,
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should drop all items
        self.assertEqual(self.player.remove_item.call_count, 2)
        self.assertEqual(self.current_room.add_item.call_count, 2)


class UpdatedPlayerDefeatTest(unittest.IsolatedAsyncioTestCase):
    """Test updated handle_player_defeat function."""

    def setUp(self):
        """Set up test fixtures."""
        self.attacker = Mock()
        self.attacker.name = "Attacker"
        self.attacker.points = 1000
        self.attacker.add_points = Mock(return_value=(False, ""))

        self.defender = Mock()
        self.defender.name = "Defender"
        self.defender.current_room = "room1"
        self.defender.points = 500
        self.defender.inventory = []
        self.defender.remove_item = Mock()

        self.current_room = Mock()
        self.current_room.add_item = Mock()

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.current_room)

        self.player_manager = Mock()
        self.player_manager.save_players = Mock()

        self.online_sessions = {
            "attacker_sid": {"player": self.attacker},
            "defender_sid": {"player": self.defender},
        }
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()

        active_combats.clear()

    async def test_player_defeat_sets_awaiting_respawn(self):
        """Test player defeat sets awaiting_respawn flag."""
        from commands.combat import handle_player_defeat

        await handle_player_defeat(
            self.attacker,
            self.defender,
            "defender_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should set awaiting_respawn and put player in limbo
        self.assertTrue(self.online_sessions["defender_sid"]["awaiting_respawn"])
        self.assertTrue(self.online_sessions["defender_sid"]["combat_death"])
        self.assertIsNone(self.defender.current_room)  # Player in limbo

    async def test_player_defeat_sends_persona_reset_message(self):
        """Test player defeat sends 'Persona reset' message."""
        from commands.combat import handle_player_defeat

        await handle_player_defeat(
            self.attacker,
            self.defender,
            "defender_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should send message with "Persona reset"
        calls = [str(call) for call in self.utils.send_message.call_args_list]
        defender_messages = [c for c in calls if "defender_sid" in c]
        self.assertTrue(any("Persona reset" in msg for msg in defender_messages))


class UpdatedMobDefeatPlayerTest(unittest.IsolatedAsyncioTestCase):
    """Test updated handle_player_defeat_by_mob function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mob = Mock(spec=Mobile)
        self.mob.id = "goblin_1"
        self.mob.name = "goblin"
        self.mob.target_player = None

        self.player = Mock()
        self.player.name = "Player1"
        self.player.current_room = "room1"
        self.player.inventory = []
        self.player.remove_item = Mock()

        self.current_room = Mock()
        self.current_room.add_item = Mock()

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.current_room)

        self.player_manager = Mock()
        self.online_sessions = {"player_sid": {"player": self.player}}
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

        active_combats.clear()

    async def test_mob_defeat_player_sets_awaiting_respawn(self):
        """Test mob defeating player sets awaiting_respawn flag."""
        from commands.combat import handle_player_defeat_by_mob

        await handle_player_defeat_by_mob(
            self.mob,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should set awaiting_respawn and put player in limbo
        self.assertTrue(self.online_sessions["player_sid"]["awaiting_respawn"])
        self.assertTrue(self.online_sessions["player_sid"]["combat_death"])
        self.assertIsNone(self.player.current_room)  # Player in limbo

    async def test_mob_defeat_player_sends_persona_reset_message(self):
        """Test mob defeating player sends 'Persona reset' message."""
        from commands.combat import handle_player_defeat_by_mob

        await handle_player_defeat_by_mob(
            self.mob,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # Should send message with "Persona reset"
        calls = [str(call) for call in self.utils.send_message.call_args_list]
        self.assertTrue(any("Persona reset" in msg for msg in calls))


class RespawnIssuesTest(unittest.IsolatedAsyncioTestCase):
    """Test for respawn issues that need to be fixed."""

    def setUp(self):
        """Set up test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.points = 5000
        self.player.level = "Warrior"
        self.player.max_stamina = 100
        self.player.stamina = 50
        self.player.current_room = None

        # Make set_current_room actually update the attribute
        def set_room(room_id):
            self.player.current_room = room_id

        self.player.set_current_room = Mock(side_effect=set_room)
        self.player.visited = set()

        self.other_player = Mock()
        self.other_player.name = "OtherPlayer"
        self.other_player.current_room = "village_center"
        self.other_player.level = "Acolyte"
        self.other_player.inventory = []

        self.spawn_room = Mock()
        self.spawn_room.name = "Village Center"
        self.spawn_room.description = "The center of the village"
        self.spawn_room.room_id = "village_center"
        self.spawn_room.exits = {"north": "room2"}
        self.spawn_room.get_items = Mock(return_value=[])

        self.game_state = Mock()
        self.game_state.get_room = Mock(return_value=self.spawn_room)

        self.player_manager = Mock()
        self.player_manager.spawn_room = "village_center"
        self.player_manager.save_players = Mock()

        self.online_sessions = {
            "player_sid": {"player": self.player},
            "other_sid": {"player": self.other_player},
        }
        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()
        self.utils.mob_manager = None

    async def test_respawn_does_not_return_success_message(self):
        """Test respawn choice 'yes' does not return 'Respawned successfully'."""
        from commands.combat import handle_respawn_choice

        self.online_sessions["player_sid"]["awaiting_respawn"] = True

        result = await handle_respawn_choice(
            self.player,
            "yes",
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            combat_death=True,
        )

        # Should NOT return "Respawned successfully"
        if result:
            self.assertNotIn("Respawned successfully", result)

    async def test_respawn_shows_other_players_at_spawn(self):
        """Test respawn shows other players in the spawn room description."""
        from commands.combat import handle_respawn_choice

        self.online_sessions["player_sid"]["awaiting_respawn"] = True

        await handle_respawn_choice(
            self.player,
            "yes",
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            combat_death=True,
        )

        # Check the welcome message sent to player
        calls = [str(call) for call in self.utils.send_message.call_args_list]
        welcome_messages = [
            c for c in calls if "player_sid" in c and "awaken" in c.lower()
        ]

        # Should show other player in description
        has_other_player = any("OtherPlayer" in msg for msg in welcome_messages)
        self.assertTrue(
            has_other_player, "Room description should include other players at spawn"
        )

    async def test_awaiting_respawn_player_not_in_who_list(self):
        """Test player awaiting respawn is not shown in 'who' command."""
        from commands.standard import handle_users

        # Player is awaiting respawn
        self.online_sessions["player_sid"]["awaiting_respawn"] = True
        self.player.current_room = None  # Player in limbo

        cmd = {"verb": "users"}

        result = await handle_users(
            cmd,
            self.other_player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        # TestPlayer should NOT be in the list (they're dead/awaiting respawn)
        self.assertNotIn("TestPlayer", result)
        # OtherPlayer should still be in the list
        self.assertIn("OtherPlayer", result)

    async def test_respawn_broadcasts_arrival_message(self):
        """Test respawn broadcasts arrival message to players at spawn."""
        from commands.combat import handle_respawn_choice
        from services.notifications import set_context

        # Set up notification context
        async def wrapped_send_message(sid, message):
            await self.utils.send_message(self.sio, sid, message)

        set_context(self.online_sessions, wrapped_send_message)

        self.online_sessions["player_sid"]["awaiting_respawn"] = True

        await handle_respawn_choice(
            self.player,
            "yes",
            "player_sid",
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            combat_death=True,
        )

        # Check messages sent to OTHER players
        # The send_message mock is called as: send_message(sio, sid, message)
        # So we need to check call_args for each call
        other_player_received_messages = []
        for call in self.utils.send_message.call_args_list:
            args, kwargs = call
            if len(args) >= 3:
                sid = args[1]
                message = args[2]
                if sid == "other_sid":
                    other_player_received_messages.append(message)

        # Other player should receive arrival notification
        has_arrival = any(
            "TestPlayer" in msg and "arrived" in msg.lower()
            for msg in other_player_received_messages
        )
        self.assertTrue(
            has_arrival,
            f"Other players at spawn should see arrival message. Messages: {other_player_received_messages}",
        )


if __name__ == "__main__":
    unittest.main()
