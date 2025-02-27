# backend/tests/test_edge_cases.py

import unittest
import logging
from commands.parser import (
    CommandContext, 
    parse_command_string, 
    parse_single_command, 
    parse_command
)

# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestParserEdgeCases(unittest.TestCase):
    """Test edge cases for the command parser."""
    
    def test_empty_input(self):
        """Test empty input."""
        context = CommandContext()
        
        # Empty string
        result = parse_command_string("", context)
        self.assertEqual(len(result), 0)
        
        # Whitespace string
        result = parse_command_string("   ", context)
        self.assertEqual(len(result), 0)
        
        # None input - should handle gracefully
        result = parse_command_string(None, context)
        self.assertEqual(len(result), 0)
    
    def test_extra_whitespace(self):
        """Test commands with extra whitespace."""
        context = CommandContext()
        
        # Extra whitespace before command
        result = parse_command_string("   look", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "look")
        
        # Extra whitespace after command
        result = parse_command_string("look   ", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "look")
        
        # Extra whitespace between tokens
        result = parse_command_string("get   sword", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
        
        # Multiple whitespace in conjunctions
        result = parse_command_string("get sword   and   drop shield", context)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
        self.assertEqual(result[1]["verb"], "drop")
        self.assertEqual(result[1]["subject"], "shield")
    
    def test_case_insensitivity(self):
        """Test case insensitivity."""
        context = CommandContext()
        
        # Mixed case verb
        result = parse_command_string("LoOk", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "look")
        
        # Mixed case subject
        result = parse_command_string("get SwoRD", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
        
        # Mixed case instrument
        result = parse_command_string("unlock door with KeY", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "unlock")
        self.assertEqual(result[0]["subject"], "door")
        self.assertEqual(result[0]["instrument"], "key")
    
    def test_multiple_conjunctions(self):
        """Test commands with multiple conjunctions."""
        context = CommandContext()
        
        # Multiple 'and's
        result = parse_command_string("get sword and drop axe and go north", context)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
        self.assertEqual(result[1]["verb"], "drop")
        self.assertEqual(result[1]["subject"], "axe")
        self.assertEqual(result[2]["verb"], "go")
        self.assertEqual(result[2]["subject"], "north")
        
        # Mixed conjunctions
        result = parse_command_string("get sword, drop axe, then go north", context)
        self.assertEqual(len(result), 3)
        
        # Empty segments in between conjunctions
        result = parse_command_string("get sword,, drop axe", context)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword")
        self.assertEqual(result[1]["verb"], "drop")
        self.assertEqual(result[1]["subject"], "axe")
    
    def test_multi_word_subjects(self):
        """Test commands with multi-word subjects."""
        context = CommandContext()
        
        # Multi-word subject
        result = parse_command_string("get rusty old sword", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "rusty old sword")
        
        # Multi-word subject and instrument
        result = parse_command_string("attack large troll with sharp magical sword", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "attack")
        self.assertEqual(result[0]["subject"], "large troll")
        self.assertEqual(result[0]["instrument"], "sharp magical sword")
    
    def test_special_with_equivalents(self):
        """Test different prepositions equivalent to 'with'."""
        context = CommandContext()
        
        # Test various prepositions
        prepositions = ["with", "using", "via", "by", "at", "to", "from"]
        for prep in prepositions:
            cmd = f"hit troll {prep} sword"
            result = parse_command_string(cmd, context)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["verb"], "hit")
            self.assertEqual(result[0]["subject"], "troll")
            self.assertEqual(result[0]["instrument"], "sword")
    
    def test_context_persistence(self):
        """Test that context persists between commands."""
        context = CommandContext()
        
        # First set a subject
        parse_command_string("look at sword", context)
        
        # Then reference it with a pronoun
        result = parse_command_string("get it", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "it")  # Pronoun not resolved here, just stored
        
        # Check the context for proper pronoun resolution
        self.assertEqual(context.last_it, "it")
        self.assertEqual(context.last_subject, "it")
    
    def test_multi_word_verbs(self):
        """Test handling of multi-word verbs (which aren't really supported)."""
        context = CommandContext()
        
        # Multi-word verb - first word is treated as the verb
        result = parse_command_string("pick up sword", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "pick")
        self.assertEqual(result[0]["subject"], "up sword")


class TestCommandExecutionEdgeCases(unittest.TestCase):
    """Test edge cases for command execution."""
    
    def test_ambiguous_command_abbreviations(self):
        """Test handling of ambiguous command abbreviations."""
        context = CommandContext()
        
        # Test "i" which could mean either "inventory" or "in"
        result = parse_command("i", context)
        self.assertEqual(len(result), 1)
        # We've set up the parser to prioritize "inventory" for "i"
        self.assertEqual(result[0]["verb"], "inventory")
        
        # Test "u" which could mean either "users" or "up"
        result = parse_command("u", context)
        self.assertEqual(len(result), 1)
        # We've set up the parser to prioritize "up" for "u"
        self.assertEqual(result[0]["verb"], "up")
    
    def test_command_repetition(self):
        """Test repeated command tokens."""
        context = CommandContext()
        
        # Repeated verbs
        result = parse_command_string("look look", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "look")
        self.assertEqual(result[0]["subject"], "look")
        
        # Repeated subjects
        result = parse_command_string("get sword sword", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "sword sword")
    
    def test_excessive_tokens(self):
        """Test commands with excessive tokens."""
        context = CommandContext()
        
        # Many tokens
        result = parse_command_string("get the rusted ancient magical golden sword with my two bare hands", context)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["verb"], "get")
        self.assertEqual(result[0]["subject"], "the rusted ancient magical golden sword")
        self.assertEqual(result[0]["instrument"], "my two bare hands")


if __name__ == "__main__":
    unittest.main()