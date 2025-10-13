import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.combat import (
    active_combats,
    handle_attack,
    mob_initiate_attack,
)
from managers.mob_manager import MobManager
from models.Mobile import Mobile
from models.Player import Player


class _DummyRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.name = f"Room {room_id}"
        self.description = "A test room."
        self.items = []
        self.exits = {}

    def add_item(self, item):
        if item not in self.items:
            self.items.append(item)

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)


class _DummyGameState:
    def __init__(self, rooms):
        self._rooms = {room.room_id: room for room in rooms}

    def get_room(self, room_id):
        return self._rooms.get(room_id)


class _DummyPlayerManager:
    def __init__(self, spawn_room="room1"):
        self.spawn_room = spawn_room

    def save_players(self):
        return None


class _DummySio:
    def __init__(self):
        self.emits = []

    async def emit(self, event, payload, room=None):
        self.emits.append((event, payload, room))


class _RecordingUtils:
    def __init__(self, mob_manager):
        self.mob_manager = mob_manager
        self.messages = []
        self.stats_updates = []

    async def send_message(self, sio, sid, message):
        self.messages.append((sid, message))

    async def send_stats_update(self, sio, sid, player):
        self.stats_updates.append(player)


class _DummyWeapon:
    def __init__(self, name="sword", damage=10):
        self.name = name
        self.damage = damage


class MobCombatBugsTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        active_combats.clear()

    async def asyncTearDown(self):
        active_combats.clear()

    @patch("commands.combat.random.uniform", return_value=1.0)
    @patch("commands.combat.random.randint", return_value=10)
    async def test_player_attacks_mob_after_mob_initiates(self, mock_randint, mock_uniform):
        """
        Test that when a mob initiates combat with a player, and the player
        then tries to attack the mob, they don't start duplicate combat.
        """
        player = Player("Stupidgem")
        player.current_room = "room1"

        weapon = _DummyWeapon("sword", 10)
        player.inventory.append(weapon)

        mob = Mobile("Elder", "elder_1", "An elder", current_room="room1")

        mob_manager = MobManager()
        mob_manager.mobs[mob.id] = mob
        utils = _RecordingUtils(mob_manager)
        game_state = _DummyGameState([_DummyRoom("room1")])
        player_manager = _DummyPlayerManager(spawn_room="room1")
        online_sessions = {"sid1": {"player": player}}
        sio = _DummySio()

        # Mob initiates combat first
        await mob_initiate_attack(mob, player, "sid1", player_manager, game_state, online_sessions, sio, utils)

        # Verify combat was initiated
        self.assertIn(mob.id, active_combats)
        self.assertIn(player.name, active_combats)

        # Clear messages from mob initiation
        utils.messages.clear()

        # Player tries to attack the mob (simulating the user's command)
        cmd = {
            "verb": "attack",
            "subject": "elder",
            "subject_object": mob,
            "instrument": "sword",
            "instrument_object": weapon
        }

        result = await handle_attack(cmd, player, game_state, player_manager, online_sessions, sio, utils)

        # Should not create duplicate combat - should inform player they're already fighting
        self.assertEqual(result, f"You're already fighting {mob.name}!")

        # Should NOT have any combat dialogue messages (PvP messages)
        message_texts = [msg for _sid, msg in utils.messages]
        self.assertFalse(any("attacks you" in msg for msg in message_texts),
                        "Should not show PvP 'attacks you' messages when already in combat")

    @patch("commands.combat.random.uniform", return_value=1.0)
    @patch("commands.combat.random.randint", return_value=10)
    async def test_aggressive_mob_attacks_then_player_attacks_back(self, mock_randint, mock_uniform):
        """
        Test the exact scenario from the bug report:
        1. Elder (aggressive mob) arrives in room
        2. Elder attacks player
        3. Player attacks Elder with sword
        Should NOT show duplicate/confused combat messages
        """
        player = Player("Stupidgem")
        player.current_room = "room1"

        weapon = _DummyWeapon("sword", 10)
        player.inventory.append(weapon)

        # Create aggressive mob
        mob = Mobile(
            "Elder",
            "elder_1",
            "An elder",
            current_room="room1",
            aggressive=True,
            aggro_delay_min=0,
            aggro_delay_max=0
        )
        mob.initialize_aggro_delay()
        mob.aggro_counter = 0  # Ready to attack immediately

        mob_manager = MobManager()
        mob_manager.mobs[mob.id] = mob
        utils = _RecordingUtils(mob_manager)
        game_state = _DummyGameState([_DummyRoom("room1")])
        player_manager = _DummyPlayerManager(spawn_room="room1")
        online_sessions = {"sid1": {"player": player}}
        sio = _DummySio()

        # Step 1: Mob attacks player (simulating mob tick aggression)
        self.assertTrue(mob.can_attack_player())
        await mob_initiate_attack(mob, player, "sid1", player_manager, game_state, online_sessions, sio, utils)

        # Verify combat established
        self.assertIn(mob.id, active_combats)
        self.assertIn(player.name, active_combats)

        # Step 2: Player tries to attack back
        utils.messages.clear()

        cmd = {
            "verb": "attack",
            "subject": "elder",
            "subject_object": mob,
            "instrument": "sword",
            "instrument_object": weapon
        }

        result = await handle_attack(cmd, player, game_state, player_manager, online_sessions, sio, utils)

        # Should inform player they're already in combat
        self.assertIn("already fighting", result.lower())

        # Should NOT receive own "attacks you" messages
        message_texts = [msg for _sid, msg in utils.messages]
        self.assertFalse(any(f"{player.name} attacks you" in msg for msg in message_texts),
                        "Player should not receive message saying they attack themselves")

    async def test_mob_cannot_move_during_combat(self):
        """
        Test that a mob in combat cannot move, even if its movement tick happens.
        """
        player = Player("Hero")
        player.current_room = "room1"

        # Create mob with patrol route
        mob = Mobile(
            "Elder",
            "elder_1",
            "An elder",
            current_room="room1",
            movement_interval=1,  # Would normally move every tick
            patrol_rooms=["room1", "room2"],
        )
        mob.last_move_tick = 0  # Ready to move

        mob_manager = MobManager()
        mob_manager.mobs[mob.id] = mob
        utils = _RecordingUtils(mob_manager)

        room1 = _DummyRoom("room1")
        room2 = _DummyRoom("room2")
        room1.exits = {"east": "room2"}
        room2.exits = {"west": "room1"}
        game_state = _DummyGameState([room1, room2])

        player_manager = _DummyPlayerManager()
        online_sessions = {"sid1": {"player": player}}
        sio = _DummySio()

        # Put mob in combat
        active_combats[mob.id] = {
            "target": player,
            "target_sid": "sid1",
            "weapon": None,
            "initiative": True,
            "last_turn": None,
            "is_mob": True,
            "entity": mob,
        }
        active_combats[player.name] = {
            "target": mob,
            "target_sid": None,
            "weapon": None,
            "initiative": False,
            "last_turn": None,
            "is_mob": False,
            "entity": player,
        }

        # Process mob tick - should NOT move
        await mob_manager.tick_all_mobs(
            sio,
            online_sessions,
            player_manager,
            game_state,
            utils,
        )

        # Mob should still be in room1
        self.assertEqual(mob.current_room, "room1")

        # Should not have any movement messages
        message_texts = [msg for _sid, msg in utils.messages]
        self.assertFalse(any("leaves" in msg or "arrives" in msg for msg in message_texts),
                        "Mob should not move during combat")


if __name__ == "__main__":
    unittest.main()
