"""
Comprehensive tests for parser module.

Tests cover:
- parse_command_wrapper with regular commands
- parse_command_wrapper with quoted commands (say)
- parse_command_wrapper with direct messages
- parse_command_wrapper with movement commands
- parse_command_wrapper error cases
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.parser import parse_command_wrapper
from tests.test_helpers import create_mock_player, create_mock_game_state


class ParseCommandWrapperBasicTest(unittest.TestCase):
    """Test parse_command_wrapper basic functionality."""

    @patch("commands.parser.parse_command")
    @patch("commands.parser.vocabulary_manager")
    def test_parse_command_wrapper_returns_empty_list_for_empty_string(
        self, mock_vocab, mock_parse
    ):
        """Test parse_command_wrapper returns empty list for empty command."""
        # Act
        result = parse_command_wrapper("", online_sessions={})

        # Assert
        self.assertEqual(result, [])
        mock_parse.assert_not_called()

    @patch("commands.parser.parse_command")
    @patch("commands.parser.vocabulary_manager")
    def test_parse_command_wrapper_returns_empty_list_for_whitespace(
        self, mock_vocab, mock_parse
    ):
        """Test parse_command_wrapper returns empty list for whitespace."""
        # Act
        result = parse_command_wrapper("   ", online_sessions={})

        # Assert
        self.assertEqual(result, [])

    @patch("commands.parser.parse_command")
    @patch("commands.parser.vocabulary_manager")
    def test_parse_command_wrapper_calls_natural_language_parser(
        self, mock_vocab, mock_parse
    ):
        """Test parse_command_wrapper calls natural language parser."""
        # Arrange
        mock_parse.return_value = [{"verb": "look"}]
        player = create_mock_player()
        game_state = create_mock_game_state()
        context = {"player": player, "game_state": game_state}

        # Act
        parse_command_wrapper("look", context=context, online_sessions={})

        # Assert
        mock_parse.assert_called_once()

    @patch("commands.parser.parse_command")
    @patch("commands.parser.vocabulary_manager")
    def test_parse_command_wrapper_adds_context_to_commands(
        self, mock_vocab, mock_parse
    ):
        """Test parse_command_wrapper adds context to parsed commands."""
        # Arrange
        mock_parse.return_value = [{"verb": "look"}]
        players_in_room = [create_mock_player()]
        online_sessions = {}

        # Act
        result = parse_command_wrapper(
            "look", players_in_room=players_in_room, online_sessions=online_sessions
        )

        # Assert
        self.assertEqual(len(result), 1)
        self.assertIn("players_in_room", result[0])
        self.assertIn("online_sessions", result[0])
        self.assertEqual(result[0]["players_in_room"], players_in_room)


class ParseCommandWrapperQuotedTest(unittest.TestCase):
    """Test parse_command_wrapper with quoted commands."""

    def test_parse_command_wrapper_handles_quoted_say_command(self):
        """Test parse_command_wrapper handles quoted say command."""
        # Act
        result = parse_command_wrapper('"Hello world', online_sessions={})

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "say")
        self.assertEqual(result[0]["subject"], "Hello world")

    def test_parse_command_wrapper_preserves_exact_message_for_say(self):
        """Test parse_command_wrapper preserves exact message for say."""
        # Act
        result = parse_command_wrapper('"   Hello   world   ', online_sessions={})

        # Assert
        self.assertEqual(result[0]["subject"], "Hello   world")

    def test_parse_command_wrapper_handles_empty_quoted_command(self):
        """Test parse_command_wrapper handles empty quoted command."""
        # Act
        result = parse_command_wrapper('"', online_sessions={})

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "say")
        self.assertEqual(result[0]["subject"], "")


class ParseCommandWrapperDirectMessageTest(unittest.TestCase):
    """Test parse_command_wrapper with direct messages."""

    def test_parse_command_wrapper_handles_direct_player_message(self):
        """Test parse_command_wrapper handles direct player message."""
        # Arrange
        target_player = create_mock_player(name="Bob")
        online_sessions = {
            "sid1": {"player": target_player, "temp_data": {"username": "Bob"}}
        }

        # Act
        result = parse_command_wrapper(
            "Bob Hello there", online_sessions=online_sessions
        )

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "tell")
        self.assertEqual(result[0]["subject"], "Bob")
        self.assertEqual(result[0]["instrument"], "Hello there")
        self.assertTrue(result[0].get("is_direct_message"))

    def test_parse_command_wrapper_direct_message_case_insensitive(self):
        """Test parse_command_wrapper direct message is case insensitive."""
        # Arrange
        target_player = create_mock_player(name="Bob")
        online_sessions = {
            "sid1": {"player": target_player, "temp_data": {"username": "Bob"}}
        }

        # Act
        result = parse_command_wrapper(
            "bob Hello there", online_sessions=online_sessions
        )

        # Assert
        self.assertEqual(result[0]["verb"], "tell")
        self.assertEqual(result[0]["subject"], "bob")

    def test_parse_command_wrapper_direct_message_with_no_message(self):
        """Test parse_command_wrapper handles direct message with no message."""
        # Arrange
        target_player = create_mock_player(name="Bob")
        online_sessions = {
            "sid1": {"player": target_player, "temp_data": {"username": "Bob"}}
        }

        # Act
        result = parse_command_wrapper("Bob", online_sessions=online_sessions)

        # Assert
        self.assertEqual(result[0]["verb"], "tell")
        self.assertEqual(result[0]["instrument"], "")


class ParseCommandWrapperMovementTest(unittest.TestCase):
    """Test parse_command_wrapper with movement commands."""

    @patch("commands.parser.vocabulary_manager")
    @patch("commands.parser.is_movement_command")
    @patch("commands.parser.parse_command")
    def test_parse_command_wrapper_marks_movement_commands(
        self, mock_parse, mock_is_movement, mock_vocab
    ):
        """Test parse_command_wrapper marks movement commands with is_movement flag."""
        # Arrange
        mock_parse.return_value = [{"verb": "north"}]
        mock_is_movement.return_value = True

        # Act
        result = parse_command_wrapper("north", online_sessions={})

        # Assert
        self.assertTrue(result[0].get("is_movement"))

    @patch("commands.parser.vocabulary_manager")
    @patch("commands.parser.parse_command")
    def test_parse_command_wrapper_creates_default_movement_command(
        self, mock_parse, mock_vocab
    ):
        """Test parse_command_wrapper creates default command for unparsed movement."""
        # Arrange
        mock_parse.return_value = []
        mock_vocab.expand_word.return_value = "north"
        mock_vocab.is_direction.return_value = True

        # Act
        result = parse_command_wrapper("n", online_sessions={})

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "north")
        self.assertTrue(result[0].get("is_movement"))


class ParseCommandWrapperFallbackTest(unittest.TestCase):
    """Test parse_command_wrapper fallback behavior."""

    @patch("commands.parser.vocabulary_manager")
    @patch("commands.parser.parse_command")
    def test_parse_command_wrapper_creates_default_command_when_parser_fails(
        self, mock_parse, mock_vocab
    ):
        """Test parse_command_wrapper creates default command when parser returns nothing."""
        # Arrange
        mock_parse.return_value = []
        mock_vocab.expand_word.side_effect = lambda x: x
        mock_vocab.is_direction.return_value = False

        # Act
        result = parse_command_wrapper("look", online_sessions={})

        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "look")
        self.assertIsNone(result[0]["subject"])

    @patch("commands.parser.vocabulary_manager")
    @patch("commands.parser.parse_command")
    def test_parse_command_wrapper_expands_abbreviated_verbs(
        self, mock_parse, mock_vocab
    ):
        """Test parse_command_wrapper expands abbreviated verbs in fallback."""
        # Arrange
        mock_parse.return_value = []
        mock_vocab.expand_word.return_value = "look"
        mock_vocab.is_direction.return_value = False

        # Act
        result = parse_command_wrapper("l", online_sessions={})

        # Assert
        self.assertEqual(result[0]["verb"], "look")
        mock_vocab.expand_word.assert_called_with("l")

    @patch("commands.parser.vocabulary_manager")
    @patch("commands.parser.parse_command")
    def test_parse_command_wrapper_includes_subject_in_fallback(
        self, mock_parse, mock_vocab
    ):
        """Test parse_command_wrapper includes subject in fallback command."""
        # Arrange
        mock_parse.return_value = []
        mock_vocab.expand_word.side_effect = lambda x: x
        mock_vocab.is_direction.return_value = False

        # Act
        result = parse_command_wrapper("get sword", online_sessions={})

        # Assert
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")


class ParseCommandWrapperContextTest(unittest.TestCase):
    """Test parse_command_wrapper context handling."""

    @patch("commands.parser.parse_command")
    @patch("commands.parser.natural_language_parser")
    @patch("commands.parser.vocabulary_manager")
    def test_parse_command_wrapper_sets_mob_manager_from_context(
        self, mock_vocab, mock_nlp, mock_parse
    ):
        """Test parse_command_wrapper sets mob_manager from context."""
        # Arrange
        mock_parse.return_value = []
        mock_vocab.expand_word.side_effect = lambda x: x
        mock_vocab.is_direction.return_value = False

        mock_mob_manager = Mock()
        context = {"mob_manager": mock_mob_manager}

        # Act
        parse_command_wrapper("look", context=context, online_sessions={})

        # Assert
        mock_nlp.set_mob_manager.assert_called_once_with(mock_mob_manager)

    @patch("commands.parser.parse_command")
    @patch("commands.parser.vocabulary_manager")
    def test_parse_command_wrapper_extracts_player_from_context_dict(
        self, mock_vocab, mock_parse
    ):
        """Test parse_command_wrapper extracts player from context dictionary."""
        # Arrange
        mock_parse.return_value = [{"verb": "look"}]
        player = create_mock_player()
        game_state = create_mock_game_state()
        context = {"player": player, "game_state": game_state}

        # Act
        parse_command_wrapper("look", context=context, online_sessions={})

        # Assert
        mock_parse.assert_called_once()
        call_args = mock_parse.call_args[0]
        self.assertEqual(call_args[1], player)
        self.assertEqual(call_args[2], game_state)


if __name__ == "__main__":
    unittest.main()
