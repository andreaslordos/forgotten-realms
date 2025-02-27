# backend/tests/test_parser.py

import unittest
import logging
from commands.parser import (
    CommandContext, 
    parse_command_string, 
    parse_single_command, 
    parse_command,
    DIRECTION_ALIASES,
    COMMAND_ABBREVIATIONS
)

# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCommandContext(unittest.TestCase):
    """Tests for the CommandContext class."""
    
    def test_init(self):
        """Test that CommandContext initializes correctly."""
        context = CommandContext()
        self.assertIsNone(context.last_verb)
        self.assertIsNone(context.last_subject)
        self.assertIsNone(context.last_object)
        self.assertIsNone(context.last_instrument)
        self.assertIsNone(context.last_player)
        self.assertIsNone(context.last_male)
        self.assertIsNone(context.last_female)
        self.assertIsNone(context.last_it)
    
    def test_update(self):
        """Test that update() correctly updates the context."""
        context = CommandContext()
        context.update("look", "sword", None, None, False)
        self.assertEqual(context.last_verb, "look")
        self.assertEqual(context.last_subject, "sword")
        self.assertEqual(context.last_it, "sword")
        self.assertIsNone(context.last_object)
        self.assertIsNone(context.last_instrument)
        
        # Test updating with a player
        context.update("tell", "bob", None, "hello", True, "M")
        self.assertEqual(context.last_verb, "tell")
        self.assertEqual(context.last_subject, "bob")
        self.assertEqual(context.last_male, "bob")
        self.assertEqual(context.last_player, "bob")
        self.assertIsNone(context.last_object)
        self.assertEqual(context.last_instrument, "hello")
    
    def test_resolve_pronoun(self):
        """Test that resolve_pronoun() correctly resolves pronouns."""
        context = CommandContext()
        
        # No pronouns set yet
        self.assertEqual(context.resolve_pronoun("it"), "it")
        self.assertEqual(context.resolve_pronoun("him"), "him")
        self.assertEqual(context.resolve_pronoun("her"), "her")
        self.assertEqual(context.resolve_pronoun("them"), "them")
        
        # Set pronouns
        context.update("look", "sword", None, None, False)
        context.update("tell", "bob", None, "hello", True, "M")
        context.update("tell", "alice", None, "hi", True, "F")
        
        self.assertEqual(context.resolve_pronoun("it"), "sword")
        self.assertEqual(context.resolve_pronoun("him"), "bob")
        self.assertEqual(context.resolve_pronoun("her"), "alice")
        self.assertEqual(context.resolve_pronoun("them"), "alice")  # Last player referenced


class TestParseCommandString(unittest.TestCase):
    """Tests for parse_command_string function."""
    
    def test_basic_command(self):
        """Test parsing a basic command."""
        context = CommandContext()
        result = parse_command_string("look", context)
        self.assertEqual(len(result), 1, f"Expected one command, got {len(result)}: {result}")
        self.assertEqual(result[0]["verb"], "look")
        self.assertIsNone(result[0]["subject"])
    
    def test_command_with_subject(self):
        """Test parsing a command with a subject."""
        context = CommandContext()
        result = parse_command_string("get sword", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
    
    def test_command_with_instrument(self):
        """Test parsing a command with an instrument."""
        context = CommandContext()
        result = parse_command_string("unlock door with key", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "unlock")
        self.assertEqual(result[0]["subject"], "door")
        self.assertEqual(result[0]["instrument"], "key")
    
    def test_command_with_abbreviations(self):
        """Test parsing a command with abbreviations."""
        context = CommandContext()
        result = parse_command_string("g sword", context, {"g": "get"})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
    
    def test_multiple_commands(self):
        """Test parsing multiple commands separated by conjunctions."""
        context = CommandContext()
        result = parse_command_string("get sword and drop axe", context)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
        self.assertEqual(result[1]["verb"], "drop")
        self.assertEqual(result[1]["subject"], "axe")
        
        # Test other conjunctions
        result = parse_command_string("get sword then drop axe", context)
        self.assertEqual(len(result), 2)
        
        result = parse_command_string("get sword, drop axe", context)
        self.assertEqual(len(result), 2)
        
        result = parse_command_string("get sword. drop axe", context)
        self.assertEqual(len(result), 2)


class TestParseSingleCommand(unittest.TestCase):
    """Tests for parse_single_command function."""
    
    def test_basic_parsing(self):
        """Test basic command parsing."""
        context = CommandContext()
        
        result = parse_single_command("look", context, {})
        self.assertIsNotNone(result, "parse_single_command returned None for 'look'")
        self.assertEqual(result["verb"], "look")
        self.assertIsNone(result["subject"])
        self.assertIsNone(result["instrument"])
        
        result = parse_single_command("get sword", context, {})
        self.assertIsNotNone(result)
        self.assertEqual(result["verb"], "get")
        self.assertEqual(result["subject"], "sword")
        self.assertIsNone(result["instrument"])
        
        result = parse_single_command("unlock door with key", context, {})
        self.assertIsNotNone(result)
        self.assertEqual(result["verb"], "unlock")
        self.assertEqual(result["subject"], "door")
        self.assertEqual(result["instrument"], "key")
    
    def test_abbreviated_verb(self):
        """Test parsing with an abbreviated verb."""
        context = CommandContext()
        abbrevs = {"g": "get", "l": "look"}
        
        result = parse_single_command("g sword", context, abbrevs)
        self.assertIsNotNone(result)
        self.assertEqual(result["verb"], "get")
        self.assertEqual(result["subject"], "sword")
        
        result = parse_single_command("l", context, abbrevs)
        self.assertIsNotNone(result)
        self.assertEqual(result["verb"], "look")
        self.assertIsNone(result["subject"])
    
    def test_with_equivalents(self):
        """Test various prepositions that can substitute for 'with'."""
        context = CommandContext()
        
        for equiv in ["with", "using", "by", "via", "at", "to", "from"]:
            cmd = f"attack troll {equiv} sword"
            result = parse_single_command(cmd, context, {})
            self.assertIsNotNone(result, f"parse_single_command returned None for '{cmd}'")
            self.assertEqual(result["verb"], "attack")
            self.assertEqual(result["subject"], "troll")
            self.assertEqual(result["instrument"], "sword")
    
    def test_pronoun_resolution(self):
        """Test resolving pronouns in commands."""
        context = CommandContext()
        # First, update context with 'sword' as 'it' and 'bob' as 'him'
        context.update("look", "sword", None, None, False)
        context.update("tell", "bob", None, None, True, "M")
        
        # Test 'get it' -> 'get sword'
        result = parse_single_command("get it", context, {})
        self.assertIsNotNone(result, "parse_single_command returned None for 'get it'")
        self.assertEqual(result["verb"], "get")
        self.assertEqual(result["subject"], "sword")
        
        # Test 'tell him hello' -> 'tell bob hello'
        result = parse_single_command("tell him hello", context, {})
        self.assertIsNotNone(result, "parse_single_command returned None for 'tell him hello'")
        self.assertEqual(result["verb"], "tell")
        self.assertEqual(result["subject"], "bob", f"Expected 'bob', got {result['subject']}")
        self.assertEqual(result["instrument"], "hello")


class TestParseCommand(unittest.TestCase):
    """Tests for the main parse_command function."""
    
    def test_movement_commands(self):
        """Test parsing movement commands."""
        context = CommandContext()
        
        # Test each direction alias individually
        for alias, full in DIRECTION_ALIASES.items():
            result = parse_command(alias, context)
            self.assertEqual(len(result), 1, f"Failed on alias: {alias}")
            self.assertEqual(result[0]["verb"], full, f"Failed on alias: {alias}, got verb: {result[0]['verb']}")
            self.assertIsNone(result[0]["subject"])
        
        # Test with 'go' prefix
        result = parse_command("go north", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "north")
        self.assertIsNone(result[0]["subject"])
    
    def test_command_abbreviations(self):
        """Test command abbreviations."""
        context = CommandContext()
        
        # Test a subset of abbreviations that don't conflict with directions
        safe_abbreviations = {"g": "get", "l": "look", "dr": "drop", "sc": "score", "qq": "quit", "i": "inventory"}
        for abbrev, full in safe_abbreviations.items():
            result = parse_command(abbrev, context)
            self.assertEqual(len(result), 1, f"Failed on abbreviation: {abbrev}")
            self.assertEqual(result[0]["verb"], full, f"Failed on abbreviation: {abbrev}, expected: {full}, got: {result[0]['verb']}")
    
    def test_complex_command(self):
        """Test a more complex command scenario."""
        context = CommandContext()
        
        # First, update the context so 'it' refers to 'sword'
        context.update("look", "sword", None, None, False)
        
        # Test "get it" command
        result = parse_command("get it", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
        
        # Test command chaining
        result = parse_command("get sword and drop it and go north", context)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
        self.assertEqual(result[1]["verb"], "drop")
        self.assertEqual(result[1]["subject"], "sword")  # 'it' should resolve to 'sword'
        self.assertEqual(result[2]["verb"], "north")


if __name__ == "__main__":
    unittest.main(verbosity=2)