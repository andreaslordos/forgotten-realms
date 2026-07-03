# backend/services/tests/test_golden_doors.py
"""Tests for golden doors: riddle gate, key gate, and dimension opening."""

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import utils as utils_module
import services.notifications as notifications
from managers.game_state import GameState
from managers.mob_definitions import get_mob_definitions
from managers.mob_manager import MobManager
from models.Item import Item
from models.Player import Player
from models.Room import Room
from services.golden_doors import (
    DOOR_REGISTRY,
    FAILURE_BROADCAST,
    GOLDEN_KEY_ID,
    OPEN_BROADCAST,
    OPENING_MESSAGE,
    _generate_and_open,
    create_golden_door,
    make_open_effect,
    reset_doors,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "storage"
    / "fallback_zones"
    / "hollow_reliquary.json"
)


def load_fixture():
    """Load the shipped fallback zone spec from disk."""
    with open(FIXTURE_PATH) as f:
        return json.load(f)


def make_fake_generator(spec=None, side_effect=None, available=True):
    """Build a fake ZoneGenerator that never touches the network."""
    generator = Mock()
    generator.is_available = Mock(return_value=available)
    generator.generate_zone_spec = AsyncMock(return_value=spec, side_effect=side_effect)
    return generator


class GoldenDoorTestBase(unittest.IsolatedAsyncioTestCase):
    """Shared world, notification context and mob manager for door tests."""

    def setUp(self):
        """Set up a door room, a player session, and a real mob manager."""
        reset_doors()
        self.game_state = GameState()
        self.room = Room("crypt", "Crypt", "A cold crypt.")
        self.game_state.add_room(self.room)
        self.player = Player("Tester")
        self.player.set_current_room("crypt")

        # Route broadcasts to a mock so they don't warn (and can be asserted).
        self._old_sessions = notifications.SESSIONS
        self._old_send = notifications.send_msg
        self.send_message = AsyncMock()
        notifications.set_context({"sid1": {"player": self.player}}, self.send_message)

        # _try_open reads utils.mob_manager; give it a real one.
        self._had_mob_manager = hasattr(utils_module, "mob_manager")
        self._old_mob_manager = getattr(utils_module, "mob_manager", None)
        self.mob_manager = MobManager()
        self.mob_manager.load_mob_definitions(get_mob_definitions())
        utils_module.mob_manager = self.mob_manager

    def tearDown(self):
        """Restore globals mutated in setUp."""
        reset_doors()
        notifications.SESSIONS = self._old_sessions
        notifications.send_msg = self._old_send
        if self._had_mob_manager:
            utils_module.mob_manager = self._old_mob_manager
        elif hasattr(utils_module, "mob_manager"):
            del utils_module.mob_manager

    def _create_door(self, generator_factory=None):
        return create_golden_door(
            "t",
            self.room,
            theme_hint="a test dimension",
            riddle_text="'NAME ME.'",
            riddle_answer="Echo",
            generator_factory=generator_factory,
        )

    def _give_key(self):
        key = Item("golden key", GOLDEN_KEY_ID, "A golden key.", weight=1, value=0)
        self.player.add_item(key)
        return key

    async def _drain_tasks(self):
        """Wait for every background task spawned during the test."""
        tasks = [
            task for task in asyncio.all_tasks() if task is not asyncio.current_task()
        ]
        if tasks:
            await asyncio.gather(*tasks)


class CreateGoldenDoorTest(GoldenDoorTestBase):
    """Test create_golden_door wiring: registry, item, riddle trigger."""

    async def test_create_golden_door_registers_state(self):
        """Test the door registers a sealed state with a lowered answer."""
        # Act
        self._create_door()

        # Assert
        state = DOOR_REGISTRY["t"]
        self.assertEqual(state.room_id, "crypt")
        self.assertEqual(state.status, "sealed")
        self.assertEqual(state.riddle_answer, "echo")
        self.assertFalse(state.riddle_spoken)

    async def test_create_golden_door_adds_door_item_to_room(self):
        """Test the door StatefulItem is placed in the room."""
        # Act
        door = self._create_door()

        # Assert
        self.assertIn(door, self.room.items)
        self.assertEqual(door.id, "golden_door_t")
        self.assertEqual(door.get_state(), "sealed")
        self.assertIs(DOOR_REGISTRY["t"].door_item, door)

    async def test_create_golden_door_adds_riddle_speech_trigger(self):
        """Test speaking the riddle answer is wired as a room trigger."""
        # Act
        self._create_door()

        # Assert
        self.assertIn("echo", self.room.speech_triggers)
        trigger = self.room.speech_triggers["echo"][0]
        self.assertFalse(trigger["one_time"])
        self.assertIsNotNone(trigger["effect_fn"])
        self.assertIsNotNone(trigger["conditional_fn"])

    async def test_create_golden_door_open_requires_key_and_riddle(self):
        """Test the opening interaction needs golden_key and the riddle."""
        # Act
        door = self._create_door()

        # Assert
        opening = door.interactions["open"][0]
        self.assertEqual(opening["required_instrument"], GOLDEN_KEY_ID)
        self.assertEqual(opening["from_state"], "sealed")
        self.assertEqual(opening["target_state"], "opening")
        self.assertIn("conditional_fn", opening)
        self.assertIn("effect_fn", opening)

    async def test_create_golden_door_open_conditional_tracks_riddle(self):
        """Test the open conditional only passes once the riddle is spoken."""
        # Arrange
        door = self._create_door()
        conditional = door.interactions["open"][0]["conditional_fn"]

        # Act / Assert
        self.assertFalse(conditional(self.player, self.game_state))
        DOOR_REGISTRY["t"].riddle_spoken = True
        self.assertTrue(conditional(self.player, self.game_state))


class RiddleSpeechTriggerTest(GoldenDoorTestBase):
    """Test the riddle speech trigger's conditional and effect."""

    async def test_riddle_effect_sets_riddle_spoken(self):
        """Test invoking the trigger effect marks the riddle as spoken."""
        # Arrange
        self._create_door()
        trigger = self.room.speech_triggers["echo"][0]
        self.assertTrue(trigger["conditional_fn"](self.player, self.game_state))

        # Act
        await trigger["effect_fn"](self.player, self.game_state, None, {}, None, None)

        # Assert
        self.assertTrue(DOOR_REGISTRY["t"].riddle_spoken)

    async def test_riddle_conditional_false_after_spoken(self):
        """Test the trigger conditional stops firing once already spoken."""
        # Arrange
        self._create_door()
        DOOR_REGISTRY["t"].riddle_spoken = True
        trigger = self.room.speech_triggers["echo"][0]

        # Act / Assert
        self.assertFalse(trigger["conditional_fn"](self.player, self.game_state))

    async def test_riddle_conditional_false_when_not_sealed(self):
        """Test the trigger conditional stops firing once the door opens."""
        # Arrange
        self._create_door()
        DOOR_REGISTRY["t"].status = "open"
        trigger = self.room.speech_triggers["echo"][0]

        # Act / Assert
        self.assertFalse(trigger["conditional_fn"](self.player, self.game_state))


class MakeOpenEffectTest(GoldenDoorTestBase):
    """Test the synchronous open effect kicks off the generation task."""

    async def test_make_open_effect_returns_opening_message(self):
        """Test a sealed door flips to opening and returns flavor text."""
        # Arrange
        generator = make_fake_generator(spec=load_fixture())
        self._create_door(generator_factory=lambda: generator)
        self._give_key()
        effect = make_open_effect("t", lambda: generator)

        # Act
        result = effect(self.player, self.game_state)

        # Assert (before the background task lands)
        self.assertEqual(result, OPENING_MESSAGE)
        self.assertEqual(DOOR_REGISTRY["t"].status, "opening")

        # Let the background generation task complete.
        await self._drain_tasks()
        self.assertEqual(DOOR_REGISTRY["t"].status, "open")

    async def test_make_open_effect_returns_none_when_already_opening(self):
        """Test a second open while the light pours does nothing."""
        # Arrange
        generator = make_fake_generator(spec=load_fixture())
        self._create_door(generator_factory=lambda: generator)
        DOOR_REGISTRY["t"].status = "opening"
        effect = make_open_effect("t", lambda: generator)
        before = len(asyncio.all_tasks())

        # Act
        result = effect(self.player, self.game_state)

        # Assert
        self.assertIsNone(result)
        self.assertEqual(len(asyncio.all_tasks()), before)

    async def test_make_open_effect_returns_none_when_already_open(self):
        """Test opening an open door does nothing."""
        # Arrange
        generator = make_fake_generator(spec=load_fixture())
        self._create_door(generator_factory=lambda: generator)
        DOOR_REGISTRY["t"].status = "open"
        effect = make_open_effect("t", lambda: generator)

        # Act
        result = effect(self.player, self.game_state)

        # Assert
        self.assertIsNone(result)
        self.assertEqual(DOOR_REGISTRY["t"].status, "open")

    async def test_make_open_effect_returns_none_for_unknown_door(self):
        """Test an unregistered door id is a no-op."""
        # Arrange
        effect = make_open_effect("nope", lambda: make_fake_generator())

        # Act
        result = effect(self.player, self.game_state)

        # Assert
        self.assertIsNone(result)


class GenerateAndOpenTest(GoldenDoorTestBase):
    """Test the background generation task end to end (no network)."""

    async def test_generate_and_open_valid_spec_opens_the_door(self):
        """Test a valid generated spec injects the zone and opens the door."""
        # Arrange
        door = self._create_door()
        self._give_key()
        DOOR_REGISTRY["t"].status = "opening"
        generator = make_fake_generator(spec=load_fixture())

        # Act
        await _generate_and_open("t", self.player, self.game_state, generator)

        # Assert
        state = DOOR_REGISTRY["t"]
        self.assertEqual(state.status, "open")
        self.assertEqual(door.get_state(), "open")
        self.assertIsNotNone(self.game_state.get_room("pd_t_threshold"))
        self.assertEqual(self.room.exits["in"], "pd_t_threshold")
        key_ids = [getattr(i, "id", None) for i in self.player.inventory]
        self.assertNotIn(GOLDEN_KEY_ID, key_ids)
        self.send_message.assert_any_await("sid1", OPEN_BROADCAST)

    async def test_generate_and_open_spawns_zone_mobs(self):
        """Test zone mobs are spawned via utils.mob_manager."""
        # Arrange
        self._create_door()
        self._give_key()
        DOOR_REGISTRY["t"].status = "opening"
        generator = make_fake_generator(spec=load_fixture())

        # Act
        await _generate_and_open("t", self.player, self.game_state, generator)

        # Assert
        mobs = self.mob_manager.get_mobs_in_room("pd_t_ossuary")
        self.assertEqual(len(mobs), 1)
        self.assertEqual(mobs[0].name, "skeleton")

    async def test_generate_and_open_reseals_when_all_attempts_fail(self):
        """Test invalid specs twice with no fallback reseal the door."""
        # Arrange
        door = self._create_door()
        self._give_key()
        DOOR_REGISTRY["t"].status = "opening"
        generator = make_fake_generator(spec={})  # always invalid

        # Act
        with patch("services.zone_generator.load_fallback_spec", return_value=None):
            await _generate_and_open("t", self.player, self.game_state, generator)

        # Assert
        state = DOOR_REGISTRY["t"]
        self.assertEqual(state.status, "sealed")
        self.assertEqual(door.get_state(), "sealed")
        self.assertEqual(generator.generate_zone_spec.await_count, 2)
        self.assertIsNone(self.game_state.get_room("pd_t_threshold"))
        key_ids = [getattr(i, "id", None) for i in self.player.inventory]
        self.assertIn(GOLDEN_KEY_ID, key_ids)
        self.send_message.assert_any_await("sid1", FAILURE_BROADCAST)

    async def test_generate_and_open_falls_back_when_generator_raises(self):
        """Test a crashing generator still opens via the shipped fallback."""
        # Arrange
        self._create_door()
        self._give_key()
        DOOR_REGISTRY["t"].status = "opening"
        generator = make_fake_generator(side_effect=RuntimeError("boom"))

        # Act
        await _generate_and_open("t", self.player, self.game_state, generator)

        # Assert
        self.assertEqual(DOOR_REGISTRY["t"].status, "open")
        self.assertIsNotNone(self.game_state.get_room("pd_t_threshold"))
        self.send_message.assert_any_await("sid1", OPEN_BROADCAST)

    async def test_generate_and_open_uses_fallback_when_unavailable(self):
        """Test an unavailable generator (no client) opens via fallback."""
        # Arrange
        self._create_door()
        self._give_key()
        DOOR_REGISTRY["t"].status = "opening"
        generator = make_fake_generator(available=False)

        # Act
        await _generate_and_open("t", self.player, self.game_state, generator)

        # Assert
        self.assertEqual(DOOR_REGISTRY["t"].status, "open")
        generator.generate_zone_spec.assert_not_awaited()
        self.assertIsNotNone(self.game_state.get_room("pd_t_threshold"))

    async def test_generate_and_open_unknown_door_is_noop(self):
        """Test a missing registry entry returns without side effects."""
        # Act
        await _generate_and_open(
            "ghost", self.player, self.game_state, make_fake_generator()
        )

        # Assert
        self.send_message.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
