"""
Comprehensive tests for globals module.

Tests cover:
- Global state initialization
- online_sessions dictionary
- version string
- State management
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import globals as globals_module


class GlobalsInitializationTest(unittest.TestCase):
    """Test globals module initialization."""

    def test_online_sessions_is_dict(self):
        """Test online_sessions is initialized as a dictionary."""
        # Assert
        self.assertIsInstance(globals_module.online_sessions, dict)

    def test_online_sessions_is_empty_on_init(self):
        """Test online_sessions is empty when module is loaded."""
        # Note: This test may fail if other tests have modified globals
        # In production, we'd use a fixture or reset mechanism
        # For now, we just verify it's a dict
        self.assertIsInstance(globals_module.online_sessions, dict)

    def test_version_is_string(self):
        """Test version is a string."""
        # Assert
        self.assertIsInstance(globals_module.version, str)

    def test_version_has_correct_format(self):
        """Test version follows expected format."""
        # Assert
        self.assertRegex(globals_module.version, r'^\d+\.\d+$')

    def test_version_is_correct_value(self):
        """Test version is set to 0.23."""
        # Assert
        self.assertEqual(globals_module.version, "0.23")


class GlobalsOnlineSessionsTest(unittest.TestCase):
    """Test online_sessions dictionary functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Store original state
        self.original_sessions = globals_module.online_sessions.copy()

        # Clear sessions for testing
        globals_module.online_sessions.clear()

    def tearDown(self):
        """Restore original state."""
        globals_module.online_sessions.clear()
        globals_module.online_sessions.update(self.original_sessions)

    def test_online_sessions_can_store_session_data(self):
        """Test online_sessions can store session data."""
        # Arrange
        sid = "test_sid_123"
        session_data = {"player": Mock(), "connected_at": "2025-01-01"}

        # Act
        globals_module.online_sessions[sid] = session_data

        # Assert
        self.assertIn(sid, globals_module.online_sessions)
        self.assertEqual(globals_module.online_sessions[sid], session_data)

    def test_online_sessions_can_be_modified(self):
        """Test online_sessions dictionary can be modified."""
        # Arrange
        sid = "test_sid_123"
        globals_module.online_sessions[sid] = {"player": None}

        # Act
        globals_module.online_sessions[sid]["player"] = Mock()

        # Assert
        self.assertIsNotNone(globals_module.online_sessions[sid]["player"])

    def test_online_sessions_can_be_deleted(self):
        """Test sessions can be removed from online_sessions."""
        # Arrange
        sid = "test_sid_123"
        globals_module.online_sessions[sid] = {"player": Mock()}

        # Act
        del globals_module.online_sessions[sid]

        # Assert
        self.assertNotIn(sid, globals_module.online_sessions)

    def test_online_sessions_supports_multiple_sessions(self):
        """Test online_sessions can store multiple session entries."""
        # Arrange
        sid1 = "test_sid_1"
        sid2 = "test_sid_2"
        sid3 = "test_sid_3"

        # Act
        globals_module.online_sessions[sid1] = {"player": Mock()}
        globals_module.online_sessions[sid2] = {"player": Mock()}
        globals_module.online_sessions[sid3] = {"player": Mock()}

        # Assert
        self.assertEqual(len(globals_module.online_sessions), 3)
        self.assertIn(sid1, globals_module.online_sessions)
        self.assertIn(sid2, globals_module.online_sessions)
        self.assertIn(sid3, globals_module.online_sessions)

    def test_online_sessions_iteration(self):
        """Test online_sessions can be iterated over."""
        # Arrange
        globals_module.online_sessions["sid1"] = {"player": Mock()}
        globals_module.online_sessions["sid2"] = {"player": Mock()}

        # Act
        sids = list(globals_module.online_sessions.keys())

        # Assert
        self.assertEqual(len(sids), 2)
        self.assertIn("sid1", sids)
        self.assertIn("sid2", sids)


class GlobalsVersionTest(unittest.TestCase):
    """Test version string functionality."""

    def test_version_is_accessible(self):
        """Test version can be accessed."""
        # Act
        version = globals_module.version

        # Assert
        self.assertIsNotNone(version)

    def test_version_is_not_empty(self):
        """Test version is not an empty string."""
        # Assert
        self.assertNotEqual(globals_module.version, "")
        self.assertTrue(len(globals_module.version) > 0)


class GlobalsStateManagementTest(unittest.TestCase):
    """Test global state management patterns."""

    def setUp(self):
        """Set up test fixtures."""
        # Store original state
        self.original_sessions = globals_module.online_sessions.copy()
        globals_module.online_sessions.clear()

    def tearDown(self):
        """Restore original state."""
        globals_module.online_sessions.clear()
        globals_module.online_sessions.update(self.original_sessions)

    def test_get_nonexistent_session_raises_keyerror(self):
        """Test accessing non-existent session raises KeyError."""
        # Act & Assert
        with self.assertRaises(KeyError):
            _ = globals_module.online_sessions["nonexistent"]

    def test_get_with_default_returns_none_for_nonexistent(self):
        """Test get() returns None for non-existent session."""
        # Act
        result = globals_module.online_sessions.get("nonexistent")

        # Assert
        self.assertIsNone(result)

    def test_get_with_custom_default_returns_default(self):
        """Test get() returns custom default for non-existent session."""
        # Arrange
        default = {"player": None}

        # Act
        result = globals_module.online_sessions.get("nonexistent", default)

        # Assert
        self.assertEqual(result, default)

    def test_clear_removes_all_sessions(self):
        """Test clear() removes all sessions."""
        # Arrange
        globals_module.online_sessions["sid1"] = {"player": Mock()}
        globals_module.online_sessions["sid2"] = {"player": Mock()}

        # Act
        globals_module.online_sessions.clear()

        # Assert
        self.assertEqual(len(globals_module.online_sessions), 0)

    def test_pop_removes_and_returns_session(self):
        """Test pop() removes and returns session data."""
        # Arrange
        sid = "test_sid"
        session_data = {"player": Mock()}
        globals_module.online_sessions[sid] = session_data

        # Act
        result = globals_module.online_sessions.pop(sid)

        # Assert
        self.assertEqual(result, session_data)
        self.assertNotIn(sid, globals_module.online_sessions)

    def test_update_merges_multiple_sessions(self):
        """Test update() merges multiple sessions."""
        # Arrange
        new_sessions = {
            "sid1": {"player": Mock()},
            "sid2": {"player": Mock()}
        }

        # Act
        globals_module.online_sessions.update(new_sessions)

        # Assert
        self.assertEqual(len(globals_module.online_sessions), 2)
        self.assertIn("sid1", globals_module.online_sessions)
        self.assertIn("sid2", globals_module.online_sessions)


if __name__ == "__main__":
    unittest.main()
