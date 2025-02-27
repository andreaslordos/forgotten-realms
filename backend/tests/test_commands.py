# backend/tests/test_commands.py

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from commands.registry import command_registry, CommandRegistry
from models.player import Player
from models.room import Room
from models.item import Item

class AsyncTestCase(unittest.TestCase):
    """Base class for async test cases."""
    
    def run_async(self, coro):
        """Run an async coroutine in a test case."""
        return asyncio.get_event_loop().run_until_complete(coro)

class TestStandardCommands(AsyncTestCase):
    """Test basic game commands."""
    
    def setUp(self):
        """Set up test environment."""
        # Create player
        self.player = Player("TestPlayer")
        
        # Create a test room
        self.room = Room("test_room", "Test Room", "This is a test room.")
        
        # Create test items
        self.sword = Item("sword", "A shiny sword", weight=5, value=10)
        self.shield = Item("shield", "A sturdy shield", weight=8, value=15)
        
        # Add items to room
        self.room.add_item(self.sword)
        self.room.add_item(self.shield)
        
        # Set up game state
        self.game_state = Mock()
        self.game_state.get_room.return_value = self.room
        self.game_state.rooms = {"test_room": self.room}
        
        # Set up player manager
        self.player_manager = Mock()
        self.player_manager.spawn_room = "test_room"
        
        # Set player location
        self.player.set_current_room("test_room")
        
        # Set up utils and online sessions
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()
        
        self.online_sessions = {
            "test_sid": {
                "player": self.player,
                "visited": set(),
                "command_queue": []
            }
        }
        
        # Mock socket.io
        self.sio = AsyncMock()
        
        # Set up visited set
        self.visited = set()
    
    async def test_look_command(self):
        """Test the 'look' command."""
        # Get the look handler
        look_handler = command_registry.get_handler("look")
        self.assertIsNotNone(look_handler, "Look handler not found")
        
        # Set up command dict
        cmd = {"verb": "look", "subject": None}
        
        # Execute the command
        result = await look_handler(cmd, self.player, self.game_state, self.player_manager, 
                               self.visited, self.online_sessions, self.sio, self.utils)
        
        # Check result
        self.assertIn("Test Room", result)
        self.assertIn("test room", result)
        self.assertIn("sword", result.lower())
        self.assertIn("shield", result.lower())
        
        # Test looking at an item
        cmd = {"verb": "look", "subject": "sword"}
        result = await look_handler(cmd, self.player, self.game_state, self.player_manager,
                               self.visited, self.online_sessions, self.sio, self.utils)
        self.assertIn("sword", result.lower())
        self.assertIn("shiny", result.lower())
    
    async def test_inventory_command(self):
        """Test the 'inventory' command."""
        # Get the inventory handler
        inv_handler = command_registry.get_handler("inventory")
        self.assertIsNotNone(inv_handler, "Inventory handler not found")
        
        # Set up command dict
        cmd = {"verb": "inventory", "subject": None}
        
        # Empty inventory
        result = await inv_handler(cmd, self.player, self.game_state, self.player_manager,
                              self.visited, self.online_sessions, self.sio, self.utils)
        self.assertIn("aren't carrying anything", result.lower())
        
        # Add an item to inventory
        self.player.add_item(self.sword)
        
        # Check inventory again
        result = await inv_handler(cmd, self.player, self.game_state, self.player_manager,
                              self.visited, self.online_sessions, self.sio, self.utils)
        self.assertIn("sword", result.lower())
    
    async def test_get_drop_commands(self):
        """Test the 'get' and 'drop' commands."""
        # Get the handlers
        get_handler = command_registry.get_handler("get")
        drop_handler = command_registry.get_handler("drop")
        self.assertIsNotNone(get_handler, "Get handler not found")
        self.assertIsNotNone(drop_handler, "Drop handler not found")
        
        # Test getting an item
        cmd = {"verb": "get", "subject": "sword"}
        result = await get_handler(cmd, self.player, self.game_state, self.player_manager,
                              self.visited, self.online_sessions, self.sio, self.utils)
        self.assertIn("taken", result.lower())
        self.assertEqual(len(self.player.inventory), 1)
        self.assertEqual(self.player.inventory[0].name, "sword")
        
        # Test dropping the item
        cmd = {"verb": "drop", "subject": "sword"}
        result = await drop_handler(cmd, self.player, self.game_state, self.player_manager,
                               self.visited, self.online_sessions, self.sio, self.utils)
        self.assertIn("dropped", result.lower())
        self.assertEqual(len(self.player.inventory), 0)
        
        # Test getting all items
        cmd = {"verb": "get", "subject": "all"}
        result = await get_handler(cmd, self.player, self.game_state, self.player_manager,
                              self.visited, self.online_sessions, self.sio, self.utils)
        self.assertIn("picked up", result.lower())
        self.assertEqual(len(self.player.inventory), 2)
    
    async def test_score_command(self):
        """Test the 'score' command."""
        # Get the score handler
        score_handler = command_registry.get_handler("score")
        self.assertIsNotNone(score_handler, "Score handler not found")
        
        # Set up command dict
        cmd = {"verb": "score", "subject": None}
        
        # Check score
        result = await score_handler(cmd, self.player, self.game_state, self.player_manager,
                                self.visited, self.online_sessions, self.sio, self.utils)
        self.assertIn("score", result.lower())
        self.assertIn("points", result.lower())
        self.assertIn("stamina", result.lower())
        self.assertIn("strength", result.lower())
        self.assertIn("dexterity", result.lower())
        self.assertIn("carrying capacity", result.lower())


class TestCommunicationCommands(AsyncTestCase):
    """Test communication commands."""
    
    def setUp(self):
        """Set up test environment."""
        # Create players
        self.player1 = Player("Player1")
        self.player2 = Player("Player2")
        
        # Create a test room
        self.room = Room("test_room", "Test Room", "This is a test room.")
        
        # Set up game state
        self.game_state = Mock()
        self.game_state.get_room.return_value = self.room
        self.game_state.rooms = {"test_room": self.room}
        
        # Set up player manager
        self.player_manager = Mock()
        
        # Set player locations
        self.player1.set_current_room("test_room")
        self.player2.set_current_room("test_room")
        
        # Set up utils and online sessions
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        
        self.online_sessions = {
            "sid1": {
                "player": self.player1,
                "visited": set(),
                "command_queue": []
            },
            "sid2": {
                "player": self.player2,
                "visited": set(),
                "command_queue": []
            }
        }
        
        # Mock socket.io
        self.sio = AsyncMock()
        self.sio.manager.sid = "sid1"  # Set current session ID for player1
        
        # Set up visited set
        self.visited = set()
    
    async def test_say_command(self):
        """Test the 'say' command."""
        # Get the say handler
        say_handler = command_registry.get_handler("say")
        self.assertIsNotNone(say_handler, "Say handler not found")
        
        # Set up command dict
        cmd = {"verb": "say", "subject": "Hello, everyone!"}
        
        # Execute the command
        result = await say_handler(cmd, self.player1, self.game_state, self.player_manager,
                              self.visited, self.online_sessions, self.sio, self.utils)
        
        # Check result
        self.assertIn("you say", result.lower())
        self.assertIn("hello", result.lower())
        
        # Check that the message was sent to other players in the room
        self.utils.send_message.assert_called()
        # Get the last call arguments
        args, _ = self.utils.send_message.call_args
        self.assertEqual(args[0], self.sio)
        self.assertEqual(args[1], "sid2")
        self.assertIn("Player1", args[2])
        self.assertIn("Hello, everyone!", args[2])
    
    async def test_tell_command(self):
        """Test the 'tell' command."""
        # Get the tell handler
        tell_handler = command_registry.get_handler("tell")
        self.assertIsNotNone(tell_handler, "Tell handler not found")
        
        # Set up command dict
        cmd = {"verb": "tell", "subject": "Player2", "instrument": "This is a private message"}
        
        # Execute the command
        result = await tell_handler(cmd, self.player1, self.game_state, self.player_manager,
                               self.visited, self.online_sessions, self.sio, self.utils)
        
        # Check result
        self.assertIn("you tell", result.lower())
        self.assertIn("player2", result.lower())
        self.assertIn("this is a private message", result.lower())
        
        # Check that the message was sent to the recipient
        self.utils.send_message.assert_called()
        args, _ = self.utils.send_message.call_args
        self.assertEqual(args[0], self.sio)
        self.assertEqual(args[1], "sid2")
        self.assertIn("Player1", args[2])
        self.assertIn("This is a private message", args[2])


class TestPuzzleCommands(AsyncTestCase):
    """Test puzzle interaction commands."""
    
    def setUp(self):
        """Set up test environment."""
        # Create player
        self.player = Player("TestPlayer")
        
        # Create a test room with a puzzle feature
        self.room = Room("test_room", "Test Room", "This is a test room with a door.")
        
        # Create test items
        self.key = Item("key", "A rusty key", weight=1, value=0)
        self.axe = Item("axe", "A sharp axe", weight=10, value=0)
        
        # Add items to player's inventory
        self.player.add_item(self.key)
        self.player.add_item(self.axe)
        
        # Set up game state
        self.game_state = Mock()
        self.game_state.get_room.return_value = self.room
        self.game_state.rooms = {"test_room": self.room}
        
        # Set up player manager
        self.player_manager = Mock()
        
        # Set player location
        self.player.set_current_room("test_room")
        
        # Set up utils
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        
        # Set up online sessions
        self.online_sessions = {
            "test_sid": {
                "player": self.player,
                "visited": set(),
                "command_queue": []
            }
        }
        
        # Mock socket.io
        self.sio = AsyncMock()
        
        # Set up visited set
        self.visited = set()
    
    async def test_use_command(self):
        """Test the 'use' command."""
        # Get the use handler
        use_handler = command_registry.get_handler("use")
        self.assertIsNotNone(use_handler, "Use handler not found")
        
        # Set up command dict
        cmd = {"verb": "use", "subject": "key", "instrument": "door"}
        
        # Execute the command
        result = await use_handler(cmd, self.player, self.game_state, self.player_manager,
                              self.visited, self.online_sessions, self.sio, self.utils)
        
        # Check result (should be a generic response as we don't have real puzzle mechanics implemented)
        self.assertIn("key", result.lower())
        self.assertIn("door", result.lower())
    
    async def test_knock_command(self):
        """Test the 'knock' command."""
        # Get the knock handler
        knock_handler = command_registry.get_handler("knock")
        self.assertIsNotNone(knock_handler, "Knock handler not found")
        
        # Set up command dict
        cmd = {"verb": "knock", "subject": "door"}
        
        # Execute the command
        result = await knock_handler(cmd, self.player, self.game_state, self.player_manager,
                                self.visited, self.online_sessions, self.sio, self.utils)
        
        # Check result
        self.assertIn("knock", result.lower())
        self.assertIn("door", result.lower())


class TestCombatCommands(AsyncTestCase):
    """Test combat commands."""
    
    def setUp(self):
        """Set up test environment."""
        # Create players
        self.player1 = Player("Player1")
        self.player2 = Player("Player2")
        
        # Create a test room
        self.room = Room("test_room", "Test Room", "This is a test room.")
        
        # Create test items
        self.sword = Item("sword", "A shiny sword", weight=5, value=10)
        
        # Add items to player1's inventory
        self.player1.add_item(self.sword)
        
        # Set up game state
        self.game_state = Mock()
        self.game_state.get_room.return_value = self.room
        self.game_state.rooms = {"test_room": self.room}
        
        # Set up player manager
        self.player_manager = Mock()
        self.player_manager.spawn_room = "test_room"
        
        # Set player locations
        self.player1.set_current_room("test_room")
        self.player2.set_current_room("test_room")
        
        # Set up utils
        self.utils = Mock()
        self.utils.send_message = AsyncMock()
        self.utils.send_stats_update = AsyncMock()
        
        # Set up online sessions
        self.online_sessions = {
            "sid1": {
                "player": self.player1,
                "visited": set(),
                "command_queue": []
            },
            "sid2": {
                "player": self.player2,
                "visited": set(),
                "command_queue": []
            }
        }
        
        # Mock socket.io
        self.sio = AsyncMock()
        self.sio.manager.sid = "sid1"  # Set current session ID for player1
        
        # Set up visited set
        self.visited = set()
    
    async def test_attack_command(self):
        """Test the 'attack' command."""
        # Get the attack handler
        attack_handler = command_registry.get_handler("attack")
        self.assertIsNotNone(attack_handler, "Attack handler not found")
        
        # Set up command dict
        cmd = {"verb": "attack", "subject": "Player2", "instrument": "sword"}
        
        # Execute the command
        result = await attack_handler(cmd, self.player1, self.game_state, self.player_manager,
                                 self.visited, self.online_sessions, self.sio, self.utils)
        
        # Check result
        self.assertIn("attack", result.lower())
        self.assertIn("player2", result.lower())
        self.assertIn("sword", result.lower())
        
        # Check that the attack notification was sent to the target
        self.utils.send_message.assert_called()
        args, _ = self.utils.send_message.call_args_list[0]
        self.assertEqual(args[0], self.sio)
        self.assertEqual(args[1], "sid2")
        self.assertIn("Player1", args[2])
        self.assertIn("attacks you", args[2].lower())


if __name__ == "__main__":
    unittest.main()