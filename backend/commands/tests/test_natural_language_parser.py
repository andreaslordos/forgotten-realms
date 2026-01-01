"""
Comprehensive tests for command parsing system.

Tests cover:
- Tokenization
- Vocabulary management (abbreviations, synonyms, directions)
- Context and pronoun resolution
- Syntax pattern matching
- Object binding
- Full command parsing
- Command chaining
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from commands.natural_language_parser import (
    tokenize,
    TokenType,
    VocabularyManager,
    CommandContext,
    SyntaxPattern,
    ObjectBinder,
    parse_command,
    is_movement_command,
)
from models.Player import Player
from models.Item import Item
from models.Room import Room
from managers.game_state import GameState


class TokenizationTest(unittest.TestCase):
    """Test command tokenization."""

    def test_tokenize_simple_command(self):
        """Test tokenizing a simple command."""
        tokens = tokenize("get sword")

        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].value, "get")
        self.assertEqual(tokens[1].value, "sword")

    def test_tokenize_with_quoted_string(self):
        """Test tokenizing command with quoted string."""
        tokens = tokenize('say "hello world"')

        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].value, "say")
        self.assertEqual(tokens[1].value, "hello world")
        self.assertEqual(tokens[1].type, TokenType.QUOTED_STRING)

    def test_tokenize_quote_prefix(self):
        """Test tokenizing command starting with quote."""
        tokens = tokenize('"hello everyone')

        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].value, "say")
        self.assertEqual(tokens[1].value, "hello everyone")

    def test_tokenize_with_numbers(self):
        """Test tokenizing command with numbers."""
        tokens = tokenize("drop 5 coins")

        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[1].type, TokenType.NUMBER)
        self.assertEqual(tokens[1].value, "5")

    def test_tokenize_empty_command(self):
        """Test tokenizing empty command."""
        tokens = tokenize("")

        self.assertEqual(len(tokens), 0)

    def test_tokenize_preserves_position(self):
        """Test that tokenization preserves character positions."""
        tokens = tokenize("look at sword")

        self.assertGreaterEqual(tokens[0].position, 0)
        self.assertLess(tokens[1].position, tokens[2].position)


class VocabularyManagementTest(unittest.TestCase):
    """Test vocabulary management."""

    def setUp(self):
        """Set up test vocabulary manager."""
        self.vocab = VocabularyManager()

    def test_expand_simple_abbreviation(self):
        """Test expanding simple abbreviations."""
        expanded = self.vocab.expand_word("g")

        self.assertEqual(expanded, "get")

    def test_expand_direction_abbreviation(self):
        """Test expanding direction abbreviations."""
        self.assertEqual(self.vocab.expand_word("n"), "north")
        self.assertEqual(self.vocab.expand_word("s"), "south")
        self.assertEqual(self.vocab.expand_word("e"), "east")
        self.assertEqual(self.vocab.expand_word("nw"), "northwest")

    def test_resolve_synonym(self):
        """Test resolving synonyms."""
        expanded = self.vocab.expand_word("grab")

        self.assertEqual(expanded, "get")

    def test_context_aware_abbreviation(self):
        """Test context-aware abbreviation expansion."""
        # "w" as first word (verb position) should expand to "west"
        expanded = self.vocab.expand_word("w", position=0, total_words=1)
        self.assertEqual(expanded, "west")

        # "w" in middle position should expand to "with"
        expanded = self.vocab.expand_word("w", position=1, total_words=3)
        self.assertEqual(expanded, "with")

    def test_add_custom_abbreviation(self):
        """Test adding custom abbreviations."""
        self.vocab.add_abbreviation("foo", "foobar")
        expanded = self.vocab.expand_word("foo")

        self.assertEqual(expanded, "foobar")

    def test_add_custom_synonym(self):
        """Test adding custom synonyms."""
        self.vocab.add_synonym("snatch", "get")
        expanded = self.vocab.expand_word("snatch")

        self.assertEqual(expanded, "get")

    def test_is_direction(self):
        """Test direction recognition."""
        self.assertTrue(self.vocab.is_direction("north"))
        self.assertTrue(self.vocab.is_direction("n"))
        self.assertFalse(self.vocab.is_direction("sword"))

    def test_is_preposition(self):
        """Test preposition recognition."""
        self.assertTrue(self.vocab.is_preposition("with"))
        self.assertTrue(self.vocab.is_preposition("to"))
        self.assertFalse(self.vocab.is_preposition("sword"))

    def test_preposition_types(self):
        """Test standard vs reversed preposition classification."""
        self.assertTrue(self.vocab.is_standard_preposition("with"))
        self.assertFalse(self.vocab.is_reversed_preposition("with"))

        self.assertTrue(self.vocab.is_reversed_preposition("to"))
        self.assertFalse(self.vocab.is_standard_preposition("to"))


class CommandContextTest(unittest.TestCase):
    """Test command context and pronoun resolution."""

    def setUp(self):
        """Set up test context."""
        self.context = CommandContext()

    def test_context_initialization(self):
        """Test context starts empty."""
        self.assertIsNone(self.context.last_verb)
        self.assertIsNone(self.context.last_subject)
        self.assertIsNone(self.context.last_instrument)

    def test_update_context_with_verb(self):
        """Test updating context with verb."""
        self.context.update(verb="get")

        self.assertEqual(self.context.last_verb, "get")

    def test_update_context_with_subject(self):
        """Test updating context with subject."""
        item = {"name": "sword", "is_creature": False}
        self.context.update(subject=item)

        self.assertEqual(self.context.last_subject, item)
        self.assertEqual(self.context.last_it, item)

    def test_resolve_pronoun_it(self):
        """Test resolving 'it' pronoun."""
        item = {"name": "sword"}
        self.context.update(subject=item)

        resolved = self.context.resolve_pronoun("it")

        self.assertEqual(resolved, item)

    def test_resolve_unset_pronoun(self):
        """Test resolving pronoun with no referent."""
        resolved = self.context.resolve_pronoun("it")

        self.assertIsNone(resolved)


class SyntaxPatternTest(unittest.TestCase):
    """Test syntax pattern matching."""

    def test_simple_verb_pattern(self):
        """Test simple verb-only pattern."""
        pattern = SyntaxPattern("VERB")
        tokens = tokenize("quit")

        matched, bindings = pattern.matches(tokens)

        self.assertTrue(matched)
        self.assertEqual(bindings["verb"], "quit")

    def test_verb_object_pattern(self):
        """Test verb-object pattern."""
        pattern = SyntaxPattern("VERB SUBJECT")
        tokens = tokenize("get sword")

        matched, bindings = pattern.matches(tokens)

        self.assertTrue(matched)
        self.assertEqual(bindings["verb"], "get")
        self.assertEqual(bindings["subject"], "sword")

    def test_standard_syntax_pattern(self):
        """Test standard syntax with preposition."""
        pattern = SyntaxPattern("VERB SUBJECT with INSTRUMENT")
        tokens = tokenize("attack goblin with sword")

        matched, bindings = pattern.matches(tokens)

        self.assertTrue(matched)
        self.assertEqual(bindings["verb"], "attack")
        self.assertEqual(bindings["subject"], "goblin")
        self.assertEqual(bindings["instrument"], "sword")
        self.assertEqual(bindings["preposition"], "with")

    def test_reversed_syntax_pattern(self):
        """Test reversed syntax with 'to' preposition."""
        pattern = SyntaxPattern("VERB INSTRUMENT to SUBJECT")
        tokens = tokenize("give sword to guard")

        matched, bindings = pattern.matches(tokens)

        self.assertTrue(matched)
        self.assertEqual(bindings["verb"], "give")
        self.assertEqual(bindings["instrument"], "sword")
        self.assertEqual(bindings["subject"], "guard")

    def test_pattern_no_match(self):
        """Test pattern that doesn't match."""
        pattern = SyntaxPattern("VERB SUBJECT with INSTRUMENT")
        tokens = tokenize("look")

        matched, bindings = pattern.matches(tokens)

        self.assertFalse(matched)

    def test_multi_word_subject(self):
        """Test pattern with multi-word subject."""
        pattern = SyntaxPattern("VERB SUBJECT")
        tokens = tokenize("get rusty old sword")

        matched, bindings = pattern.matches(tokens)

        self.assertTrue(matched)
        self.assertEqual(bindings["subject"], "rusty old sword")


class ObjectBindingTest(unittest.TestCase):
    """Test object binding to game objects."""

    def setUp(self):
        """Set up test environment."""
        self.player = Player("TestHero")
        self.game_state = GameState()
        self.room = Room("test_room", "Test Room", "A test room")
        self.game_state.add_room(self.room)
        self.player.set_current_room("test_room")
        self.context = CommandContext()
        self.binder = ObjectBinder()

    def test_bind_item_in_inventory(self):
        """Test binding to item in player inventory."""
        sword = Item("Sword", "sword_1", "A sharp sword")
        self.player.add_item(sword)

        bound = self.binder.bind_subject(
            "sword", self.player, self.game_state, self.context
        )

        self.assertEqual(bound, sword)

    def test_bind_item_in_room(self):
        """Test binding to item in room."""
        torch = Item("Torch", "torch_1", "A burning torch")
        self.room.add_item(torch)

        bound = self.binder.bind_subject(
            "torch", self.player, self.game_state, self.context
        )

        self.assertEqual(bound, torch)

    def test_bind_special_keyword_all(self):
        """Test binding special 'all' keyword."""
        bound = self.binder.bind_subject(
            "all", self.player, self.game_state, self.context
        )

        self.assertEqual(bound, "all")

    def test_bind_nonexistent_object(self):
        """Test binding to nonexistent object."""
        bound = self.binder.bind_subject(
            "dragon", self.player, self.game_state, self.context
        )

        self.assertIsNone(bound)

    def test_bind_instrument(self):
        """Test binding instrument."""
        sword = Item("Sword", "sword_1", "A sword")
        self.player.add_item(sword)

        bound = self.binder.bind_instrument(
            "sword", self.player, self.game_state, self.context
        )

        self.assertEqual(bound, sword)

    def test_bind_subject_matches_by_synonym_in_inventory(self):
        """Test binding subject matches item by synonym in inventory."""
        # Create item with synonyms
        knight_medallion = Item(
            "silver medallion",
            "medallion_1",
            "A silver medallion",
            synonyms=["medallion", "token", "badge"],
        )
        self.player.add_item(knight_medallion)

        # Should match by synonym "medallion"
        bound = self.binder.bind_subject(
            "medallion", self.player, self.game_state, self.context
        )
        self.assertEqual(bound, knight_medallion)

        # Should match by synonym "badge"
        bound = self.binder.bind_subject(
            "badge", self.player, self.game_state, self.context
        )
        self.assertEqual(bound, knight_medallion)

    def test_bind_subject_matches_by_synonym_in_room(self):
        """Test binding subject matches item by synonym in room."""
        # Create item with synonyms in room
        ghostly_knight = Item(
            "spectral knight",
            "ghost_knight",
            "A ghostly knight",
            synonyms=["knight", "ghost", "spirit", "specter"],
        )
        self.room.add_item(ghostly_knight)

        # Should match by synonym "ghost"
        bound = self.binder.bind_subject(
            "ghost", self.player, self.game_state, self.context
        )
        self.assertEqual(bound, ghostly_knight)

        # Should match by synonym "knight"
        bound = self.binder.bind_subject(
            "knight", self.player, self.game_state, self.context
        )
        self.assertEqual(bound, ghostly_knight)

    def test_bind_subject_matches_by_partial_name(self):
        """Test binding subject matches by partial name (substring)."""
        long_sword = Item("Long Sword", "sword_1", "A long sword")
        self.room.add_item(long_sword)

        # Should match by substring "sword"
        bound = self.binder.bind_subject(
            "sword", self.player, self.game_state, self.context
        )
        self.assertEqual(bound, long_sword)

    def test_bind_instrument_matches_by_synonym_in_inventory(self):
        """Test binding instrument matches item by synonym in inventory."""
        magic_key = Item(
            "golden key",
            "key_1",
            "A golden key",
            synonyms=["key", "gold key"],
        )
        self.player.add_item(magic_key)

        # Should match by synonym "key"
        bound = self.binder.bind_instrument(
            "key", self.player, self.game_state, self.context
        )
        self.assertEqual(bound, magic_key)

    def test_bind_instrument_matches_by_synonym_in_room(self):
        """Test binding instrument matches item by synonym in room."""
        ancient_lever = Item(
            "ancient lever",
            "lever_1",
            "An old lever",
            synonyms=["lever", "handle", "switch"],
        )
        self.room.add_item(ancient_lever)

        # Should match by synonym "handle"
        bound = self.binder.bind_instrument(
            "handle", self.player, self.game_state, self.context
        )
        self.assertEqual(bound, ancient_lever)


class FullCommandParsingTest(unittest.TestCase):
    """Test complete command parsing."""

    def setUp(self):
        """Set up test environment."""
        self.player = Player("TestHero")
        self.game_state = GameState()
        self.room = Room("test_room", "Test Room", "A test room")
        self.game_state.add_room(self.room)
        self.player.set_current_room("test_room")

    def test_parse_simple_command(self):
        """Test parsing simple one-word command."""
        commands = parse_command("quit", self.player, self.game_state)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "quit")

    def test_parse_movement_command(self):
        """Test parsing movement commands."""
        commands = parse_command("north", self.player, self.game_state)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "north")
        self.assertTrue(commands[0].get("is_movement", False))

    def test_parse_abbreviated_movement(self):
        """Test parsing abbreviated movement."""
        commands = parse_command("n", self.player, self.game_state)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "north")
        self.assertTrue(commands[0].get("is_movement", False))

    def test_parse_get_command(self):
        """Test parsing 'get' command."""
        sword = Item("Sword", "sword_1", "A sword")
        self.room.add_item(sword)

        commands = parse_command("get sword", self.player, self.game_state)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "get")
        self.assertEqual(commands[0]["subject"], "sword")
        self.assertEqual(commands[0]["subject_object"], sword)

    def test_parse_attack_with_weapon(self):
        """Test parsing attack command with weapon."""
        commands = parse_command(
            "attack goblin with sword", self.player, self.game_state
        )

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "attack")
        self.assertEqual(commands[0]["subject"], "goblin")
        self.assertEqual(commands[0]["instrument"], "sword")

    def test_parse_abbreviated_command(self):
        """Test parsing abbreviated commands."""
        commands = parse_command("g sword", self.player, self.game_state)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "get")
        self.assertEqual(commands[0]["subject"], "sword")

    def test_parse_say_command(self):
        """Test parsing say command."""
        commands = parse_command('"hello everyone', self.player, self.game_state)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "say")
        self.assertEqual(commands[0]["subject"], "hello everyone")

    def test_parse_empty_command(self):
        """Test parsing empty command."""
        commands = parse_command("", self.player, self.game_state)

        self.assertEqual(len(commands), 0)

    def test_parse_go_direction(self):
        """Test parsing 'go north' style commands."""
        commands = parse_command("go north", self.player, self.game_state)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "north")
        self.assertTrue(commands[0].get("is_movement", False))


class CommandChainingTest(unittest.TestCase):
    """Test command chaining functionality."""

    def setUp(self):
        """Set up test environment."""
        self.player = Player("TestHero")
        self.game_state = GameState()
        self.room = Room("test_room", "Test Room", "A test room")
        self.game_state.add_room(self.room)
        self.player.set_current_room("test_room")

    def test_parse_chained_commands_with_comma(self):
        """Test parsing commands chained with comma."""
        commands = parse_command("look, inventory", self.player, self.game_state)

        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0]["verb"], "look")
        self.assertEqual(commands[1]["verb"], "inventory")

    def test_parse_chained_commands_with_and(self):
        """Test parsing commands chained with 'and'."""
        commands = parse_command("look and inventory", self.player, self.game_state)

        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0]["verb"], "look")
        self.assertEqual(commands[1]["verb"], "inventory")

    def test_parse_chained_commands_with_then(self):
        """Test parsing commands chained with 'then'."""
        commands = parse_command("look then inventory", self.player, self.game_state)

        self.assertEqual(len(commands), 2)
        self.assertEqual(commands[0]["verb"], "look")
        self.assertEqual(commands[1]["verb"], "inventory")


class MovementCommandTest(unittest.TestCase):
    """Test movement command recognition."""

    def test_is_movement_command_north(self):
        """Test recognizing north as movement."""
        self.assertTrue(is_movement_command("north"))

    def test_is_movement_command_abbreviation(self):
        """Test recognizing abbreviated direction."""
        # Note: is_movement_command checks the expanded form
        self.assertTrue(is_movement_command("north"))

    def test_is_movement_command_diagonal(self):
        """Test recognizing diagonal directions."""
        self.assertTrue(is_movement_command("northeast"))
        self.assertTrue(is_movement_command("southwest"))

    def test_is_movement_command_special(self):
        """Test recognizing special directions."""
        self.assertTrue(is_movement_command("up"))
        self.assertTrue(is_movement_command("down"))
        self.assertTrue(is_movement_command("in"))
        self.assertTrue(is_movement_command("out"))

    def test_is_not_movement_command(self):
        """Test non-movement words."""
        self.assertFalse(is_movement_command("get"))
        self.assertFalse(is_movement_command("sword"))


class ParserIntegrationTest(unittest.TestCase):
    """Integration tests for the complete parser."""

    def setUp(self):
        """Set up test environment."""
        self.player = Player("TestHero")
        self.game_state = GameState()
        self.room = Room("test_room", "Test Room", "A test room")
        self.game_state.add_room(self.room)
        self.player.set_current_room("test_room")

        # Add some items
        self.sword = Item("Sword", "sword_1", "A sharp sword")
        self.shield = Item("Shield", "shield_1", "A sturdy shield")
        self.room.add_item(self.sword)
        self.room.add_item(self.shield)

    def test_get_and_drop_sequence(self):
        """Test realistic sequence: get item then drop it."""
        # Get the sword
        commands1 = parse_command("get sword", self.player, self.game_state)
        self.assertEqual(commands1[0]["verb"], "get")
        self.assertEqual(commands1[0]["subject_object"], self.sword)

        # Simulate picking it up
        self.player.add_item(self.sword)
        self.room.remove_item(self.sword)

        # Drop the sword
        commands2 = parse_command("drop sword", self.player, self.game_state)
        self.assertEqual(commands2[0]["verb"], "drop")
        self.assertEqual(commands2[0]["subject_object"], self.sword)

    def test_complex_multi_word_command(self):
        """Test parsing complex command with multi-word references."""
        rusty_sword = Item("Rusty Sword", "rusty_sword_1", "An old rusty sword")
        self.room.add_item(rusty_sword)

        commands = parse_command("get rusty sword", self.player, self.game_state)

        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]["verb"], "get")
        # The parser will try to match "rusty sword" to objects

    def test_inventory_command(self):
        """Test inventory command and abbreviation."""
        commands1 = parse_command("inventory", self.player, self.game_state)
        commands2 = parse_command("i", self.player, self.game_state)

        self.assertEqual(commands1[0]["verb"], "inventory")
        self.assertEqual(commands2[0]["verb"], "inventory")

    def test_look_command_variations(self):
        """Test various forms of look command."""
        commands1 = parse_command("look", self.player, self.game_state)
        commands2 = parse_command("l", self.player, self.game_state)

        self.assertEqual(commands1[0]["verb"], "look")
        self.assertEqual(commands2[0]["verb"], "look")


class ErrorClassTest(unittest.TestCase):
    """Test error classes for coverage."""

    def test_unknown_word_error(self):
        """Test UnknownWordError instantiation."""
        from commands.natural_language_parser import UnknownWordError

        error = UnknownWordError("xyzzy")
        self.assertEqual(error.word, "xyzzy")
        self.assertIn("xyzzy", str(error))

    def test_ambiguous_reference_error(self):
        """Test AmbiguousReferenceError instantiation."""
        from commands.natural_language_parser import AmbiguousReferenceError

        error = AmbiguousReferenceError("key", ["bronze key", "silver key"])
        self.assertEqual(error.noun, "key")
        self.assertEqual(error.options, ["bronze key", "silver key"])
        self.assertIn("key", str(error))

    def test_missing_object_error(self):
        """Test MissingObjectError instantiation."""
        from commands.natural_language_parser import MissingObjectError

        error = MissingObjectError("get")
        self.assertEqual(error.verb, "get")
        self.assertIn("get", str(error))

    def test_syntax_error(self):
        """Test SyntaxError instantiation."""
        from commands.natural_language_parser import SyntaxError as ParserSyntaxError

        error = ParserSyntaxError("Invalid syntax")
        self.assertIn("Invalid", str(error))


class AdditionalCoverageTest(unittest.TestCase):
    """Additional tests to increase coverage."""

    def test_tokenize_with_punctuation(self):
        """Test tokenizing command with punctuation (space separated)."""
        tokens = tokenize("look !")

        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[1].type, TokenType.PUNCTUATION)
        self.assertEqual(tokens[1].value, "!")

    def test_context_aware_abbreviation_in_new_context(self):
        """Test adding context-aware abbreviation with new context."""
        vocab = VocabularyManager()

        # Add a context-aware abbreviation
        vocab.add_abbreviation("test", "testing", context="special")

        self.assertIn("test", vocab.abbreviations)
        self.assertIsInstance(vocab.abbreviations["test"], dict)

    def test_add_abbreviation_to_existing_context_dict(self):
        """Test adding abbreviation to existing context dictionary."""
        vocab = VocabularyManager()

        # First add with a context - creates {"default": "xyzzy"}
        vocab.add_abbreviation("xyz", "xyzzy", context="context1")
        # Then add another context
        vocab.add_abbreviation("xyz", "xyzzy2", context="context2")

        # The first addition creates a default entry, not context1
        self.assertIn("default", vocab.abbreviations["xyz"])
        self.assertIn("context2", vocab.abbreviations["xyz"])

    def test_add_abbreviation_convert_simple_to_context(self):
        """Test converting simple abbreviation to context-aware."""
        vocab = VocabularyManager()

        # First add as simple
        vocab.add_abbreviation("abc", "alphabet")
        # Then add with context
        vocab.add_abbreviation("abc", "abacus", context="math")

        self.assertIsInstance(vocab.abbreviations["abc"], dict)
        self.assertEqual(vocab.abbreviations["abc"]["default"], "alphabet")
        self.assertEqual(vocab.abbreviations["abc"]["math"], "abacus")

    def test_add_abbreviation_update_default_in_dict(self):
        """Test updating default value in context-aware abbreviation."""
        vocab = VocabularyManager()

        # First add with context
        vocab.add_abbreviation("def", "definition", context="special")
        # Then update the default
        vocab.add_abbreviation("def", "default_value")

        self.assertEqual(vocab.abbreviations["def"]["default"], "default_value")

    def test_add_preposition(self):
        """Test adding custom preposition."""
        vocab = VocabularyManager()

        vocab.add_preposition("via", "standard")

        self.assertIn("via", vocab.prepositions)
        self.assertEqual(vocab.preposition_types["via"], "standard")

    def test_add_adverb(self):
        """Test adding custom adverb."""
        vocab = VocabularyManager()

        vocab.add_adverb("swiftly")

        self.assertIn("swiftly", vocab.adverbs)

    def test_is_adverb(self):
        """Test checking if word is an adverb."""
        vocab = VocabularyManager()

        self.assertTrue(vocab.is_adverb("quickly"))
        self.assertFalse(vocab.is_adverb("sword"))


if __name__ == "__main__":
    unittest.main()
