import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tick_service import COMBAT_TICK_INTERVAL, TickService


class FakeTime:
    def __init__(self, start: float = 0.0):
        self.current = start

    def time(self) -> float:
        return self.current

    async def sleep(self, seconds: float) -> None:
        self.current += seconds

    def advance(self, seconds: float) -> None:
        self.current += seconds


class FakePlayer:
    def __init__(self, name="Hero", room="room-1"):
        self.name = name
        self.current_room = room
        self.points = 0
        self.stamina = 100
        self.max_stamina = 100


class FakeUtils:
    def __init__(self):
        self.messages = []
        self.stats_updates = []
        self.mob_manager = None

    async def send_message(self, sio, sid, message):
        self.messages.append((sid, message))

    async def send_stats_update(self, sio, sid, player):
        self.stats_updates.append((sid, player))


class FakeSio:
    def __init__(self):
        self.disconnected = []

    async def disconnect(self, sid):
        self.disconnected.append(sid)


async def noop_async(*_args, **_kwargs):
    return None


class TickServiceTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake_time = FakeTime()
        self.utils = FakeUtils()
        self.sio = FakeSio()
        self.player_manager = object()
        self.game_state = object()

    async def test_processes_command_queue_and_echoes(self):
        player = FakePlayer()
        session = {
            'command_queue': ['look'],
            'player': player,
        }
        online_sessions = {'sid-1': session}

        parse_calls = []
        execute_calls = []

        def fake_parse(cmd_str, **_kwargs):
            parse_calls.append(cmd_str)
            return [{'original': cmd_str, 'verb': 'look'}]

        async def fake_execute(cmd, *args, **kwargs):
            execute_calls.append((cmd, args))
            return 'it works'

        async def fake_pending(*_args, **_kwargs):
            return ''

        async def fake_combat(*_args, **_kwargs):
            return None

        async def fake_sleeping_players(*_args, **_kwargs):
            return None

        async def fake_broadcast(*_args, **_kwargs):
            return None

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=fake_parse,
            execute_command=fake_execute,
            handle_pending_communication=fake_pending,
            combat_tick_callable=fake_combat,
            sleeping_players_callable=fake_sleeping_players,
            broadcast_logout_callable=fake_broadcast,
        )

        await service.tick_once()

        self.assertEqual(parse_calls, ['look'])
        self.assertEqual(len(execute_calls), 1)
        self.assertEqual(session['command_queue'], [])

        messages = [message for _sid, message in self.utils.messages]
        self.assertIn('look', messages)
        self.assertIn('it works', messages)
        self.assertEqual(len(self.utils.stats_updates), 1)

    async def test_combat_tick_runs_after_interval(self):
        online_sessions = {}
        combat_calls = []

        async def fake_combat(*_args):
            combat_calls.append(1)

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            combat_tick_callable=fake_combat,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()
        self.assertEqual(combat_calls, [])

        self.fake_time.advance(COMBAT_TICK_INTERVAL - 0.1)
        await service.tick_once()
        self.assertEqual(combat_calls, [])

        self.fake_time.advance(0.2)
        await service.tick_once()
        self.assertEqual(len(combat_calls), 1)

    async def test_mob_manager_tick_invoked(self):
        class FakeMobManager:
            def __init__(self):
                self.calls = 0

            async def tick_all_mobs(self, *_args):
                self.calls += 1

        fake_mob_manager = FakeMobManager()
        self.utils.mob_manager = fake_mob_manager

        service = TickService(
            self.sio,
            {},
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()
        self.assertEqual(fake_mob_manager.calls, 1)

    async def test_command_error_logged_and_user_notified(self):
        player = FakePlayer()
        session = {
            'command_queue': ['boom'],
            'player': player,
        }
        online_sessions = {'sid-1': session}

        def fake_parse(cmd_str, **_kwargs):
            return [{'original': cmd_str, 'verb': 'boom'}]

        async def failing_execute(*_args, **_kwargs):
            raise ValueError('nope')

        async def sleeping_players(*_args, **_kwargs):
            return None

        async def fake_pending(*_args, **_kwargs):
            return ''

        async def fake_combat(*_args, **_kwargs):
            return None

        async def fake_sleeping_players(*_args, **_kwargs):
            return None

        async def fake_broadcast(*_args, **_kwargs):
            return None

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=fake_parse,
            execute_command=failing_execute,
            handle_pending_communication=fake_pending,
            combat_tick_callable=fake_combat,
            sleeping_players_callable=fake_sleeping_players,
            broadcast_logout_callable=fake_broadcast,
        )

        with self.assertLogs('tick_service', level='ERROR') as log_context:
            await service.tick_once()

        self.assertTrue(any('nope' in entry for entry in log_context.output))
        error_messages = [msg for _sid, msg in self.utils.messages if 'Error processing command' in msg]
        self.assertEqual(len(error_messages), 1)
        self.assertEqual(len(self.utils.stats_updates), 1)

    async def test_sleeping_player_blocked_from_commands(self):
        """Test sleeping player cannot execute most commands."""
        player = FakePlayer()
        session = {
            'command_queue': ['look'],
            'player': player,
            'sleeping': True,
        }
        online_sessions = {'sid-1': session}

        def fake_parse(cmd_str, **_kwargs):
            return [{'original': cmd_str, 'verb': 'look'}]

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=fake_parse,
            execute_command=noop_async,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()

        messages = [message for _sid, message in self.utils.messages]
        self.assertIn('You are asleep.', messages)

    async def test_quit_command_triggers_disconnect(self):
        """Test quit command sets should_disconnect flag."""
        player = FakePlayer()
        session = {
            'command_queue': ['quit'],
            'player': player,
        }
        online_sessions = {'sid-1': session}

        def fake_parse(cmd_str, **_kwargs):
            return [{'original': cmd_str, 'verb': 'quit'}]

        async def quit_execute(*_args, **_kwargs):
            return "quit"

        async def fake_broadcast(*_args, **_kwargs):
            return None

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=fake_parse,
            execute_command=quit_execute,
            sleeping_players_callable=noop_async,
            broadcast_logout_callable=fake_broadcast,
        )

        await service.tick_once()

        self.assertTrue(session.get('should_disconnect'))
        self.assertIn('sid-1', self.sio.disconnected)

    async def test_multiple_commands_requeued(self):
        """Test multiple parsed commands are requeued properly."""
        player = FakePlayer()
        session = {
            'command_queue': ['n;s'],
            'player': player,
        }
        online_sessions = {'sid-1': session}

        def fake_parse(cmd_str, **_kwargs):
            return [
                {'original': 'n', 'verb': 'north'},
                {'original': 's', 'verb': 'south'}
            ]

        async def fake_execute(cmd, *args, **kwargs):
            return f"Moved {cmd.get('verb')}"

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=fake_parse,
            execute_command=fake_execute,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()

        # Second command should be requeued
        self.assertEqual(session['command_queue'], ['s'])

    async def test_pending_communication_handled(self):
        """Test pending communication is processed."""
        player = FakePlayer()
        session = {
            'command_queue': ['response'],
            'player': player,
            'pending_comm': {'type': 'tell'},
        }
        online_sessions = {'sid-1': session}

        async def fake_pending(pending_comm, cmd_str, *args, **kwargs):
            return f"Handled: {cmd_str}"

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            handle_pending_communication=fake_pending,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()

        messages = [message for _sid, message in self.utils.messages]
        self.assertTrue(any('Handled: response' in msg for msg in messages))

    async def test_converse_mode_prepends_say(self):
        """Test converse mode prepends 'say' to commands."""
        player = FakePlayer()
        session = {
            'command_queue': ['hello world'],
            'player': player,
            'converse_mode': True,
        }
        online_sessions = {'sid-1': session}

        parse_calls = []

        def fake_parse(cmd_str, **_kwargs):
            parse_calls.append(cmd_str)
            return [{'original': cmd_str, 'verb': 'say'}]

        async def fake_execute(cmd, *args, **kwargs):
            return "You say something"

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=fake_parse,
            execute_command=fake_execute,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()

        self.assertTrue(any('say hello world' in call for call in parse_calls))

    async def test_converse_mode_exits_with_star(self):
        """Test converse mode exits with * prefix."""
        player = FakePlayer()
        session = {
            'command_queue': ['*look'],
            'player': player,
            'converse_mode': True,
        }
        online_sessions = {'sid-1': session}

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=lambda *args, **kwargs: [],
            execute_command=noop_async,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()

        self.assertFalse(session.get('converse_mode'))
        messages = [message for _sid, message in self.utils.messages]
        self.assertTrue(any('Converse mode OFF' in msg for msg in messages))

    async def test_unparseable_command_returns_error(self):
        """Test unparseable commands return error message."""
        player = FakePlayer()
        session = {
            'command_queue': ['invalid'],
            'player': player,
        }
        online_sessions = {'sid-1': session}

        def fake_parse(cmd_str, **_kwargs):
            return []

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=fake_parse,
            execute_command=noop_async,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()

        messages = [message for _sid, message in self.utils.messages]
        self.assertTrue(any("didn't understand" in msg for msg in messages))

    async def test_player_sid_passed_to_execute_command(self):
        """Test player_sid is passed to execute_command for respawn interception."""
        player = FakePlayer()
        session = {
            'command_queue': ['look'],
            'player': player,
        }
        online_sessions = {'sid-123': session}

        execute_kwargs = {}

        def fake_parse(cmd_str, **_kwargs):
            return [{'original': cmd_str, 'verb': 'look'}]

        async def fake_execute(cmd, *args, **kwargs):
            execute_kwargs.update(kwargs)
            return 'ok'

        service = TickService(
            self.sio,
            online_sessions,
            self.player_manager,
            self.game_state,
            self.utils,
            time_func=self.fake_time.time,
            sleep_func=self.fake_time.sleep,
            parse_command=fake_parse,
            execute_command=fake_execute,
            sleeping_players_callable=noop_async,
        )

        await service.tick_once()

        # Verify player_sid was passed
        self.assertIn('player_sid', execute_kwargs)
        self.assertEqual(execute_kwargs['player_sid'], 'sid-123')


if __name__ == '__main__':
    unittest.main()
