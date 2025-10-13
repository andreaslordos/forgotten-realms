"""
Comprehensive tests for get_online_players module.

Tests cover:
- get_online_players with dict sessions
- get_online_players with object sessions
- get_online_players filtering
- get_online_players edge cases
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.get_online_players import get_online_players
from tests.test_helpers import create_mock_player


class GetOnlinePlayersBasicTest(unittest.TestCase):
    """Test get_online_players basic functionality."""

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_returns_list(self, mock_sessions):
        """Test get_online_players returns a list."""
        mock_sessions.items.return_value = []

        result = get_online_players()

        self.assertIsInstance(result, list)

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_returns_empty_list_when_no_sessions(
        self, mock_sessions
    ):
        """Test get_online_players returns empty list when no sessions."""
        mock_sessions.items.return_value = []

        result = get_online_players()

        self.assertEqual(result, [])

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_extracts_players_from_dict_sessions(
        self, mock_sessions
    ):
        """Test get_online_players extracts players from dictionary sessions."""
        player1 = create_mock_player(name="Alice")
        player2 = create_mock_player(name="Bob")

        mock_sessions.items.return_value = [
            ("sid1", {"player": player1}),
            ("sid2", {"player": player2}),
        ]

        result = get_online_players()

        self.assertEqual(len(result), 2)
        self.assertIn(player1, result)
        self.assertIn(player2, result)

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_extracts_players_from_object_sessions(
        self, mock_sessions
    ):
        """Test get_online_players extracts players from object sessions."""
        player = create_mock_player(name="Charlie")

        session_obj = Mock()
        session_obj.player = player

        mock_sessions.items.return_value = [("sid1", session_obj)]

        result = get_online_players()

        self.assertEqual(len(result), 1)
        self.assertIn(player, result)


class GetOnlinePlayersFilteringTest(unittest.TestCase):
    """Test get_online_players filtering."""

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_skips_sessions_without_player(self, mock_sessions):
        """Test get_online_players skips sessions without a player."""
        player = create_mock_player(name="Alice")

        mock_sessions.items.return_value = [
            ("sid1", {"player": player}),
            ("sid2", {"other_data": "value"}),  # No player
            ("sid3", {"player": None}),  # Null player
        ]

        result = get_online_players()

        self.assertEqual(len(result), 1)
        self.assertIn(player, result)

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_handles_mixed_session_types(self, mock_sessions):
        """Test get_online_players handles mixed session types."""
        player1 = create_mock_player(name="Alice")
        player2 = create_mock_player(name="Bob")

        session_obj = Mock()
        session_obj.player = player2

        mock_sessions.items.return_value = [
            ("sid1", {"player": player1}),
            ("sid2", session_obj),
        ]

        result = get_online_players()

        self.assertEqual(len(result), 2)
        self.assertIn(player1, result)
        self.assertIn(player2, result)

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_skips_object_sessions_without_player_attribute(
        self, mock_sessions
    ):
        """Test get_online_players skips object sessions without player attribute."""
        player = create_mock_player(name="Alice")

        session_obj = Mock(spec=[])  # No attributes

        mock_sessions.items.return_value = [
            ("sid1", {"player": player}),
            ("sid2", session_obj),
        ]

        result = get_online_players()

        self.assertEqual(len(result), 1)
        self.assertIn(player, result)


class GetOnlinePlayersEdgeCasesTest(unittest.TestCase):
    """Test get_online_players edge cases."""

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_handles_many_sessions(self, mock_sessions):
        """Test get_online_players handles many sessions."""
        players = [create_mock_player(name=f"Player{i}") for i in range(100)]
        sessions = [(f"sid{i}", {"player": players[i]}) for i in range(100)]

        mock_sessions.items.return_value = sessions

        result = get_online_players()

        self.assertEqual(len(result), 100)
        for player in players:
            self.assertIn(player, result)

    @patch("services.get_online_players.online_sessions")
    def test_get_online_players_maintains_distinct_players(self, mock_sessions):
        """Test get_online_players maintains distinct player instances."""
        player1 = create_mock_player(name="Alice")
        player2 = create_mock_player(name="Alice")  # Same name, different object

        mock_sessions.items.return_value = [
            ("sid1", {"player": player1}),
            ("sid2", {"player": player2}),
        ]

        result = get_online_players()

        self.assertEqual(len(result), 2)
        self.assertIs(result[0], player1)
        self.assertIs(result[1], player2)


if __name__ == "__main__":
    unittest.main()
