# backend/services/tests/test_world_clock.py
"""Tests for the day/night world clock service."""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Room import Room
from services.world_clock import (
    CYCLE_SECONDS,
    DAWN_MESSAGE,
    DAY_SECONDS,
    DUSK_MESSAGE,
    WorldClock,
    get_world_clock,
    set_world_clock,
)


class FakeTime:
    """Controllable clock for deterministic time-based tests."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def time(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class WorldClockPhaseTest(unittest.TestCase):
    """Test WorldClock phase and night detection across the cycle."""

    def setUp(self):
        """Set up a clock anchored to a controllable fake time."""
        self.fake = FakeTime()
        self.clock = WorldClock(time_func=self.fake.time, epoch=self.fake.time())

    def tearDown(self):
        """Clear the module-global clock so other tests aren't polluted."""
        set_world_clock(None)

    def test_is_night_returns_false_at_cycle_start(self):
        """Test is_night is False at cycle position 0 (day)."""
        # Arrange - clock starts at epoch (position 0)

        # Act
        result = self.clock.is_night()

        # Assert
        self.assertFalse(result)
        self.assertEqual(self.clock.phase(), "day")

    def test_is_night_returns_true_at_day_boundary(self):
        """Test is_night is True exactly at position 1800 (dusk)."""
        # Arrange
        self.fake.advance(DAY_SECONDS)

        # Act
        result = self.clock.is_night()

        # Assert
        self.assertTrue(result)
        self.assertEqual(self.clock.phase(), "night")

    def test_is_night_returns_false_after_full_cycle(self):
        """Test is_night wraps back to day at position 2700."""
        # Arrange
        self.fake.advance(CYCLE_SECONDS)

        # Act
        result = self.clock.is_night()

        # Assert
        self.assertFalse(result)
        self.assertEqual(self.clock.phase(), "day")

    def test_seconds_until_transition_during_day(self):
        """Test seconds_until_transition counts down to dusk during day."""
        # Arrange - 600 seconds into the day
        self.fake.advance(600.0)

        # Act
        remaining = self.clock.seconds_until_transition()

        # Assert - 1800 - 600 = 1200 seconds until dusk
        self.assertEqual(remaining, 1200.0)

    def test_seconds_until_transition_during_night(self):
        """Test seconds_until_transition counts down to dawn during night."""
        # Arrange - 200 seconds into the night
        self.fake.advance(DAY_SECONDS + 200.0)

        # Act
        remaining = self.clock.seconds_until_transition()

        # Assert - 2700 - 2000 = 700 seconds until dawn
        self.assertEqual(remaining, 700.0)


class WorldClockDescribeTest(unittest.TestCase):
    """Test WorldClock.describe player-facing strings."""

    def setUp(self):
        """Set up a clock anchored to a controllable fake time."""
        self.fake = FakeTime()
        self.clock = WorldClock(time_func=self.fake.time, epoch=self.fake.time())

    def tearDown(self):
        """Clear the module-global clock so other tests aren't polluted."""
        set_world_clock(None)

    def test_describe_reports_day_with_minutes_until_dusk(self):
        """Test describe reports day phase with minutes remaining."""
        # Arrange - at position 0, 30 minutes of daylight remain

        # Act
        text = self.clock.describe()

        # Assert
        self.assertEqual(text, "It is day. Dusk falls in about 30 minute(s).")

    def test_describe_reports_dusk_moments_away_under_a_minute(self):
        """Test describe warns of imminent dusk when under 60 seconds remain."""
        # Arrange - 30 seconds before dusk
        self.fake.advance(DAY_SECONDS - 30.0)

        # Act
        text = self.clock.describe()

        # Assert
        self.assertEqual(
            text, "It is day, but the light is failing - dusk is moments away."
        )

    def test_describe_reports_night_with_minutes_until_dawn(self):
        """Test describe reports night phase with minutes remaining."""
        # Arrange - dusk just fell; 15 minutes of night remain
        self.fake.advance(DAY_SECONDS)

        # Act
        text = self.clock.describe()

        # Assert
        self.assertEqual(text, "It is night. Dawn breaks in about 15 minute(s).")

    def test_describe_reports_dawn_moments_away_under_a_minute(self):
        """Test describe warns of imminent dawn when under 60 seconds remain."""
        # Arrange - 45 seconds before dawn
        self.fake.advance(CYCLE_SECONDS - 45.0)

        # Act
        text = self.clock.describe()

        # Assert
        self.assertEqual(text, "It is night. Dawn is moments away.")


class WorldClockTickTest(unittest.IsolatedAsyncioTestCase):
    """Test WorldClock.tick transition handling."""

    def setUp(self):
        """Set up a clock, rooms, sessions, and mocked collaborators."""
        self.fake = FakeTime()
        self.clock = WorldClock(time_func=self.fake.time, epoch=self.fake.time())

        # Real rooms so is_outdoor is a genuine attribute
        self.outdoor_room = Room(
            "crossroads", "Crossroads", "A windswept crossroads.", is_outdoor=True
        )
        self.indoor_room = Room("inn", "Inn", "A cosy inn.", is_outdoor=False)
        rooms = {"crossroads": self.outdoor_room, "inn": self.indoor_room}
        self.game_state = Mock()
        self.game_state.get_room = Mock(side_effect=lambda rid: rooms.get(rid))

        self.outdoor_player = Mock()
        self.outdoor_player.current_room = "crossroads"
        self.indoor_player = Mock()
        self.indoor_player.current_room = "inn"
        self.sleeping_player = Mock()
        self.sleeping_player.current_room = "crossroads"
        self.online_sessions = {
            "sid_out": {"player": self.outdoor_player},
            "sid_in": {"player": self.indoor_player},
            "sid_sleep": {"player": self.sleeping_player, "sleeping": True},
        }

        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

        # Mob manager mock backed by a real spawn_records dict
        self.mob_manager = Mock()
        self.mob_manager.spawn_records = {}
        self._spawned_ids = []

        def fake_spawn(definition_id, room_id, game_state):
            mob = Mock()
            mob.id = f"{definition_id}_{len(self._spawned_ids)}_{room_id}"
            self._spawned_ids.append(mob.id)
            self.mob_manager.spawn_records[mob.id] = (definition_id, room_id)
            return mob

        self.mob_manager.spawn_mob = Mock(side_effect=fake_spawn)
        self.mob_manager.remove_mob = Mock(return_value=True)

    def tearDown(self):
        """Clear the module-global clock so other tests aren't polluted."""
        set_world_clock(None)

    async def _tick(self):
        return await self.clock.tick(
            self.sio,
            self.online_sessions,
            self.game_state,
            self.utils,
            self.mob_manager,
        )

    async def test_tick_returns_none_without_phase_change(self):
        """Test tick returns None and stays quiet with no transition."""
        # Arrange - still daytime
        self.fake.advance(60.0)

        # Act
        result = await self._tick()

        # Assert
        self.assertIsNone(result)
        self.utils.send_message.assert_not_called()
        self.mob_manager.spawn_mob.assert_not_called()

    async def test_tick_returns_night_on_dusk_transition(self):
        """Test tick returns 'night' when day rolls over to night."""
        # Arrange
        self.fake.advance(DAY_SECONDS)

        # Act
        result = await self._tick()

        # Assert
        self.assertEqual(result, "night")

    async def test_tick_sends_dusk_message_only_to_awake_outdoor_players(self):
        """Test dusk message reaches outdoor players but not indoor/sleeping."""
        # Arrange
        self.fake.advance(DAY_SECONDS)

        # Act
        await self._tick()

        # Assert - only the awake outdoor player heard the howl
        self.utils.send_message.assert_awaited_once_with(
            self.sio, "sid_out", DUSK_MESSAGE
        )

    async def test_tick_spawns_night_mobs_and_forgets_their_spawn_records(self):
        """Test dusk spawns NIGHT_SPAWNS and pops each id from spawn_records."""
        # Arrange
        from managers.mob_definitions import NIGHT_SPAWNS

        self.fake.advance(DAY_SECONDS)

        # Act
        await self._tick()

        # Assert - one spawn per NIGHT_SPAWNS entry, tracked for dawn
        self.assertEqual(self.mob_manager.spawn_mob.call_count, len(NIGHT_SPAWNS))
        for definition_id, room_id in NIGHT_SPAWNS:
            self.mob_manager.spawn_mob.assert_any_call(
                definition_id, room_id, self.game_state
            )
        self.assertEqual(self.clock._night_mob_ids, self._spawned_ids)
        # Night mobs must never respawn on a timer
        self.assertEqual(self.mob_manager.spawn_records, {})

    async def test_tick_returns_day_and_despawns_night_mobs_at_dawn(self):
        """Test dawn returns 'day', broadcasts, and removes every night mob."""
        # Arrange - go through dusk first so night mobs exist
        self.fake.advance(DAY_SECONDS)
        await self._tick()
        self.utils.send_message.reset_mock()
        night_ids = list(self.clock._night_mob_ids)
        self.assertTrue(night_ids)

        self.fake.advance(CYCLE_SECONDS - DAY_SECONDS)

        # Act
        result = await self._tick()

        # Assert
        self.assertEqual(result, "day")
        self.utils.send_message.assert_awaited_once_with(
            self.sio, "sid_out", DAWN_MESSAGE
        )
        for mob_id in night_ids:
            self.mob_manager.remove_mob.assert_any_call(
                mob_id, self.game_state, schedule_respawn=False
            )
        self.assertEqual(self.clock._night_mob_ids, [])

    async def test_tick_handles_missing_mob_manager(self):
        """Test tick still reports the transition when mob_manager is None."""
        # Arrange
        self.fake.advance(DAY_SECONDS)

        # Act
        result = await self.clock.tick(
            self.sio, self.online_sessions, self.game_state, self.utils, None
        )

        # Assert - message still sent, no crash
        self.assertEqual(result, "night")
        self.utils.send_message.assert_awaited_once_with(
            self.sio, "sid_out", DUSK_MESSAGE
        )


class WorldClockGlobalAccessorTest(unittest.TestCase):
    """Test set_world_clock/get_world_clock module-global round-trip."""

    def tearDown(self):
        """Clear the module-global clock so other tests aren't polluted."""
        set_world_clock(None)

    def test_set_world_clock_round_trips_through_get_world_clock(self):
        """Test get_world_clock returns the clock passed to set_world_clock."""
        # Arrange
        fake = FakeTime()
        clock = WorldClock(time_func=fake.time, epoch=fake.time())

        # Act
        set_world_clock(clock)

        # Assert
        self.assertIs(get_world_clock(), clock)

    def test_set_world_clock_none_clears_global(self):
        """Test set_world_clock(None) clears the global clock."""
        # Arrange
        fake = FakeTime()
        set_world_clock(WorldClock(time_func=fake.time, epoch=fake.time()))

        # Act
        set_world_clock(None)

        # Assert
        self.assertIsNone(get_world_clock())


if __name__ == "__main__":
    unittest.main()
