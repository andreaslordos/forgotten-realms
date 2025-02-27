# backend/tests/test_communication.py

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from commands.registry import command_registry
from commands.executor import execute_command
from commands.parser import CommandContext, parse_command
from models.player import Player
from models.room import Room
from models.item import Item

class AsyncTestCase(unittest.TestCase):
    """Base class for async test cases."""
    
    def run_async(self, coro):
        """Run an async coroutine in a test case."""
        return asyncio.get_event_loop().run_until_complete(coro)


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
        
        # Set up visited set
        self.visited = set()
    
    async def test_say_command(self):
        """Test the 'say' command."""
        # Execute the command directly
        result = await execute_command(
            "say Hello everyone", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Check result
        self.assertIn("You say:", result)
        self.assertIn("Hello everyone", result)
        
        # Check that the message was sent to other players in the room
        self.utils.send_message.assert_called()
        
        # Find the call with the message to the other player
        found_message = False
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "says" in args[2] and "Hello everyone" in args[2]:
                found_message = True
                break
        
        self.assertTrue(found_message, "Message wasn't sent to the other player")
    
    async def test_quote_say_command(self):
        """Test the quote-prefixed say command."""
        # Execute the command directly
        result = await execute_command(
            '"Hello from quotes', 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Check result
        self.assertIn("You say:", result)
        self.assertIn("Hello from quotes", result)
        
        # Find the call with the message to the other player
        found_message = False
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "says" in args[2] and "Hello from quotes" in args[2]:
                found_message = True
                break
        
        self.assertTrue(found_message, "Quote-prefixed say message wasn't sent")
    
    async def test_shout_command(self):
        """Test the 'shout' command."""
        # Execute the command directly
        result = await execute_command(
            "shout Attention everyone!", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Check result
        self.assertIn(result)
        self.assertIn("Attention everyone!", result)
        
        # Find the call with the message to the other player
        found_message = False
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "shouts" in args[2] and "Attention everyone!" in args[2]:
                found_message = True
                break
        
        self.assertTrue(found_message, "Shout message wasn't broadcast")
    
    async def test_tell_command(self):
        """Test the 'tell' command."""
        # Execute the command directly
        result = await execute_command(
            "tell Player2 This is a private message", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Check result
        self.assertIn("You tell Player2:", result)
        self.assertIn("This is a private message", result)
        
        # Find the call with the message to the other player
        found_message = False
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "tells you" in args[2] and "This is a private message" in args[2]:
                found_message = True
                break
        
        self.assertTrue(found_message, "Private message wasn't sent")
    
    async def test_direct_player_message(self):
        """Test sending a message directly to a player."""
        # Parse the command first to see if it converts to a tell command
        context = CommandContext()
        parsed = parse_command("Player2 Hello directly", context, [self.player1, self.player2])
        
        # Check that it was parsed as a tell command
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["verb"], "tell")
        self.assertEqual(parsed[0]["subject"], "Player2")
        self.assertEqual(parsed[0]["instrument"], "Hello directly")
        
        # Now execute the command
        result = await execute_command(
            "Player2 Hello directly", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Check result
        self.assertIn("You tell Player2:", result)
        self.assertIn("Hello directly", result)
        
        # Find the call with the message to the other player
        found_message = False
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "tells you" in args[2] and "Hello directly" in args[2]:
                found_message = True
                break
        
        self.assertTrue(found_message, "Direct player message wasn't sent")
    
    async def test_act_command(self):
        """Test the 'act' command."""
        # Execute the command directly
        result = await execute_command(
            "act waves enthusiastically", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Check result
        self.assertIn("**Player1 waves enthusiastically**", result)
        
        # Find the call with the message to the other player
        found_message = False
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "**Player1 waves enthusiastically**" in args[2]:
                found_message = True
                break
        
        self.assertTrue(found_message, "Act message wasn't sent")
    
    async def test_converse_mode(self):
        """Test toggling converse mode."""
        # Execute command to turn on converse mode
        result = await execute_command(
            "converse", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Check result
        self.assertIn("Converse mode ON", result)
        self.assertTrue(self.online_sessions["sid1"].get("converse_mode", False))
        
        # Execute a regular message in converse mode
        # This would typically be handled in tick_service.py
        # We'll simulate that logic here
        
        # Toggle converse mode off
        result = await execute_command(
            "converse", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Check result
        self.assertIn("Converse mode OFF", result)
        self.assertFalse(self.online_sessions["sid1"].get("converse_mode", True))


if __name__ == "__main__":
    unittest.main()