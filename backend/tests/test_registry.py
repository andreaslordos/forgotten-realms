# backend/tests/test_registry.py

import unittest
import logging
from commands.registry import CommandRegistry

# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockHandler:
    """Mock command handler for testing."""
    
    def __init__(self):
        self.called = False
        self.last_args = None
    
    async def handle(self, *args, **kwargs):
        self.called = True
        self.last_args = args
        return "Mock handler called"


class TestCommandRegistry(unittest.TestCase):
    """Tests for the CommandRegistry class."""
    
    def setUp(self):
        """Set up a registry and handler for testing."""
        self.registry = CommandRegistry()
        self.handler = MockHandler()
        logger.info("Setting up TestCommandRegistry")
    
    def test_register(self):
        """Test registering a command."""
        self.registry.register("test", self.handler.handle, "Test command")
        
        # Verify the command was registered
        self.assertIn("test", self.registry.commands)
        self.assertEqual(self.registry.commands["test"]["handler"], self.handler.handle)
        self.assertEqual(self.registry.commands["test"]["help_text"], "Test command")
    
    def test_get_handler(self):
        """Test retrieving a handler."""
        self.registry.register("test", self.handler.handle, "Test command")
        
        # Get the handler and verify it's correct
        handler = self.registry.get_handler("test")
        self.assertEqual(handler, self.handler.handle)
        
        # Test case insensitivity
        handler = self.registry.get_handler("TEST")
        self.assertEqual(handler, self.handler.handle)
        
        # Test non-existent command
        handler = self.registry.get_handler("nonexistent")
        self.assertIsNone(handler)
    
    def test_get_help(self):
        """Test retrieving help text."""
        self.registry.register("test", self.handler.handle, "Test command")
        
        # Get help for specific command
        help_text = self.registry.get_help("test")
        self.assertEqual(help_text, "Test command")
        
        # Test case insensitivity
        help_text = self.registry.get_help("TEST")
        self.assertEqual(help_text, "Test command")
        
        # Test non-existent command
        help_text = self.registry.get_help("nonexistent")
        self.assertIn("No help available", help_text)
        
        # Test get all help
        all_help = self.registry.get_help()
        self.assertIn("Available commands", all_help)
        self.assertIn("test: Test command", all_help)
    
    def test_register_alias(self):
        """Test registering an alias for a command."""
        self.registry.register("test", self.handler.handle, "Test command")
        self.registry.register_alias("t", "test")
        
        # Verify the alias was registered
        self.assertIn("t", self.registry.commands)
        self.assertEqual(self.registry.commands["t"]["handler"], self.handler.handle)
        self.assertIn("Alias for 'test'", self.registry.commands["t"]["help_text"])
        
        # Test getting handler by alias
        handler = self.registry.get_handler("t")
        self.assertEqual(handler, self.handler.handle)
        
        # Test trying to alias non-existent command
        with self.assertRaises(ValueError):
            self.registry.register_alias("x", "nonexistent")
    
    def test_register_aliases(self):
        """Test registering multiple aliases at once."""
        self.registry.register("test", self.handler.handle, "Test command")
        self.registry.register_aliases(["t", "tst", "testing"], "test")
        
        # Verify all aliases were registered
        for alias in ["t", "tst", "testing"]:
            self.assertIn(alias, self.registry.commands)
            self.assertEqual(self.registry.commands[alias]["handler"], self.handler.handle)


if __name__ == "__main__":
    unittest.main()