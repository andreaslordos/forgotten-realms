import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.combat import (
    active_combats,
    handle_mob_attack,
    process_combat_tick,
    process_mob_combat_attack,
)
from managers.mob_manager import MobManager
from models.Mobile import Mobile
from models.Player import Player
from utils import send_stats_update


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


class UtilsGuardTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_send_stats_update_skips_mob_objects(self):
        sio = _DummySio()
        mob = Mobile("Elder", "elder_test", "An elder", current_room="room1")

        await send_stats_update(sio, "sid", mob)
        self.assertEqual(sio.emits, [])

        player = Player("Hero")
        await send_stats_update(sio, "sid", player)
        self.assertEqual(len(sio.emits), 1)
        event, payload, room = sio.emits[0]
        self.assertEqual(event, "statsUpdate")
        self.assertEqual(room, "sid")
        self.assertEqual(payload["name"], "Hero")


class MobBehaviorTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        active_combats.clear()

    async def asyncTearDown(self):
        active_combats.clear()

    @patch("commands.combat.random.uniform", return_value=1.0)
    @patch("commands.combat.random.randint", return_value=10)
    async def test_handle_mob_attack_reports_damage(self, mock_randint, mock_uniform):
        player = Player("Hero")
        player.current_room = "room1"

        mob = Mobile("Elder", "elder_1", "An elder", current_room="room1")

        mob_manager = MobManager()
        utils = _RecordingUtils(mob_manager)
        game_state = _DummyGameState([_DummyRoom("room1")])
        player_manager = _DummyPlayerManager(spawn_room="room1")
        online_sessions = {"sid1": {"player": player}}
        sio = _DummySio()

        result = await handle_mob_attack(
            player,
            mob,
            weapon=None,
            player_sid="sid1",
            player_manager=player_manager,
            game_state=game_state,
            online_sessions=online_sessions,
            mob_manager=mob_manager,
            sio=sio,
            utils=utils,
        )

        self.assertIn("You attack Elder", result)
        message_texts = [msg for _sid, msg in utils.messages]
        self.assertTrue(any("You strike Elder" in msg for msg in message_texts))
        self.assertTrue(all(hasattr(p, "points") for p in utils.stats_updates))

    async def test_mob_does_not_move_while_in_combat(self):
        mob_manager = MobManager()
        mob_manager.mobs.clear()

        mob = Mobile(
            "Elder",
            "elder_1",
            "An elder",
            current_room="room1",
            movement_interval=1,
            patrol_rooms=["room1", "room2"],
        )
        mob.last_move_tick = 0
        mob.target_player = None
        mob_manager.mobs[mob.id] = mob

        player = Player("Hero")
        player.current_room = "room1"

        room1 = _DummyRoom("room1")
        room2 = _DummyRoom("room2")
        room1.exits = {"east": "room2"}
        room2.exits = {"west": "room1"}
        game_state = _DummyGameState([room1, room2])

        online_sessions = {"sid1": {"player": player}}
        utils = _RecordingUtils(mob_manager)
        sio = _DummySio()
        player_manager = _DummyPlayerManager()

        active_combats[mob.id] = {
            "target": player,
            "target_sid": "sid1",
            "weapon": None,
            "initiative": True,
            "last_turn": None,
            "is_mob": True,
        }

        await mob_manager.tick_all_mobs(
            sio,
            online_sessions,
            player_manager,
            game_state,
            utils,
        )

        self.assertEqual(mob.current_room, "room1")

    @patch("commands.combat.random.uniform", return_value=1.0)
    @patch("commands.combat.random.randint", return_value=10)
    async def test_process_combat_tick_handles_missing_defender_entry(
        self, mock_randint, mock_uniform
    ):
        player = Player("Hero")
        player.current_room = "room1"

        mob = Mobile("Elder", "elder_1", "An elder", current_room="room1")

        mob_manager = MobManager()
        utils = _RecordingUtils(mob_manager)
        game_state = _DummyGameState([_DummyRoom("room1")])
        player_manager = _DummyPlayerManager(spawn_room="room1")
        online_sessions = {"sid1": {"player": player}}
        sio = _DummySio()

        await handle_mob_attack(
            player,
            mob,
            weapon=None,
            player_sid="sid1",
            player_manager=player_manager,
            game_state=game_state,
            online_sessions=online_sessions,
            mob_manager=mob_manager,
            sio=sio,
            utils=utils,
        )

        # Simulate a missing mob entry (regression scenario)
        active_combats.pop(mob.id, None)

        await process_combat_tick(
            sio,
            online_sessions,
            player_manager,
            game_state,
            utils,
            mob_manager=mob_manager,
        )

        # Combat state should be cleaned up (no ghost attacks)
        self.assertNotIn(player.name, active_combats)
        self.assertNotIn(mob.id, active_combats)

    @patch("commands.combat.random.uniform", return_value=1.0)
    @patch("commands.combat.random.randint", side_effect=[10, 10, 10])
    async def test_killing_mob_cleans_up_combat_state(self, mock_randint, mock_uniform):
        player = Player("Hero")
        player.current_room = "room1"

        mob = Mobile(
            "Elder",
            "elder_cleanup",
            "An elder",
            current_room="room1",
            max_stamina=5,
            damage=1,
        )

        mob_manager = MobManager()
        mob_manager.mobs[mob.id] = mob
        utils = _RecordingUtils(mob_manager)
        game_state = _DummyGameState([_DummyRoom("room1")])
        player_manager = _DummyPlayerManager(spawn_room="room1")
        online_sessions = {"sid1": {"player": player}}
        sio = _DummySio()

        await handle_mob_attack(
            player,
            mob,
            weapon=None,
            player_sid="sid1",
            player_manager=player_manager,
            game_state=game_state,
            online_sessions=online_sessions,
            mob_manager=mob_manager,
            sio=sio,
            utils=utils,
        )

        await process_mob_combat_attack(
            player,
            mob,
            None,
            "sid1",
            player_manager,
            game_state,
            online_sessions,
            mob_manager,
            sio,
            utils,
        )

        self.assertNotIn(player.name, active_combats)
        self.assertNotIn(mob.id, active_combats)
        self.assertNotIn(mob.id, mob_manager.mobs)

    @patch("commands.combat.random.uniform", return_value=1.0)
    @patch("commands.combat.random.randint", return_value=10)
    async def test_dead_mob_entries_removed_on_subsequent_ticks(
        self, mock_randint, mock_uniform
    ):
        player = Player("Hero")
        player.current_room = "room1"

        mob = Mobile(
            "Elder",
            "elder_cleanup_tick",
            "An elder",
            current_room="room1",
            max_stamina=5,
        )

        mob_manager = MobManager()
        mob_manager.mobs[mob.id] = mob
        utils = _RecordingUtils(mob_manager)
        game_state = _DummyGameState([_DummyRoom("room1")])
        player_manager = _DummyPlayerManager(spawn_room="room1")
        online_sessions = {"sid1": {"player": player}}
        sio = _DummySio()

        class _TempWeapon:
            def __init__(self):
                self.name = "test blade"
                self.damage = 50

        weapon = _TempWeapon()
        player.inventory.append(weapon)

        await handle_mob_attack(
            player,
            mob,
            weapon,
            player_sid="sid1",
            player_manager=player_manager,
            game_state=game_state,
            online_sessions=online_sessions,
            mob_manager=mob_manager,
            sio=sio,
            utils=utils,
        )

        mob.stamina = 0
        mob.state = "dead"

        await process_combat_tick(
            sio,
            online_sessions,
            player_manager,
            game_state,
            utils,
            mob_manager=mob_manager,
        )

        self.assertNotIn(player.name, active_combats)
        self.assertNotIn(mob.id, active_combats)
        self.assertNotIn(mob.id, mob_manager.mobs)

        # Ensure a subsequent tick with a stale entry still performs cleanup and does not re-add
        active_combats[mob.id] = {
            "entity": mob,
            "target": player,
            "initiative": True,
            "is_mob": True,
        }

        await process_combat_tick(
            sio,
            online_sessions,
            player_manager,
            game_state,
            utils,
            mob_manager=mob_manager,
        )

        self.assertNotIn(mob.id, active_combats)


if __name__ == "__main__":
    unittest.main()
