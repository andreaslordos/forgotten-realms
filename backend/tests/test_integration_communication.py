# backend/tests/test_integration_communication.py

import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from commands.executor import execute_command
from commands.parser import parse_command
from models.player import Player
from models.room import Room
from managers.game_state import GameState
from managers.player import PlayerManager

class AsyncTestCase(unittest.TestCase):
    """Base class for async test cases."""
    
    def run_async(self, coro):
        """Run an async coroutine in a test case."""
        return asyncio.get_event_loop().run_until_complete(coro)


class TestCommunicationIntegration(AsyncTestCase):
    """Integration tests for the communication system."""
    
    def setUp(self):
        """Set up test environment."""
        # Create players
        self.player1 = Player("Player1")
        self.player2 = Player("Player2")
        self.player3 = Player("Player3")
        
        # Set up rooms
        self.room1 = Room("room1", "Room 1", "This is room 1.")
        self.room2 = Room("room2", "Room 2", "This is room 2.")
        
        # Connect rooms
        self.room1.exits = {"east": "room2"}
        self.room2.exits = {"west": "room1"}
        
        # Set up game state
        self.game_state = Mock(spec=GameState)
        self.game_state.rooms = {"room1": self.room1, "room2": self.room2}
        self.game_state.get_room = lambda room_id: self.game_state.rooms.get(room_id)
        self.game_state.save_rooms = Mock()
        
        # Set up player manager
        self.player_manager = Mock(spec=PlayerManager)
        self.player_manager.spawn_room = "room1"
        self.player_manager.save_players = Mock()
        
        # Set player locations
        self.player1.set_current_room("room1")
        self.player2.set_current_room("room1")
        self.player3.set_current_room("room2")
        
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
            },
            "sid3": {
                "player": self.player3,
                "visited": set(),
                "command_queue": []
            }
        }
        
        # Mock socket.io
        self.sio = AsyncMock()
        
        # Set up visited sets
        self.visited1 = set()
        self.visited2 = set()
        self.visited3 = set()
    
    async def test_local_communication(self):
        """Test all forms of in-room communication."""
        # Test say command
        result = await execute_command(
            "say Hello to those in my room", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited1,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Verify say command results
        self.assertIn("You say:", result)
        self.assertIn("Hello to those in my room", result)
        
        # Check that player2 received the message but player3 did not
        # Since player2 is in same room, player3 is in a different room
        found_p2_message = False
        found_p3_message = False
        
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "says" in args[2]:
                found_p2_message = True
            if args[1] == "sid3" and "Player1" in args[2] and "says" in args[2]:
                found_p3_message = True
        
        self.assertTrue(found_p2_message, "Player2 didn't receive the say message")
        self.assertFalse(found_p3_message, "Player3 incorrectly received the say message")
        
        # Reset the mock to clear call history
        self.utils.send_message.reset_mock()
        
        # Test quote-based say command
        result = await execute_command(
            '"Testing the quote command', 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited1,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Verify quote command results
        self.assertIn("You say:", result)
        self.assertIn("Testing the quote command", result)
        
        # Check that player2 received the message but player3 did not
        found_p2_message = False
        found_p3_message = False
        
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "says" in args[2]:
                found_p2_message = True
            if args[1] == "sid3" and "Player1" in args[2] and "says" in args[2]:
                found_p3_message = True
        
        self.assertTrue(found_p2_message, "Player2 didn't receive the quote message")
        self.assertFalse(found_p3_message, "Player3 incorrectly received the quote message")
        
        # Reset the mock
        self.utils.send_message.reset_mock()
        
        # Test act command
        result = await execute_command(
            "act jumps up and down", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited1,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Verify act command results
        self.assertIn("**Player1 jumps up and down**", result)
        
        # Check that player2 received the message but player3 did not
        found_p2_message = False
        found_p3_message = False
        
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "**Player1 jumps up and down**" in args[2]:
                found_p2_message = True
            if args[1] == "sid3" and "**Player1 jumps up and down**" in args[2]:
                found_p3_message = True
        
        self.assertTrue(found_p2_message, "Player2 didn't receive the act message")
        self.assertFalse(found_p3_message, "Player3 incorrectly received the act message")
    
    async def test_global_communication(self):
        """Test global communication (shout)."""
        # Reset the mock
        self.utils.send_message.reset_mock()
        
        # Test shout command
        result = await execute_command(
            "shout This is a global announcement!", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited1,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Verify shout command results
        self.assertIn(result)
        self.assertIn("This is a global announcement!", result)
        
        # Check that both player2 and player3 received the shout
        found_p2_message = False
        found_p3_message = False
        
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "shouts" in args[2]:
                found_p2_message = True
            if args[1] == "sid3" and "Player1" in args[2] and "shouts" in args[2]:
                found_p3_message = True
        
        self.assertTrue(found_p2_message, "Player2 didn't receive the shout message")
        self.assertTrue(found_p3_message, "Player3 didn't receive the shout message")
    
    async def test_private_communication(self):
        """Test private communication between players."""
        # Reset the mock
        self.utils.send_message.reset_mock()
        
        # Test tell command to player in same room
        result = await execute_command(
            "tell Player2 This is a private message", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited1,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Verify tell command results
        self.assertIn("You tell Player2:", result)
        self.assertIn("This is a private message", result)
        
        # Check that player2 received the message but player3 did not
        found_p2_message = False
        found_p3_message = False
        
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "tells you" in args[2]:
                found_p2_message = True
            if args[1] == "sid3" and "Player1" in args[2] and "tells you" in args[2]:
                found_p3_message = True
        
        self.assertTrue(found_p2_message, "Player2 didn't receive the tell message")
        self.assertFalse(found_p3_message, "Player3 incorrectly received the tell message")
        
        # Reset the mock
        self.utils.send_message.reset_mock()
        
        # Test tell command to player in different room
        result = await execute_command(
            "tell Player3 Message across rooms", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited1,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Verify tell command results
        self.assertIn("You tell Player3:", result)
        self.assertIn("Message across rooms", result)
        
        # Check that player3 received the message but player2 did not
        found_p2_message = False
        found_p3_message = False
        
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "tells you" in args[2]:
                found_p2_message = True
            if args[1] == "sid3" and "Player1" in args[2] and "tells you" in args[2]:
                found_p3_message = True
        
        self.assertFalse(found_p2_message, "Player2 incorrectly received the tell message")
        self.assertTrue(found_p3_message, "Player3 didn't receive the tell message")
    
    async def test_direct_player_message(self):
        """Test direct player messaging (Player2 message)."""
        # Reset the mock
        self.utils.send_message.reset_mock()
        
        # Test direct player message
        result = await execute_command(
            "Player2 This is a direct player message", 
            self.player1, 
            self.game_state, 
            self.player_manager,
            self.visited1,
            self.online_sessions,
            self.sio,
            self.utils
        )
        
        # Verify direct message results
        self.assertIn("You tell Player2:", result)
        self.assertIn("This is a direct player message", result)
        
        # Check that player2 received the message but player3 did not
        found_p2_message = False
        found_p3_message = False
        
        for call in self.utils.send_message.call_args_list:
            args = call[0]
            if args[1] == "sid2" and "Player1" in args[2] and "tells you" in args[2]:
                found_p2_message = True
            if args[1] == "sid3" and "Player1" in args[2] and "tells you" in args[2]:
                found_p3_message = True
        
        self.assertTrue(found_p2_message, "Player2 didn't receive the direct message")
        self.assertFalse(found_p3_message, "Player3 incorrectly received the direct message")


if __name__ == "__main__":
    unittest.main()