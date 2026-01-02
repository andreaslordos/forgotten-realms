"""
Comprehensive tests for executor module.

Tests cover:
- Command execution and routing
- Movement handling and validation
- Combat blocking during movement
- Room description building
- Private message routing
- Mob aggression on room entry
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.executor import execute_command, handle_movement, build_look_description
from models.Room import Room
from models.Item import Item
from models.Mobile import Mobile


class ExecuteCommandTest(unittest.IsolatedAsyncioTestCase):
    """Test execute_command function."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "room1"

        self.game_state = Mock()
        self.player_manager = Mock()
        self.sio = AsyncMock()
        self.utils = Mock()
        self.online_sessions = {}

    async def test_execute_command_quit_returns_quit(self):
        """Test quit command returns 'quit' string."""
        cmd = {"verb": "quit"}

        result = await execute_command(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
        )

        self.assertEqual(result, "quit")

    async def test_execute_command_routes_to_registered_handler(self):
        """Test command routes to registered handler."""
        # Mock the registry to return a handler
        mock_handler = AsyncMock(return_value="handler result")

        with patch(
            "commands.executor.command_registry.get_handler", return_value=mock_handler
        ):
            cmd = {"verb": "look"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            mock_handler.assert_called_once()
            self.assertEqual(result, "handler result")

    async def test_execute_command_unknown_verb_returns_error(self):
        """Test unknown verb returns error message."""
        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "unknowncommand"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertIn("don't know", result.lower())
            self.assertIn("unknowncommand", result.lower())

    async def test_execute_command_routes_movement_commands(self):
        """Test movement commands are routed to handle_movement."""
        room = Room(
            room_id="room1",
            name="Test Room",
            description="A room",
            exits={"north": "room2"},
        )
        self.game_state.get_room.return_value = room
        self.player_manager.save_players = Mock()

        new_room = Room(room_id="room2", name="New Room", description="Another room")

        def get_room_side_effect(room_id):
            if room_id == "room1":
                return room
            elif room_id == "room2":
                return new_room
            return None

        self.game_state.get_room.side_effect = get_room_side_effect
        self.player.visited = set()

        # Make set_current_room actually update the player's current_room
        def set_room(room_id):
            self.player.current_room = room_id

        self.player.set_current_room = Mock(side_effect=set_room)

        # Mock mob_manager
        self.utils.mob_manager = Mock()
        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[])

        with patch("commands.executor.is_movement_command", return_value=True):
            with patch("commands.executor.broadcast_departure", new=AsyncMock()):
                with patch("commands.executor.broadcast_arrival", new=AsyncMock()):
                    with patch("commands.combat.is_in_combat", return_value=False):
                        cmd = {"verb": "north"}

                        result = await execute_command(
                            cmd,
                            self.player,
                            self.game_state,
                            self.player_manager,
                            self.online_sessions,
                            self.sio,
                            self.utils,
                        )

                        # Should return room description
                        self.assertIn("New Room", result)


class HandleMovementTest(unittest.IsolatedAsyncioTestCase):
    """Test handle_movement function."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "room1"
        self.player.visited = set()
        self.player.set_current_room = Mock()

        self.room1 = Room(
            room_id="room1",
            name="Room 1",
            description="First room",
            exits={"north": "room2", "south": "room3"},
        )

        self.room2 = Room(room_id="room2", name="Room 2", description="Second room")

        self.game_state = Mock()

        def get_room_side_effect(room_id):
            if room_id == "room1":
                return self.room1
            elif room_id == "room2":
                return self.room2
            return None

        self.game_state.get_room.side_effect = get_room_side_effect

        self.player_manager = Mock()
        self.player_manager.save_players = Mock()

        self.sio = AsyncMock()
        self.utils = Mock()
        self.utils.mob_manager = Mock()
        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[])

        self.online_sessions = {}

    async def test_handle_movement_moves_player_to_valid_exit(self):
        """Test moving player through valid exit."""

        # Make set_current_room actually update the player's current_room
        def set_room(room_id):
            self.player.current_room = room_id

        self.player.set_current_room = Mock(side_effect=set_room)

        with patch("commands.executor.broadcast_departure", new=AsyncMock()):
            with patch("commands.executor.broadcast_arrival", new=AsyncMock()):
                with patch("commands.combat.is_in_combat", return_value=False):
                    cmd = {"verb": "north"}

                    result = await handle_movement(
                        cmd,
                        self.player,
                        self.game_state,
                        self.player_manager,
                        self.online_sessions,
                        self.sio,
                        self.utils,
                    )

                    # Should move player
                    self.player.set_current_room.assert_called_once_with("room2")
                    # Should save
                    self.player_manager.save_players.assert_called_once()
                    # Should return room description
                    self.assertIn("Room 2", result)

    async def test_handle_movement_invalid_exit_returns_error(self):
        """Test moving through invalid exit returns error."""
        with patch("commands.combat.is_in_combat", return_value=False):
            cmd = {"verb": "east"}  # Not a valid exit

            result = await handle_movement(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertIn("can't go that way", result.lower())

    async def test_handle_movement_blocked_during_combat(self):
        """Test movement is blocked during combat."""
        with patch("commands.combat.is_in_combat", return_value=True):
            cmd = {"verb": "north"}

            result = await handle_movement(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertIn("combat", result.lower())
            self.assertIn("flee", result.lower())
            # Should not move player
            self.player.set_current_room.assert_not_called()

    async def test_handle_movement_resets_idle_mob_aggro_delay(self):
        """Test moving into room with idle aggressive mob resets its aggro delay."""
        # Create aggressive mob that is idle (counter at 0)
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="An aggressive goblin",
            aggressive=True,
            max_stamina=50,
            current_room="room2",
            aggro_delay_min=2,
            aggro_delay_max=4,
        )
        mob.aggro_tick_counter = 0  # Mob is idle
        mob.target_player = None

        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[mob])
        self.online_sessions["player_sid"] = {"player": self.player}

        with patch("commands.executor.broadcast_departure", new=AsyncMock()):
            with patch("commands.executor.broadcast_arrival", new=AsyncMock()):
                cmd = {"verb": "north"}

                await handle_movement(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    self.online_sessions,
                    self.sio,
                    self.utils,
                )

                # Aggro delay should be reset (between min and max)
                self.assertIsNotNone(mob.aggro_tick_counter)
                self.assertGreaterEqual(mob.aggro_tick_counter, 2)
                self.assertLessEqual(mob.aggro_tick_counter, 4)

    async def test_handle_movement_does_not_reset_counting_mob_aggro(self):
        """Test moving into room doesn't reset mob aggro if already counting down."""
        # Create aggressive mob that is already counting down
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="An aggressive goblin",
            aggressive=True,
            max_stamina=50,
            current_room="room2",
            aggro_delay_min=2,
            aggro_delay_max=4,
        )
        mob.aggro_tick_counter = 3  # Already counting down
        mob.target_player = None

        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[mob])
        self.online_sessions["player_sid"] = {"player": self.player}

        with patch("commands.executor.broadcast_departure", new=AsyncMock()):
            with patch("commands.executor.broadcast_arrival", new=AsyncMock()):
                cmd = {"verb": "north"}

                await handle_movement(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    self.online_sessions,
                    self.sio,
                    self.utils,
                )

                # Aggro delay should NOT be reset - still at 3
                self.assertEqual(mob.aggro_tick_counter, 3)

    async def test_handle_movement_does_not_reset_mob_with_target(self):
        """Test moving into room doesn't reset mob aggro if mob has a target."""
        # Create aggressive mob that already has a target
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="An aggressive goblin",
            aggressive=True,
            max_stamina=50,
            current_room="room2",
            aggro_delay_min=2,
            aggro_delay_max=4,
        )
        mob.aggro_tick_counter = 0
        mob.target_player = Mock()  # Has a target

        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[mob])
        self.online_sessions["player_sid"] = {"player": self.player}

        with patch("commands.executor.broadcast_departure", new=AsyncMock()):
            with patch("commands.executor.broadcast_arrival", new=AsyncMock()):
                cmd = {"verb": "north"}

                await handle_movement(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    self.online_sessions,
                    self.sio,
                    self.utils,
                )

                # Aggro delay should NOT be reset since mob has a target
                self.assertEqual(mob.aggro_tick_counter, 0)

    async def test_handle_movement_resets_mob_after_previous_player_left(self):
        """Test new player gets grace period even if previous player left mid-countdown."""
        # Scenario: Player A triggered countdown but left. Counter reached 0.
        # Player B enters - should get a fresh grace period.
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="An aggressive goblin",
            aggressive=True,
            max_stamina=50,
            current_room="room2",
            aggro_delay_min=2,
            aggro_delay_max=4,
        )
        # Mob countdown reached 0 after previous player left
        mob.aggro_tick_counter = 0
        mob.target_player = None  # No target (previous player left)

        self.utils.mob_manager.get_mobs_in_room = Mock(return_value=[mob])
        self.online_sessions["player_sid"] = {"player": self.player}

        with patch("commands.executor.broadcast_departure", new=AsyncMock()):
            with patch("commands.executor.broadcast_arrival", new=AsyncMock()):
                cmd = {"verb": "north"}

                await handle_movement(
                    cmd,
                    self.player,
                    self.game_state,
                    self.player_manager,
                    self.online_sessions,
                    self.sio,
                    self.utils,
                )

                # New player should get fresh grace period
                self.assertIsNotNone(mob.aggro_tick_counter)
                self.assertGreaterEqual(mob.aggro_tick_counter, 2)
                self.assertLessEqual(mob.aggro_tick_counter, 4)


class BuildLookDescriptionTest(unittest.TestCase):
    """Test build_look_description function."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "room1"
        self.player.visited = set()

        self.room = Room(
            room_id="room1", name="Test Room", description="A test room for testing"
        )

        self.game_state = Mock()
        self.game_state.get_room.return_value = self.room

        self.online_sessions = {}

    def test_build_look_description_includes_room_name(self):
        """Test description includes room name."""
        result = build_look_description(self.player, self.game_state)

        self.assertIn("Test Room", result)

    def test_build_look_description_includes_full_description_on_first_visit(self):
        """Test full description shown on first visit."""
        result = build_look_description(self.player, self.game_state)

        self.assertIn("Test Room", result)
        self.assertIn("A test room for testing", result)
        self.assertIn("room1", self.player.visited)

    def test_build_look_description_omits_full_description_on_revisit(self):
        """Test full description omitted on revisit."""
        self.player.visited.add("room1")

        result = build_look_description(self.player, self.game_state)

        self.assertIn("Test Room", result)
        self.assertNotIn("A test room for testing", result)

    def test_build_look_description_includes_full_description_when_look_true(self):
        """Test full description shown when look=True."""
        self.player.visited.add("room1")

        result = build_look_description(self.player, self.game_state, look=True)

        self.assertIn("Test Room", result)
        self.assertIn("A test room for testing", result)

    def test_build_look_description_lists_items(self):
        """Test description lists items in room."""
        item = Item(
            name="bronze key", id="key_1", description="A bronze key lies on the ground"
        )
        self.room.add_item(item)

        result = build_look_description(self.player, self.game_state)

        self.assertIn("bronze key", result.lower())

    def test_build_look_description_lists_mobs(self):
        """Test description lists mobs in room."""
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="A goblin stands here",
            max_stamina=50,
            current_room="room1",
        )

        mob_manager = Mock()
        mob_manager.get_mobs_in_room = Mock(return_value=[mob])

        with patch("commands.combat.is_in_combat", return_value=False):
            result = build_look_description(
                self.player, self.game_state, mob_manager=mob_manager
            )

            self.assertIn("goblin", result.lower())

    def test_build_look_description_shows_mob_combat_status(self):
        """Test description shows mob combat status."""
        mob = Mobile(
            name="goblin",
            id="goblin_1",
            description="A goblin stands here",
            max_stamina=50,
            current_room="room1",
        )

        mob_manager = Mock()
        mob_manager.get_mobs_in_room = Mock(return_value=[mob])

        with patch("commands.combat.is_in_combat", return_value=True):
            result = build_look_description(
                self.player, self.game_state, mob_manager=mob_manager
            )

            self.assertIn("combat", result.lower())

    def test_build_look_description_lists_other_players(self):
        """Test description lists other players in room."""
        other_player = Mock()
        other_player.name = "OtherPlayer"
        other_player.level = "Novice"
        other_player.current_room = "room1"
        other_player.inventory = []

        self.online_sessions["other_sid"] = {"player": other_player}

        with patch("commands.utils.get_player_inventory", return_value="a sword"):
            with patch("commands.combat.is_in_combat", return_value=False):
                result = build_look_description(
                    self.player, self.game_state, online_sessions=self.online_sessions
                )

                self.assertIn("OtherPlayer", result)
                self.assertIn("Novice", result)

    def test_build_look_description_shows_player_combat_status(self):
        """Test description shows player combat status."""
        other_player = Mock()
        other_player.name = "OtherPlayer"
        other_player.level = "Novice"
        other_player.current_room = "room1"
        other_player.inventory = []

        self.online_sessions["other_sid"] = {"player": other_player, "sleeping": False}

        with patch("commands.utils.get_player_inventory", return_value=""):
            with patch("commands.combat.is_in_combat", return_value=True):
                result = build_look_description(
                    self.player, self.game_state, online_sessions=self.online_sessions
                )

                self.assertIn("in combat", result.lower())

    def test_build_look_description_shows_player_sleeping_status(self):
        """Test description shows player sleeping status."""
        other_player = Mock()
        other_player.name = "OtherPlayer"
        other_player.level = "Novice"
        other_player.current_room = "room1"
        other_player.inventory = []

        self.online_sessions["other_sid"] = {"player": other_player, "sleeping": True}

        with patch("commands.utils.get_player_inventory", return_value=""):
            with patch("commands.combat.is_in_combat", return_value=False):
                result = build_look_description(
                    self.player, self.game_state, online_sessions=self.online_sessions
                )

                self.assertIn("asleep", result.lower())

    def test_build_look_description_excludes_self(self):
        """Test description doesn't list the player themselves."""
        self.online_sessions["player_sid"] = {"player": self.player}

        with patch("commands.combat.is_in_combat", return_value=False):
            result = build_look_description(
                self.player, self.game_state, online_sessions=self.online_sessions
            )

            # Should not list TestPlayer since that's the player viewing
            lines = result.split("\n")
            player_lines = [line for line in lines if "TestPlayer" in line]
            self.assertEqual(len(player_lines), 0)


class ExecuteCommandSpeechTriggerTest(unittest.IsolatedAsyncioTestCase):
    """Test execute_command speech trigger functionality."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "room1"

        self.room = Room(
            room_id="room1",
            name="Test Room",
            description="A test room",
        )

        self.game_state = Mock()
        self.game_state.get_room.return_value = self.room

        self.player_manager = Mock()
        self.sio = AsyncMock()
        self.utils = Mock()
        self.online_sessions = {}

    async def test_speech_trigger_matches_keyword_in_input(self):
        """Test speech trigger fires when keyword is in input."""
        self.room.add_speech_trigger(
            keyword="lathander",
            message="The sacred name echoes!",
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "lathander", "original": "lathander"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(result, "The sacred name echoes!")

    async def test_speech_trigger_keyword_case_insensitive(self):
        """Test speech trigger matching is case-insensitive."""
        self.room.add_speech_trigger(
            keyword="lathander",
            message="The sacred name echoes!",
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "lathander", "original": "LATHANDER"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(result, "The sacred name echoes!")

    async def test_speech_trigger_one_time_only_fires_once(self):
        """Test one-time speech trigger only fires once."""
        self.room.add_speech_trigger(
            keyword="abracadabra",
            message="Magic happens!",
            one_time=True,
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "abracadabra", "original": "abracadabra"}

            # First trigger
            result1 = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            # Second trigger should not fire
            result2 = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(result1, "Magic happens!")
            self.assertIn("don't know", result2.lower())

    async def test_speech_trigger_not_one_time_fires_multiple(self):
        """Test non-one-time trigger fires multiple times."""
        self.room.add_speech_trigger(
            keyword="hello",
            message="Hello back!",
            one_time=False,
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "hello", "original": "hello"}

            result1 = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            result2 = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(result1, "Hello back!")
            self.assertEqual(result2, "Hello back!")

    async def test_speech_trigger_conditional_fn_passes(self):
        """Test speech trigger fires when conditional_fn returns True."""
        self.room.add_speech_trigger(
            keyword="open sesame",
            message="The door opens!",
            conditional_fn=lambda player, game_state: True,
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "open", "original": "open sesame"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(result, "The door opens!")

    async def test_speech_trigger_conditional_fn_fails_skips_trigger(self):
        """Test speech trigger skipped when conditional_fn returns False."""
        self.room.add_speech_trigger(
            keyword="open sesame",
            message="The door opens!",
            conditional_fn=lambda player, game_state: False,
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "open", "original": "open sesame"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            # Should fall through to unknown command
            self.assertIn("don't know", result.lower())

    async def test_speech_trigger_multiple_triggers_first_matching_wins(self):
        """Test first matching trigger wins when multiple exist for keyword."""
        # Add trigger that fails condition first
        self.room.add_speech_trigger(
            keyword="lathander",
            message="Already parted!",
            conditional_fn=lambda player, game_state: False,
        )
        # Add trigger that passes condition second
        self.room.add_speech_trigger(
            keyword="lathander",
            message="The mists part!",
            conditional_fn=lambda player, game_state: True,
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "lathander", "original": "lathander"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            # Second trigger should fire since first's condition failed
            self.assertEqual(result, "The mists part!")

    async def test_speech_trigger_fallback_when_no_condition(self):
        """Test trigger without conditional_fn acts as fallback."""
        # Add conditional trigger first
        self.room.add_speech_trigger(
            keyword="xyzzy",
            message="Special effect!",
            conditional_fn=lambda player, game_state: False,
        )
        # Add fallback trigger (no conditional_fn)
        self.room.add_speech_trigger(
            keyword="xyzzy",
            message="Nothing happens.",
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "xyzzy", "original": "xyzzy"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(result, "Nothing happens.")

    async def test_speech_trigger_effect_fn_called(self):
        """Test effect_fn is called when trigger fires."""
        effect_called = {"count": 0}

        async def my_effect(
            player, game_state, player_manager, online_sessions, sio, utils
        ):
            effect_called["count"] += 1

        self.room.add_speech_trigger(
            keyword="activate",
            message="Activated!",
            effect_fn=my_effect,
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "activate", "original": "activate"}

            await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(effect_called["count"], 1)

    async def test_speech_trigger_effect_fn_receives_correct_params(self):
        """Test effect_fn receives all expected parameters."""
        received_params = {}

        async def capture_params(
            player, game_state, player_manager, online_sessions, sio, utils
        ):
            received_params["player"] = player
            received_params["game_state"] = game_state
            received_params["player_manager"] = player_manager
            received_params["online_sessions"] = online_sessions
            received_params["sio"] = sio
            received_params["utils"] = utils

        self.room.add_speech_trigger(
            keyword="test",
            message="Tested!",
            effect_fn=capture_params,
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "test", "original": "test"}

            await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(received_params["player"], self.player)
            self.assertEqual(received_params["game_state"], self.game_state)
            self.assertEqual(received_params["player_manager"], self.player_manager)
            self.assertEqual(received_params["online_sessions"], self.online_sessions)
            self.assertEqual(received_params["sio"], self.sio)
            self.assertEqual(received_params["utils"], self.utils)

    async def test_speech_trigger_keyword_substring_match(self):
        """Test speech trigger matches keyword as substring in input."""
        self.room.add_speech_trigger(
            keyword="magic",
            message="You feel magical!",
        )

        with patch("commands.executor.command_registry.get_handler", return_value=None):
            cmd = {"verb": "say", "original": "say the magic word"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(result, "You feel magical!")

    async def test_speech_trigger_no_match_falls_through(self):
        """Test unmatched keyword falls through to command handler."""
        self.room.add_speech_trigger(
            keyword="specific_word",
            message="Triggered!",
        )

        mock_handler = AsyncMock(return_value="handler result")
        with patch(
            "commands.executor.command_registry.get_handler", return_value=mock_handler
        ):
            cmd = {"verb": "look", "original": "look around"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
            )

            self.assertEqual(result, "handler result")


class ExecuteCommandRespawnTest(unittest.IsolatedAsyncioTestCase):
    """Test execute_command handling respawn choices."""

    def setUp(self):
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "room1"
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

    async def test_execute_command_intercepts_respawn_yes(self):
        """Test respawn choice 'yes' is intercepted."""
        self.online_sessions["player_sid"]["awaiting_respawn"] = True
        self.online_sessions["player_sid"]["combat_death"] = True

        cmd = {"verb": "yes", "original": "yes"}

        result = await execute_command(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            player_sid="player_sid",
        )

        # Should respawn
        self.assertEqual(self.player.points, 0)
        self.assertEqual(self.player.level, "Neophyte")
        self.player.set_current_room.assert_called_with("village_center")
        self.assertIsNotNone(result)

    async def test_execute_command_intercepts_respawn_no(self):
        """Test respawn choice 'no' returns quit."""
        self.online_sessions["player_sid"]["awaiting_respawn"] = True
        self.online_sessions["player_sid"]["combat_death"] = True

        cmd = {"verb": "no", "original": "no"}

        result = await execute_command(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            player_sid="player_sid",
        )

        # Should return quit
        self.assertEqual(result, "quit")

    async def test_execute_command_intercepts_respawn_y_short_form(self):
        """Test respawn choice 'y' (short form) is intercepted."""
        self.online_sessions["player_sid"]["awaiting_respawn"] = True
        self.online_sessions["player_sid"]["combat_death"] = True

        cmd = {"verb": "y", "original": "y"}

        result = await execute_command(
            cmd,
            self.player,
            self.game_state,
            self.player_manager,
            self.online_sessions,
            self.sio,
            self.utils,
            player_sid="player_sid",
        )

        # Should respawn
        self.assertEqual(self.player.points, 0)
        self.assertIsNotNone(result)

    async def test_execute_command_normal_when_not_awaiting_respawn(self):
        """Test normal command processing when not awaiting respawn."""
        # No awaiting_respawn flag
        mock_handler = AsyncMock(return_value="handler result")

        with patch(
            "commands.executor.command_registry.get_handler", return_value=mock_handler
        ):
            cmd = {"verb": "look"}

            result = await execute_command(
                cmd,
                self.player,
                self.game_state,
                self.player_manager,
                self.online_sessions,
                self.sio,
                self.utils,
                player_sid="player_sid",
            )

            # Should route to normal handler
            mock_handler.assert_called_once()
            self.assertEqual(result, "handler result")


if __name__ == "__main__":
    unittest.main()
