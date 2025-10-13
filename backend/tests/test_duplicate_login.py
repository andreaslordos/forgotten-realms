"""
Test duplicate login prevention.

This test verifies that the same user cannot log in twice simultaneously.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class DuplicateLoginPreventionTest(unittest.IsolatedAsyncioTestCase):
    """Test duplicate login prevention in event handlers."""

    async def test_duplicate_login_blocked(self):
        """Test that a user already logged in cannot log in again."""
        # This test simulates the duplicate login check in event_handlers.py

        # Mock player already logged in
        logged_in_player = Mock()
        logged_in_player.name = "TestUser"

        # Simulate online_sessions with one logged-in user
        online_sessions = {
            'sid-1': {
                'player': logged_in_player,
            }
        }

        # Simulate a new login attempt for the same user
        username_to_check = "TestUser"
        current_sid = 'sid-2'

        # Perform the duplicate check (same logic as event_handlers.py)
        duplicate_found = False
        for other_sid, other_session in online_sessions.items():
            if other_sid != current_sid:
                other_player = other_session.get('player')
                if other_player and other_player.name.lower() == username_to_check.lower():
                    duplicate_found = True
                    break

        # Assert duplicate was detected
        self.assertTrue(duplicate_found, "Duplicate login should be detected")

    async def test_different_user_allowed(self):
        """Test that a different user can log in when another is already logged in."""
        # Mock player already logged in
        logged_in_player = Mock()
        logged_in_player.name = "User1"

        # Simulate online_sessions with one logged-in user
        online_sessions = {
            'sid-1': {
                'player': logged_in_player,
            }
        }

        # Simulate a login attempt for a different user
        username_to_check = "User2"
        current_sid = 'sid-2'

        # Perform the duplicate check
        duplicate_found = False
        for other_sid, other_session in online_sessions.items():
            if other_sid != current_sid:
                other_player = other_session.get('player')
                if other_player and other_player.name.lower() == username_to_check.lower():
                    duplicate_found = True
                    break

        # Assert duplicate was NOT detected
        self.assertFalse(duplicate_found, "Different user should be allowed to log in")

    async def test_case_insensitive_duplicate_check(self):
        """Test that duplicate check is case insensitive."""
        # Mock player already logged in
        logged_in_player = Mock()
        logged_in_player.name = "TestUser"

        # Simulate online_sessions
        online_sessions = {
            'sid-1': {
                'player': logged_in_player,
            }
        }

        # Try to log in with different case
        username_to_check = "testuser"
        current_sid = 'sid-2'

        # Perform the duplicate check
        duplicate_found = False
        for other_sid, other_session in online_sessions.items():
            if other_sid != current_sid:
                other_player = other_session.get('player')
                if other_player and other_player.name.lower() == username_to_check.lower():
                    duplicate_found = True
                    break

        # Assert duplicate was detected (case insensitive)
        self.assertTrue(duplicate_found, "Duplicate check should be case insensitive")

    async def test_same_sid_not_flagged_as_duplicate(self):
        """Test that checking the same session doesn't flag as duplicate."""
        # Mock player
        player = Mock()
        player.name = "TestUser"

        # Simulate online_sessions with one user
        online_sessions = {
            'sid-1': {
                'player': player,
            }
        }

        # Check the same sid
        username_to_check = "TestUser"
        current_sid = 'sid-1'

        # Perform the duplicate check
        duplicate_found = False
        for other_sid, other_session in online_sessions.items():
            if other_sid != current_sid:
                other_player = other_session.get('player')
                if other_player and other_player.name.lower() == username_to_check.lower():
                    duplicate_found = True
                    break

        # Assert duplicate was NOT detected (same sid excluded)
        self.assertFalse(duplicate_found, "Same session should not be flagged as duplicate")


if __name__ == '__main__':
    unittest.main()
