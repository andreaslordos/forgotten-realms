"""
Comprehensive tests for rest/sleep commands.

Tests cover:
- Sleep command
- Wake command (self and others)
- Sleep healing mechanics
- Combat prevention
- Session state management
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.rest import (
    handle_sleep,
    handle_wake,
    wake_player,
    process_sleeping_players,
)
from models.Player import Player
from models.Room import Room
from managers.game_state import GameState


class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    """Base class for async tests."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Player("Alice")
        self.player.current_room = "test_room"
        self.player.stamina = self.player.max_stamina - 10  # Not at max

        self.other_player = Player("Bob")
        self.other_player.current_room = "test_room"

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
        self.utils.send_stats_update = AsyncMock()

        # Set up online sessions
        self.online_sessions = {
            "sid1": {"player": self.player, "sleeping": False},
            "sid2": {"player": self.other_player, "sleeping": False},
        }


class SleepCommandTest(AsyncTestCase):
    """Test sleep command functionality."""

    @patch("commands.rest.broadcast_room", new_callable=AsyncMock)
    async def test_sleep_success(self, mock_broadcast):
        """Test successfully going to sleep."""
        cmd = {"verb": "sleep"}

        result = await handle_sleep(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "ZZZzzz...")
        self.assertTrue(self.online_sessions["sid1"]["sleeping"])
        self.assertEqual(self.online_sessions["sid1"]["sleep_tick_counter"], 0)
        mock_broadcast.assert_called_once()

    async def test_sleep_already_sleeping(self):
        """Test sleeping when already asleep."""
        self.online_sessions["sid1"]["sleeping"] = True

        cmd = {"verb": "sleep"}

        result = await handle_sleep(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "You are already asleep.")

    @patch("commands.combat.is_in_combat", return_value=True)
    async def test_sleep_in_combat(self, mock_combat):
        """Test sleeping fails when in combat."""
        cmd = {"verb": "sleep"}

        result = await handle_sleep(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("can't sleep while in combat", result)

    @patch("commands.rest.broadcast_room", new_callable=AsyncMock)
    async def test_sleep_at_max_stamina(self, mock_broadcast):
        """Test sleep fails when at max stamina."""
        self.player.stamina = self.player.max_stamina

        cmd = {"verb": "sleep"}

        result = await handle_sleep(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertIn("already at full stamina", result)


class WakeCommandTest(AsyncTestCase):
    """Test wake command functionality."""

    @patch("commands.rest.wake_player", new_callable=AsyncMock)
    async def test_wake_self(self, mock_wake):
        """Test waking yourself up."""
        self.online_sessions["sid1"]["sleeping"] = True

        cmd = {"verb": "wake"}

        result = await handle_wake(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "You wake up.")
        mock_wake.assert_called_once()

    async def test_wake_not_sleeping(self):
        """Test wake when not asleep."""
        cmd = {"verb": "wake"}

        result = await handle_wake(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "You're not asleep.")

    @patch("commands.rest.wake_player", new_callable=AsyncMock)
    async def test_wake_other_player(self, mock_wake):
        """Test waking another player."""
        self.online_sessions["sid2"]["sleeping"] = True

        cmd = {"verb": "wake", "subject": "Bob"}

        result = await handle_wake(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "You wake Bob up.")
        mock_wake.assert_called_once()

    async def test_wake_other_already_awake(self):
        """Test waking player who is already awake."""
        cmd = {"verb": "wake", "subject": "Bob"}

        result = await handle_wake(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "Bob is already awake.")

    async def test_wake_other_while_asleep(self):
        """Test can't wake others while you're asleep."""
        self.online_sessions["sid1"]["sleeping"] = True
        self.online_sessions["sid2"]["sleeping"] = True

        cmd = {"verb": "wake", "subject": "Bob"}

        result = await handle_wake(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "You can't wake others while you're asleep.")


class WakePlayerFunctionTest(AsyncTestCase):
    """Test wake_player helper function."""

    @patch("commands.rest.broadcast_room", new_callable=AsyncMock)
    async def test_wake_player_normal(self, mock_broadcast):
        """Test normal wake up."""
        self.online_sessions["sid1"]["sleeping"] = True
        self.online_sessions["sid1"]["sleep_tick_counter"] = 5

        await wake_player(
            self.player,
            "sid1",
            self.online_sessions,
            self.sio,
            self.utils,
            max_stamina_reached=False,
        )

        self.assertFalse(self.online_sessions["sid1"]["sleeping"])
        self.assertNotIn("sleep_tick_counter", self.online_sessions["sid1"])
        mock_broadcast.assert_called_once()

    @patch("commands.rest.broadcast_room", new_callable=AsyncMock)
    async def test_wake_player_max_stamina(self, mock_broadcast):
        """Test wake up due to max stamina."""
        self.online_sessions["sid1"]["sleeping"] = True

        await wake_player(
            self.player,
            "sid1",
            self.online_sessions,
            self.sio,
            self.utils,
            max_stamina_reached=True,
        )

        self.assertFalse(self.online_sessions["sid1"]["sleeping"])
        self.utils.send_message.assert_called_once()
        call_args = self.utils.send_message.call_args[0]
        self.assertIn("too alert", call_args[2])

    @patch("commands.rest.broadcast_room", new_callable=AsyncMock)
    async def test_wake_player_by_another(self, mock_broadcast):
        """Test wake up by another player."""
        waker = Player("Waker")
        self.online_sessions["sid1"]["sleeping"] = True

        await wake_player(
            self.player,
            "sid1",
            self.online_sessions,
            self.sio,
            self.utils,
            woken_by=waker,
        )

        self.assertFalse(self.online_sessions["sid1"]["sleeping"])
        self.utils.send_message.assert_called_once()
        call_args = self.utils.send_message.call_args[0]
        self.assertIn("awakened by Waker", call_args[2])


class ProcessSleepingPlayersTest(AsyncTestCase):
    """Test sleep healing tick processing."""

    async def test_healing_at_interval(self):
        """Test healing occurs at correct interval."""
        self.online_sessions["sid1"]["sleeping"] = True
        self.online_sessions["sid1"]["sleep_tick_counter"] = 1  # Will hit interval at 2
        initial_stamina = self.player.stamina

        await process_sleeping_players(
            self.sio, self.online_sessions, self.player_manager, self.utils
        )

        # Should heal
        self.assertEqual(self.player.stamina, initial_stamina + 1)
        self.assertEqual(self.online_sessions["sid1"]["sleep_tick_counter"], 0)

    async def test_counter_increments(self):
        """Test sleep counter increments."""
        self.online_sessions["sid1"]["sleeping"] = True
        self.online_sessions["sid1"]["sleep_tick_counter"] = 0

        await process_sleeping_players(
            self.sio, self.online_sessions, self.player_manager, self.utils
        )

        self.assertEqual(self.online_sessions["sid1"]["sleep_tick_counter"], 1)

    @patch("commands.rest.wake_player", new_callable=AsyncMock)
    async def test_wake_at_max_stamina(self, mock_wake):
        """Test player wakes when reaching max stamina."""
        self.player.stamina = self.player.max_stamina - 1
        self.online_sessions["sid1"]["sleeping"] = True
        self.online_sessions["sid1"]["sleep_tick_counter"] = 1

        await process_sleeping_players(
            self.sio, self.online_sessions, self.player_manager, self.utils
        )

        self.assertEqual(self.player.stamina, self.player.max_stamina)
        mock_wake.assert_called_once_with(
            self.player,
            "sid1",
            self.online_sessions,
            self.sio,
            self.utils,
            max_stamina_reached=True,
        )

    async def test_healing_message_periodically(self):
        """Test healing message sent periodically."""
        self.online_sessions["sid1"]["sleeping"] = True
        self.online_sessions["sid1"]["sleep_tick_counter"] = 1
        self.online_sessions["sid1"][
            "healing_message_count"
        ] = 0  # 0 % 3 == 0, so message sent

        await process_sleeping_players(
            self.sio, self.online_sessions, self.player_manager, self.utils
        )

        # Check both send_message (healing message) and send_stats_update were called
        self.assertTrue(self.utils.send_message.called)
        # Find the ZZZzzz message call
        zzz_calls = [
            call
            for call in self.utils.send_message.call_args_list
            if len(call[0]) > 2 and call[0][2] == "ZZZzzz..."
        ]
        self.assertEqual(len(zzz_calls), 1)


if __name__ == "__main__":
    unittest.main()
