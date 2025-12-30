"""
Comprehensive tests for affliction service.

Tests cover:
- Applying afflictions
- Checking affliction status
- Getting active afflictions
- Removing afflictions
- Curing all afflictions
- Time remaining calculations
- Affliction expiry processing
- Player finding helpers
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.affliction_service import (
    set_context,
    apply_affliction,
    has_affliction,
    get_active_afflictions,
    remove_affliction,
    cure_all_afflictions,
    get_affliction_time_remaining,
    process_affliction_expiry,
    find_player_sid,
    find_player_by_name,
)


class SetContextTest(unittest.TestCase):
    """Test set_context function."""

    def test_set_context_sets_globals(self):
        """Test set_context sets global variables."""
        sessions = {"sid1": {"player": Mock()}}
        send_func = AsyncMock()

        set_context(sessions, send_func)

        # The function should complete without error
        # We can't easily test globals, but we verify no exception


class ApplyAfflictionTest(unittest.TestCase):
    """Test apply_affliction function."""

    def test_apply_affliction_creates_afflictions_dict(self):
        """Test apply_affliction creates afflictions dict if missing."""
        session: dict = {}

        result = apply_affliction(session, "blind", 60, "Caster")

        self.assertTrue(result)
        self.assertIn("afflictions", session)
        self.assertIn("blind", session["afflictions"])

    def test_apply_affliction_sets_correct_data(self):
        """Test apply_affliction sets correct affliction data."""
        session: dict = {}
        before_time = time.time()

        apply_affliction(session, "deaf", 30, "TestCaster")

        after_time = time.time()
        affliction = session["afflictions"]["deaf"]

        self.assertGreaterEqual(affliction["applied_at"], before_time)
        self.assertLessEqual(affliction["applied_at"], after_time)
        self.assertAlmostEqual(
            affliction["expires_at"], affliction["applied_at"] + 30, places=1
        )
        self.assertEqual(affliction["caster"], "TestCaster")

    def test_apply_affliction_overwrites_existing(self):
        """Test apply_affliction overwrites existing affliction."""
        session = {
            "afflictions": {
                "blind": {"applied_at": 0, "expires_at": 100, "caster": "OldCaster"}
            }
        }

        apply_affliction(session, "blind", 60, "NewCaster")

        self.assertEqual(session["afflictions"]["blind"]["caster"], "NewCaster")

    def test_apply_affliction_returns_true(self):
        """Test apply_affliction always returns True."""
        session: dict = {}

        result = apply_affliction(session, "dumb", 10, "Caster")

        self.assertTrue(result)


class HasAfflictionTest(unittest.TestCase):
    """Test has_affliction function."""

    def test_has_affliction_returns_false_when_no_afflictions(self):
        """Test has_affliction returns False when no afflictions dict."""
        session: dict = {}

        result = has_affliction(session, "blind")

        self.assertFalse(result)

    def test_has_affliction_returns_false_when_not_present(self):
        """Test has_affliction returns False when affliction not present."""
        session = {"afflictions": {"deaf": {"expires_at": time.time() + 60}}}

        result = has_affliction(session, "blind")

        self.assertFalse(result)

    def test_has_affliction_returns_true_when_active(self):
        """Test has_affliction returns True when affliction is active."""
        session = {"afflictions": {"blind": {"expires_at": time.time() + 60}}}

        result = has_affliction(session, "blind")

        self.assertTrue(result)

    def test_has_affliction_returns_false_when_expired(self):
        """Test has_affliction returns False when affliction has expired."""
        session = {"afflictions": {"blind": {"expires_at": time.time() - 10}}}

        result = has_affliction(session, "blind")

        self.assertFalse(result)


class GetActiveAfflictionsTest(unittest.TestCase):
    """Test get_active_afflictions function."""

    def test_get_active_afflictions_returns_empty_when_none(self):
        """Test returns empty set when no afflictions."""
        session: dict = {}

        result = get_active_afflictions(session)

        self.assertEqual(result, set())

    def test_get_active_afflictions_returns_active_only(self):
        """Test returns only non-expired afflictions."""
        current = time.time()
        session = {
            "afflictions": {
                "blind": {"expires_at": current + 60},  # Active
                "deaf": {"expires_at": current - 10},  # Expired
                "dumb": {"expires_at": current + 30},  # Active
            }
        }

        result = get_active_afflictions(session)

        self.assertEqual(result, {"blind", "dumb"})

    def test_get_active_afflictions_returns_all_when_all_active(self):
        """Test returns all afflictions when none expired."""
        current = time.time()
        session = {
            "afflictions": {
                "blind": {"expires_at": current + 60},
                "deaf": {"expires_at": current + 60},
                "cripple": {"expires_at": current + 60},
            }
        }

        result = get_active_afflictions(session)

        self.assertEqual(result, {"blind", "deaf", "cripple"})


class RemoveAfflictionTest(unittest.TestCase):
    """Test remove_affliction function."""

    def test_remove_affliction_returns_false_when_no_afflictions(self):
        """Test returns False when no afflictions dict."""
        session: dict = {}

        result = remove_affliction(session, "blind")

        self.assertFalse(result)

    def test_remove_affliction_returns_false_when_not_present(self):
        """Test returns False when affliction not present."""
        session = {"afflictions": {"deaf": {"expires_at": 100}}}

        result = remove_affliction(session, "blind")

        self.assertFalse(result)

    def test_remove_affliction_removes_and_returns_true(self):
        """Test removes affliction and returns True."""
        session = {"afflictions": {"blind": {"expires_at": 100}}}

        result = remove_affliction(session, "blind")

        self.assertTrue(result)
        self.assertNotIn("blind", session["afflictions"])

    def test_remove_affliction_keeps_other_afflictions(self):
        """Test only removes specified affliction."""
        session = {
            "afflictions": {
                "blind": {"expires_at": 100},
                "deaf": {"expires_at": 100},
            }
        }

        remove_affliction(session, "blind")

        self.assertIn("deaf", session["afflictions"])


class CureAllAfflictionsTest(unittest.TestCase):
    """Test cure_all_afflictions function."""

    def test_cure_all_returns_zero_when_none(self):
        """Test returns 0 when no afflictions."""
        session: dict = {}

        result = cure_all_afflictions(session)

        self.assertEqual(result, 0)

    def test_cure_all_returns_count(self):
        """Test returns count of removed afflictions."""
        session = {
            "afflictions": {
                "blind": {"expires_at": 100},
                "deaf": {"expires_at": 100},
                "dumb": {"expires_at": 100},
            }
        }

        result = cure_all_afflictions(session)

        self.assertEqual(result, 3)

    def test_cure_all_clears_afflictions(self):
        """Test clears all afflictions."""
        session = {
            "afflictions": {
                "blind": {"expires_at": 100},
                "deaf": {"expires_at": 100},
            }
        }

        cure_all_afflictions(session)

        self.assertEqual(session["afflictions"], {})

    def test_cure_all_clears_magic_sleep_flag(self):
        """Test clears magic_sleep session flag if present."""
        session = {"afflictions": {}, "magic_sleep": True}

        cure_all_afflictions(session)

        self.assertFalse(session["magic_sleep"])


class GetAfflictionTimeRemainingTest(unittest.TestCase):
    """Test get_affliction_time_remaining function."""

    def test_time_remaining_returns_zero_when_no_afflictions(self):
        """Test returns 0 when no afflictions dict."""
        session: dict = {}

        result = get_affliction_time_remaining(session, "blind")

        self.assertEqual(result, 0.0)

    def test_time_remaining_returns_zero_when_not_present(self):
        """Test returns 0 when affliction not present."""
        session = {"afflictions": {}}

        result = get_affliction_time_remaining(session, "blind")

        self.assertEqual(result, 0.0)

    def test_time_remaining_returns_positive_when_active(self):
        """Test returns positive value when affliction active."""
        session = {"afflictions": {"blind": {"expires_at": time.time() + 30}}}

        result = get_affliction_time_remaining(session, "blind")

        self.assertGreater(result, 25)
        self.assertLessEqual(result, 30)

    def test_time_remaining_returns_zero_when_expired(self):
        """Test returns 0 when affliction has expired."""
        session = {"afflictions": {"blind": {"expires_at": time.time() - 10}}}

        result = get_affliction_time_remaining(session, "blind")

        self.assertEqual(result, 0.0)


class ProcessAfflictionExpiryTest(unittest.IsolatedAsyncioTestCase):
    """Test process_affliction_expiry function."""

    def setUp(self):
        """Set up test fixtures."""
        self.sio = Mock()
        self.utils = Mock()
        self.utils.send_message = AsyncMock()

    async def test_expiry_skips_sessions_without_player(self):
        """Test skips sessions without player."""
        online_sessions = {"sid1": {"afflictions": {"blind": {"expires_at": 0}}}}

        await process_affliction_expiry(self.sio, online_sessions, self.utils)

        self.utils.send_message.assert_not_called()

    async def test_expiry_skips_sessions_without_afflictions(self):
        """Test skips sessions without afflictions."""
        player = Mock()
        player.name = "Test"
        online_sessions = {"sid1": {"player": player}}

        await process_affliction_expiry(self.sio, online_sessions, self.utils)

        self.utils.send_message.assert_not_called()

    async def test_expiry_removes_expired_afflictions(self):
        """Test removes expired afflictions."""
        player = Mock()
        player.name = "Test"
        online_sessions = {
            "sid1": {
                "player": player,
                "afflictions": {"blind": {"expires_at": time.time() - 10}},
            }
        }

        await process_affliction_expiry(self.sio, online_sessions, self.utils)

        self.assertNotIn("blind", online_sessions["sid1"]["afflictions"])

    async def test_expiry_sends_message_for_expired(self):
        """Test sends appropriate message when affliction expires."""
        player = Mock()
        player.name = "Test"
        online_sessions = {
            "sid1": {
                "player": player,
                "afflictions": {"blind": {"expires_at": time.time() - 10}},
            }
        }

        await process_affliction_expiry(self.sio, online_sessions, self.utils)

        self.utils.send_message.assert_called_once()
        call_args = self.utils.send_message.call_args[0]
        self.assertIn("vision clears", call_args[2])

    async def test_expiry_clears_sleeping_for_magic_sleep(self):
        """Test clears sleeping flag when magic_sleep expires."""
        player = Mock()
        player.name = "Test"
        online_sessions = {
            "sid1": {
                "player": player,
                "sleeping": True,
                "afflictions": {"magic_sleep": {"expires_at": time.time() - 10}},
            }
        }

        await process_affliction_expiry(self.sio, online_sessions, self.utils)

        self.assertFalse(online_sessions["sid1"]["sleeping"])

    async def test_expiry_keeps_non_expired_afflictions(self):
        """Test keeps afflictions that haven't expired."""
        player = Mock()
        player.name = "Test"
        online_sessions = {
            "sid1": {
                "player": player,
                "afflictions": {
                    "blind": {"expires_at": time.time() - 10},  # Expired
                    "deaf": {"expires_at": time.time() + 60},  # Not expired
                },
            }
        }

        await process_affliction_expiry(self.sio, online_sessions, self.utils)

        self.assertNotIn("blind", online_sessions["sid1"]["afflictions"])
        self.assertIn("deaf", online_sessions["sid1"]["afflictions"])

    async def test_expiry_uses_default_message_for_unknown(self):
        """Test uses default message for unknown affliction type."""
        player = Mock()
        player.name = "Test"
        online_sessions = {
            "sid1": {
                "player": player,
                "afflictions": {"custom_curse": {"expires_at": time.time() - 10}},
            }
        }

        await process_affliction_expiry(self.sio, online_sessions, self.utils)

        call_args = self.utils.send_message.call_args[0]
        self.assertIn("custom_curse", call_args[2])
        self.assertIn("wears off", call_args[2])


class FindPlayerSidTest(unittest.TestCase):
    """Test find_player_sid function."""

    def test_find_player_sid_finds_player(self):
        """Test finds player's session ID."""
        player = Mock()
        online_sessions = {"sid123": {"player": player}}

        result = find_player_sid(player, online_sessions)

        self.assertEqual(result, "sid123")

    def test_find_player_sid_returns_none_when_not_found(self):
        """Test returns None when player not found."""
        player = Mock()
        other_player = Mock()
        online_sessions = {"sid123": {"player": other_player}}

        result = find_player_sid(player, online_sessions)

        self.assertIsNone(result)

    def test_find_player_sid_returns_none_for_empty_sessions(self):
        """Test returns None for empty sessions."""
        player = Mock()
        online_sessions: dict = {}

        result = find_player_sid(player, online_sessions)

        self.assertIsNone(result)


class FindPlayerByNameTest(unittest.TestCase):
    """Test find_player_by_name function."""

    def test_find_player_by_name_finds_player(self):
        """Test finds player by name."""
        player = Mock()
        player.name = "TestPlayer"
        online_sessions = {"sid123": {"player": player}}

        result_player, result_sid = find_player_by_name("TestPlayer", online_sessions)

        self.assertEqual(result_player, player)
        self.assertEqual(result_sid, "sid123")

    def test_find_player_by_name_case_insensitive(self):
        """Test finds player with case-insensitive match."""
        player = Mock()
        player.name = "TestPlayer"
        online_sessions = {"sid123": {"player": player}}

        result_player, result_sid = find_player_by_name("testplayer", online_sessions)

        self.assertEqual(result_player, player)
        self.assertEqual(result_sid, "sid123")

    def test_find_player_by_name_returns_none_when_not_found(self):
        """Test returns (None, None) when player not found."""
        player = Mock()
        player.name = "OtherPlayer"
        online_sessions = {"sid123": {"player": player}}

        result_player, result_sid = find_player_by_name("TestPlayer", online_sessions)

        self.assertIsNone(result_player)
        self.assertIsNone(result_sid)

    def test_find_player_by_name_skips_sessions_without_player(self):
        """Test skips sessions without player object."""
        online_sessions = {"sid123": {"some_data": "value"}}

        result_player, result_sid = find_player_by_name("TestPlayer", online_sessions)

        self.assertIsNone(result_player)
        self.assertIsNone(result_sid)


if __name__ == "__main__":
    unittest.main()
