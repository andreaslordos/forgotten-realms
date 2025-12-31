"""
Comprehensive tests for pathfinding module.

Tests cover:
- handle_swamp command functionality
- Command registration and aliases
- Combat and affliction blocking
- Indoor/outdoor room detection
- Edge cases (already at lake, no path)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.pathfinding import handle_swamp
from commands.registry import command_registry
from commands.natural_language_parser import vocabulary_manager
from models.Room import Room


class HandleSwampSuccessTest(unittest.IsolatedAsyncioTestCase):
    """Test successful swamp command execution."""

    def setUp(self) -> None:
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "square"

        self.mock_game_state = Mock()
        self.mock_player_manager = Mock()
        self.mock_sio = Mock()
        self.mock_utils = Mock()

        # Create an outdoor room with swamp_direction
        self.outdoor_room = Room("square", "Village Square", "A square")
        self.outdoor_room.is_outdoor = True
        self.outdoor_room.swamp_direction = "south"
        self.outdoor_room.exits = {"south": "road", "north": "church"}

        self.mock_game_state.get_room = Mock(return_value=self.outdoor_room)

        self.online_sessions = {"player_sid": {"player": self.player}}

    @patch("commands.pathfinding.is_in_combat", return_value=False)
    @patch("commands.pathfinding.find_player_sid", return_value="player_sid")
    @patch("commands.pathfinding.has_affliction", return_value=False)
    @patch("commands.pathfinding.handle_movement")
    async def test_handle_swamp_moves_player_toward_lake(
        self,
        mock_movement: Mock,
        mock_has_affliction: Mock,
        mock_find_sid: Mock,
        mock_combat: Mock,
    ) -> None:
        """Test handle_swamp moves player in the precomputed direction."""
        mock_movement.return_value = "You move south."

        _result = await handle_swamp(
            {"verb": "swamp"},
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        # Verify handle_movement was called with the swamp_direction
        mock_movement.assert_called_once()
        call_args = mock_movement.call_args[0]
        self.assertEqual(call_args[0]["verb"], "south")


class HandleSwampBlockedTest(unittest.IsolatedAsyncioTestCase):
    """Test swamp command blocking conditions."""

    def setUp(self) -> None:
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "square"

        self.mock_game_state = Mock()
        self.mock_player_manager = Mock()
        self.mock_sio = Mock()
        self.mock_utils = Mock()

        self.outdoor_room = Room("square", "Village Square", "A square")
        self.outdoor_room.is_outdoor = True
        self.outdoor_room.swamp_direction = "south"
        self.mock_game_state.get_room = Mock(return_value=self.outdoor_room)

        self.online_sessions = {"player_sid": {"player": self.player}}

    @patch("commands.pathfinding.is_in_combat", return_value=True)
    async def test_handle_swamp_blocked_by_combat(self, mock_combat: Mock) -> None:
        """Test handle_swamp is blocked when player is in combat."""
        result = await handle_swamp(
            {"verb": "swamp"},
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        self.assertIn("combat", result.lower())
        self.assertIn("flee", result.lower())

    @patch("commands.pathfinding.is_in_combat", return_value=False)
    @patch("commands.pathfinding.find_player_sid", return_value="player_sid")
    @patch("commands.pathfinding.has_affliction", return_value=True)
    async def test_handle_swamp_blocked_by_cripple(
        self,
        mock_has_affliction: Mock,
        mock_find_sid: Mock,
        mock_combat: Mock,
    ) -> None:
        """Test handle_swamp is blocked when player is crippled."""
        result = await handle_swamp(
            {"verb": "swamp"},
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        self.assertIn("crippled", result.lower())


class HandleSwampIndoorTest(unittest.IsolatedAsyncioTestCase):
    """Test swamp command in indoor rooms."""

    def setUp(self) -> None:
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"
        self.player.current_room = "tavern"

        self.mock_game_state = Mock()
        self.mock_player_manager = Mock()
        self.mock_sio = Mock()
        self.mock_utils = Mock()

        # Create an indoor room
        self.indoor_room = Room("tavern", "Blood of the Vine Tavern", "A tavern")
        self.indoor_room.is_outdoor = False
        self.mock_game_state.get_room = Mock(return_value=self.indoor_room)

        self.online_sessions = {"player_sid": {"player": self.player}}

    @patch("commands.pathfinding.is_in_combat", return_value=False)
    @patch("commands.pathfinding.find_player_sid", return_value="player_sid")
    @patch("commands.pathfinding.has_affliction", return_value=False)
    async def test_handle_swamp_blocked_in_indoor_room(
        self,
        mock_has_affliction: Mock,
        mock_find_sid: Mock,
        mock_combat: Mock,
    ) -> None:
        """Test handle_swamp fails in indoor rooms."""
        result = await handle_swamp(
            {"verb": "swamp"},
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        self.assertIn("outdoors", result.lower())


class HandleSwampEdgeCasesTest(unittest.IsolatedAsyncioTestCase):
    """Test swamp command edge cases."""

    def setUp(self) -> None:
        """Set up common test fixtures."""
        self.player = Mock()
        self.player.name = "TestPlayer"

        self.mock_game_state = Mock()
        self.mock_player_manager = Mock()
        self.mock_sio = Mock()
        self.mock_utils = Mock()

        self.online_sessions = {"player_sid": {"player": self.player}}

    @patch("commands.pathfinding.is_in_combat", return_value=False)
    @patch("commands.pathfinding.find_player_sid", return_value="player_sid")
    @patch("commands.pathfinding.has_affliction", return_value=False)
    async def test_handle_swamp_already_at_lake(
        self,
        mock_has_affliction: Mock,
        mock_find_sid: Mock,
        mock_combat: Mock,
    ) -> None:
        """Test handle_swamp shows message when already at lake."""
        self.player.current_room = "lake"

        lake_room = Room("lake", "Lake Zarovich", "A dark lake")
        lake_room.is_outdoor = True
        self.mock_game_state.get_room = Mock(return_value=lake_room)

        result = await handle_swamp(
            {"verb": "swamp"},
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        self.assertIn("already here", result.lower())

    @patch("commands.pathfinding.is_in_combat", return_value=False)
    @patch("commands.pathfinding.find_player_sid", return_value="player_sid")
    @patch("commands.pathfinding.has_affliction", return_value=False)
    async def test_handle_swamp_no_path(
        self,
        mock_has_affliction: Mock,
        mock_find_sid: Mock,
        mock_combat: Mock,
    ) -> None:
        """Test handle_swamp shows message when no path exists."""
        self.player.current_room = "isolated"

        # Create an outdoor room without swamp_direction
        isolated_room = Room("isolated", "Isolated Area", "A dead end")
        isolated_room.is_outdoor = True
        isolated_room.swamp_direction = None
        self.mock_game_state.get_room = Mock(return_value=isolated_room)

        result = await handle_swamp(
            {"verb": "swamp"},
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        self.assertIn("can't find", result.lower())

    @patch("commands.pathfinding.is_in_combat", return_value=False)
    @patch("commands.pathfinding.find_player_sid", return_value="player_sid")
    @patch("commands.pathfinding.has_affliction", return_value=False)
    async def test_handle_swamp_room_not_found(
        self,
        mock_has_affliction: Mock,
        mock_find_sid: Mock,
        mock_combat: Mock,
    ) -> None:
        """Test handle_swamp shows message when room not found."""
        self.player.current_room = "nonexistent"
        self.mock_game_state.get_room = Mock(return_value=None)

        result = await handle_swamp(
            {"verb": "swamp"},
            self.player,
            self.mock_game_state,
            self.mock_player_manager,
            self.online_sessions,
            self.mock_sio,
            self.mock_utils,
        )

        self.assertIn("void", result.lower())


class CommandRegistrationTest(unittest.TestCase):
    """Test command registration for pathfinding commands."""

    def test_swamp_command_is_registered(self) -> None:
        """Test swamp command is registered in command registry."""
        self.assertIn("swamp", command_registry.commands)

    def test_zw_alias_is_registered(self) -> None:
        """Test 'zw' alias is registered for swamp command."""
        # Aliases are stored as abbreviations in the vocabulary manager
        expanded = vocabulary_manager.expand_word("zw")
        self.assertEqual(expanded, "swamp")


if __name__ == "__main__":
    unittest.main()
