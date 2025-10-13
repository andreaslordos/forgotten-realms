"""
Base test classes providing common setup for different test types.

This module provides:
- BaseCommandTest: For testing command handlers
- BaseModelTest: For testing model classes
- BaseManagerTest: For testing manager classes
- BaseAsyncTest: For async tests
"""

import unittest
from tests.test_helpers import (
    create_mock_sio,
    create_mock_utils,
    create_mock_game_state,
    create_mock_player_manager,
    create_mock_player,
)


class BaseCommandTest(unittest.IsolatedAsyncioTestCase):
    """Base class for command tests with common setup."""

    def setUp(self):
        """Set up common command test fixtures."""
        # Mock async dependencies
        self.mock_sio = create_mock_sio()
        self.mock_utils = create_mock_utils()

        # Mock game dependencies
        self.mock_game_state = create_mock_game_state()
        self.mock_player_manager = create_mock_player_manager()
        self.online_sessions = {}

        # Mock common objects
        self.player = create_mock_player()
        self.other_player = create_mock_player(name="OtherPlayer")


class BaseModelTest(unittest.TestCase):
    """Base class for model tests with common setup."""

    def setUp(self):
        """Set up common model test fixtures."""
        self.test_data = {}
        self.mock_player_data = {
            "name": "TestPlayer",
            "level": "Novice",
            "health": 100,
            "max_health": 100,
            "strength": 10,
            "dexterity": 10,
            "constitution": 10,
            "intelligence": 10,
            "wisdom": 10,
            "charisma": 10,
            "inventory": [],
            "location": "test_room_1",
            "points": 0,
            "gold": 0,
        }


class BaseManagerTest(unittest.TestCase):
    """Base class for manager tests with common setup."""

    def setUp(self):
        """Set up common manager test fixtures."""
        self.mock_game_state = create_mock_game_state()
        self.test_data = {}


class BaseAsyncTest(unittest.IsolatedAsyncioTestCase):
    """Base class for async tests with common async fixtures."""

    def setUp(self):
        """Set up common async test fixtures."""
        self.mock_sio = create_mock_sio()
        self.mock_utils = create_mock_utils()


class BaseAsyncManagerTest(unittest.IsolatedAsyncioTestCase):
    """Base class for async manager tests."""

    def setUp(self):
        """Set up common async manager test fixtures."""
        self.mock_game_state = create_mock_game_state()
        self.mock_sio = create_mock_sio()
        self.mock_utils = create_mock_utils()
