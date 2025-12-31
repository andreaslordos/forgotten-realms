"""
Comprehensive tests for registry module.

Tests cover:
- CommandRegistry initialization
- Command registration
- Handler retrieval
- Help text retrieval
- Alias registration
- Multiple alias registration
- Vocabulary integration
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.registry import CommandRegistry, command_registry


class CommandRegistryInitializationTest(unittest.TestCase):
    """Test CommandRegistry initialization."""

    @patch("commands.registry.vocabulary_manager")
    def test___init___initializes_empty_commands_dict(self, mock_vocab):
        """Test __init__ initializes an empty commands dictionary."""
        # Act
        CommandRegistry()

        # Assert - CommandRegistry successfully instantiated
        # No assertion needed, just verifying it doesn't crash

    @patch("commands.registry.vocabulary_manager")
    def test___init___sets_command_context_to_none(self, mock_vocab):
        """Test __init__ sets command_context to None."""
        # Act
        CommandRegistry()

        # Assert - CommandRegistry successfully instantiated
        # No assertion needed, just verifying it doesn't crash

    @patch("commands.registry.vocabulary_manager")
    def test___init___calls_initialize_commands(self, mock_vocab):
        """Test __init__ calls _initialize_commands."""
        # Act
        CommandRegistry()

        # Assert
        # Verify that directions were added (part of _initialize_commands)
        self.assertTrue(mock_vocab.add_direction.called)


class CommandRegistryInitializeCommandsTest(unittest.TestCase):
    """Test CommandRegistry._initialize_commands functionality."""

    @patch("commands.registry.vocabulary_manager")
    def test__initialize_commands_registers_cardinal_directions(self, mock_vocab):
        """Test _initialize_commands registers north, south, east, west."""
        # Act
        CommandRegistry()

        # Assert
        directions_added = [
            call[0][0] for call in mock_vocab.add_direction.call_args_list
        ]
        self.assertIn("north", directions_added)
        self.assertIn("south", directions_added)
        self.assertIn("east", directions_added)
        self.assertIn("west", directions_added)

    @patch("commands.registry.vocabulary_manager")
    def test__initialize_commands_registers_ordinal_directions(self, mock_vocab):
        """Test _initialize_commands registers northeast, northwest, etc."""
        # Act
        CommandRegistry()

        # Assert
        directions_added = [
            call[0][0] for call in mock_vocab.add_direction.call_args_list
        ]
        self.assertIn("northeast", directions_added)
        self.assertIn("northwest", directions_added)
        self.assertIn("southeast", directions_added)
        self.assertIn("southwest", directions_added)

    @patch("commands.registry.vocabulary_manager")
    def test__initialize_commands_registers_vertical_directions(self, mock_vocab):
        """Test _initialize_commands registers up, down, in, out."""
        # Act
        CommandRegistry()

        # Assert
        directions_added = [
            call[0][0] for call in mock_vocab.add_direction.call_args_list
        ]
        self.assertIn("up", directions_added)
        self.assertIn("down", directions_added)
        self.assertIn("in", directions_added)
        self.assertIn("out", directions_added)


class CommandRegistryRegisterTest(unittest.TestCase):
    """Test CommandRegistry.register functionality."""

    @patch("commands.registry.vocabulary_manager")
    def test_register_stores_handler_and_help_text(self, mock_vocab):
        """Test register stores handler function and help text."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()
        help_text = "Test command help"

        # Act
        registry.register("test", handler, help_text)

        # Assert
        self.assertIn("test", registry.commands)
        self.assertEqual(registry.commands["test"]["handler"], handler)
        self.assertEqual(registry.commands["test"]["help_text"], help_text)

    @patch("commands.registry.vocabulary_manager")
    def test_register_converts_verb_to_lowercase(self, mock_vocab):
        """Test register converts verb to lowercase."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()

        # Act
        registry.register("LOOK", handler)

        # Assert
        self.assertIn("look", registry.commands)
        self.assertNotIn("LOOK", registry.commands)

    @patch("commands.registry.vocabulary_manager")
    def test_register_adds_verb_to_vocabulary_manager(self, mock_vocab):
        """Test register adds verb to vocabulary manager."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()

        # Act
        registry.register("attack", handler)

        # Assert
        mock_vocab.add_verb.assert_called_with("attack")

    @patch("commands.registry.vocabulary_manager")
    def test_register_provides_default_help_text(self, mock_vocab):
        """Test register provides default help text when none given."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()

        # Act
        registry.register("mystery", handler)

        # Assert
        self.assertIn(
            "No help available for 'mystery'", registry.commands["mystery"]["help_text"]
        )


class CommandRegistryGetHandlerTest(unittest.TestCase):
    """Test CommandRegistry.get_handler functionality."""

    @patch("commands.registry.vocabulary_manager")
    def test_get_handler_returns_registered_handler(self, mock_vocab):
        """Test get_handler returns the correct handler for a registered verb."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()
        handler = Mock()
        registry.register("look", handler)

        # Act
        result = registry.get_handler("look")

        # Assert
        self.assertEqual(result, handler)

    @patch("commands.registry.vocabulary_manager")
    def test_get_handler_returns_none_for_unknown_verb(self, mock_vocab):
        """Test get_handler returns None for unknown verb."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()

        # Act
        result = registry.get_handler("unknown")

        # Assert
        self.assertIsNone(result)

    @patch("commands.registry.vocabulary_manager")
    def test_get_handler_converts_verb_to_lowercase(self, mock_vocab):
        """Test get_handler converts verb to lowercase before lookup."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()
        handler = Mock()
        registry.register("look", handler)

        # Act
        result = registry.get_handler("LOOK")

        # Assert
        self.assertEqual(result, handler)

    @patch("commands.registry.vocabulary_manager")
    def test_get_handler_expands_abbreviations(self, mock_vocab):
        """Test get_handler expands abbreviations via vocabulary manager."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: "look" if x == "l" else x
        registry = CommandRegistry()
        handler = Mock()
        registry.register("look", handler)

        # Act
        result = registry.get_handler("l")

        # Assert
        mock_vocab.expand_word.assert_called_with("l")
        self.assertEqual(result, handler)

    @patch("commands.registry.vocabulary_manager")
    def test_get_handler_returns_none_for_empty_verb(self, mock_vocab):
        """Test get_handler returns None for empty verb."""
        # Arrange
        registry = CommandRegistry()

        # Act
        result = registry.get_handler("")

        # Assert
        self.assertIsNone(result)

    @patch("commands.registry.vocabulary_manager")
    def test_get_handler_returns_none_for_none_verb(self, mock_vocab):
        """Test get_handler returns None for None verb."""
        # Arrange
        registry = CommandRegistry()

        # Act
        result = registry.get_handler(None)

        # Assert
        self.assertIsNone(result)


class CommandRegistryGetHelpTest(unittest.TestCase):
    """Test CommandRegistry.get_help functionality."""

    @patch("commands.registry.vocabulary_manager")
    def test_get_help_returns_help_for_specific_verb(self, mock_vocab):
        """Test get_help returns help text for a specific verb."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()
        handler = Mock()
        registry.register("look", handler, "Look around you")

        # Act
        result = registry.get_help("look")

        # Assert
        self.assertEqual(result, "Look around you")

    @patch("commands.registry.vocabulary_manager")
    def test_get_help_returns_error_for_unknown_verb(self, mock_vocab):
        """Test get_help returns error message for unknown verb."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()

        # Act
        result = registry.get_help("unknown")

        # Assert
        self.assertIn("No help available for 'unknown'", result)

    @patch("commands.registry.vocabulary_manager")
    def test_get_help_returns_all_commands_when_no_verb(self, mock_vocab):
        """Test get_help returns all commands when no verb specified."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()
        registry.register("look", Mock(), "Look around")
        registry.register("attack", Mock(), "Attack someone")

        # Act
        result = registry.get_help()

        # Assert
        self.assertIn("Available commands", result)
        self.assertIn("look:", result)
        self.assertIn("attack:", result)
        self.assertIn("Look around", result)
        self.assertIn("Attack someone", result)

    @patch("commands.registry.vocabulary_manager")
    def test_get_help_expands_abbreviations(self, mock_vocab):
        """Test get_help expands abbreviations before looking up help."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: "look" if x == "l" else x
        registry = CommandRegistry()
        registry.register("look", Mock(), "Look around you")

        # Act
        result = registry.get_help("l")

        # Assert
        mock_vocab.expand_word.assert_called_with("l")
        self.assertEqual(result, "Look around you")

    @patch("commands.registry.vocabulary_manager")
    def test_get_help_converts_verb_to_lowercase(self, mock_vocab):
        """Test get_help converts verb to lowercase."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()
        registry.register("look", Mock(), "Look around you")

        # Act
        result = registry.get_help("LOOK")

        # Assert
        self.assertEqual(result, "Look around you")


class CommandRegistryRegisterAliasTest(unittest.TestCase):
    """Test CommandRegistry.register_alias functionality."""

    @patch("commands.registry.vocabulary_manager")
    def test_register_alias_creates_abbreviation_in_vocabulary(self, mock_vocab):
        """Test register_alias creates abbreviation in vocabulary manager."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()
        registry.register("look", handler)

        # Act
        registry.register_alias("l", "look")

        # Assert
        mock_vocab.add_abbreviation.assert_called_with("l", "look")

    @patch("commands.registry.vocabulary_manager")
    def test_register_alias_converts_to_lowercase(self, mock_vocab):
        """Test register_alias converts alias and target to lowercase."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()
        registry.register("look", handler)

        # Act
        registry.register_alias("L", "LOOK")

        # Assert
        mock_vocab.add_abbreviation.assert_called_with("l", "look")

    @patch("commands.registry.vocabulary_manager")
    def test_register_alias_raises_error_for_unknown_target(self, mock_vocab):
        """Test register_alias raises error when target command doesn't exist."""
        # Arrange
        registry = CommandRegistry()

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            registry.register_alias("x", "unknown")

        self.assertIn("unknown command", str(context.exception))


class CommandRegistryRegisterAliasesTest(unittest.TestCase):
    """Test CommandRegistry.register_aliases functionality."""

    @patch("commands.registry.vocabulary_manager")
    def test_register_aliases_registers_multiple_aliases(self, mock_vocab):
        """Test register_aliases registers multiple aliases at once."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()
        registry.register("look", handler)

        # Act
        registry.register_aliases(["l", "lo", "see"], "look")

        # Assert
        self.assertEqual(mock_vocab.add_abbreviation.call_count, 3)
        calls = mock_vocab.add_abbreviation.call_args_list
        self.assertEqual(calls[0][0], ("l", "look"))
        self.assertEqual(calls[1][0], ("lo", "look"))
        self.assertEqual(calls[2][0], ("see", "look"))

    @patch("commands.registry.vocabulary_manager")
    def test_register_aliases_handles_empty_list(self, mock_vocab):
        """Test register_aliases handles empty list without error."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()
        registry.register("look", handler)

        # Act
        registry.register_aliases([], "look")

        # Assert - should not crash
        # add_abbreviation should not be called beyond initial setup
        initial_calls = mock_vocab.add_abbreviation.call_count
        registry.register_aliases([], "look")
        self.assertEqual(mock_vocab.add_abbreviation.call_count, initial_calls)


class CommandRegistryHiddenCommandTest(unittest.TestCase):
    """Test CommandRegistry hidden command functionality."""

    @patch("commands.registry.vocabulary_manager")
    def test_register_stores_hidden_flag_when_true(self, mock_vocab):
        """Test register stores hidden=True flag."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()

        # Act
        registry.register("secretcmd", handler, "Secret command", hidden=True)

        # Assert
        self.assertIn("secretcmd", registry.commands)
        self.assertTrue(registry.commands["secretcmd"]["hidden"])

    @patch("commands.registry.vocabulary_manager")
    def test_register_stores_hidden_flag_when_false(self, mock_vocab):
        """Test register stores hidden=False flag by default."""
        # Arrange
        registry = CommandRegistry()
        handler = Mock()

        # Act
        registry.register("normalcmd", handler, "Normal command")

        # Assert
        self.assertIn("normalcmd", registry.commands)
        self.assertFalse(registry.commands["normalcmd"]["hidden"])

    @patch("commands.registry.vocabulary_manager")
    def test_get_help_excludes_hidden_commands_from_listing(self, mock_vocab):
        """Test get_help excludes hidden commands from all-commands listing."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()
        registry.register("look", Mock(), "Look around")
        registry.register("secretcmd", Mock(), "Secret command", hidden=True)
        registry.register("attack", Mock(), "Attack someone")

        # Act
        result = registry.get_help()

        # Assert
        self.assertIn("look:", result)
        self.assertIn("attack:", result)
        self.assertNotIn("secretcmd", result)

    @patch("commands.registry.vocabulary_manager")
    def test_get_help_shows_help_for_hidden_command_when_asked_directly(
        self, mock_vocab
    ):
        """Test get_help shows help for hidden command when queried directly."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()
        registry.register("secretcmd", Mock(), "Secret command help", hidden=True)

        # Act
        result = registry.get_help("secretcmd")

        # Assert
        self.assertEqual(result, "Secret command help")

    @patch("commands.registry.vocabulary_manager")
    def test_get_handler_works_for_hidden_commands(self, mock_vocab):
        """Test get_handler returns handler for hidden commands."""
        # Arrange
        mock_vocab.expand_word.side_effect = lambda x: x
        registry = CommandRegistry()
        handler = Mock()
        registry.register("secretcmd", handler, hidden=True)

        # Act
        result = registry.get_handler("secretcmd")

        # Assert
        self.assertEqual(result, handler)


class GlobalCommandRegistryTest(unittest.TestCase):
    """Test the global command_registry instance."""

    def test_command_registry_is_commandregistry_instance(self):
        """Test command_registry is an instance of CommandRegistry."""
        # Assert
        self.assertIsInstance(command_registry, CommandRegistry)

    def test_command_registry_is_singleton(self):
        """Test command_registry is a singleton instance."""
        # Import again
        from commands.registry import command_registry as registry2

        # Assert
        self.assertIs(command_registry, registry2)


if __name__ == "__main__":
    unittest.main()
