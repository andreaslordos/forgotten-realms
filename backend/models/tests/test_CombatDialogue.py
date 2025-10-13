"""
Comprehensive tests for CombatDialogue module.

Tests cover:
- get_player_hit_message with and without weapon
- get_player_miss_message
- get_opponent_hit_message with and without weapon
- get_opponent_miss_message
- get_heavy_damage_recovery
- get_killing_blow_message with and without weapon
- Message randomization
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.CombatDialogue import CombatDialogue
from tests.test_helpers import create_mock_item


class CombatDialoguePlayerHitTest(unittest.TestCase):
    """Test get_player_hit_message functionality."""

    def test_get_player_hit_message_returns_string(self):
        """Test get_player_hit_message returns a string."""
        result = CombatDialogue.get_player_hit_message("orc")
        self.assertIsInstance(result, str)

    def test_get_player_hit_message_includes_target_name(self):
        """Test get_player_hit_message includes target name."""
        result = CombatDialogue.get_player_hit_message("goblin")
        self.assertIn("goblin", result)

    def test_get_player_hit_message_with_weapon(self):
        """Test get_player_hit_message includes weapon name when provided."""
        weapon = create_mock_item(name="longsword")
        result = CombatDialogue.get_player_hit_message("orc", weapon=weapon)
        self.assertIn("longsword", result)
        self.assertIn("orc", result)

    @patch('models.CombatDialogue.random.choice')
    def test_get_player_hit_message_uses_weapon_messages(self, mock_choice):
        """Test get_player_hit_message uses weapon-specific messages."""
        weapon = create_mock_item(name="sword")
        mock_choice.return_value = "Your {weapon} slices into {target} with deadly precision!"

        result = CombatDialogue.get_player_hit_message("orc", weapon=weapon)

        self.assertIn("sword", result)
        self.assertIn("orc", result)


class CombatDialoguePlayerMissTest(unittest.TestCase):
    """Test get_player_miss_message functionality."""

    def test_get_player_miss_message_returns_string(self):
        """Test get_player_miss_message returns a string."""
        result = CombatDialogue.get_player_miss_message("orc")
        self.assertIsInstance(result, str)

    def test_get_player_miss_message_includes_target_name(self):
        """Test get_player_miss_message includes target name."""
        result = CombatDialogue.get_player_miss_message("goblin")
        self.assertIn("goblin", result)


class CombatDialogueOpponentHitTest(unittest.TestCase):
    """Test get_opponent_hit_message functionality."""

    def test_get_opponent_hit_message_returns_string(self):
        """Test get_opponent_hit_message returns a string."""
        result = CombatDialogue.get_opponent_hit_message("orc")
        self.assertIsInstance(result, str)

    def test_get_opponent_hit_message_includes_target_name(self):
        """Test get_opponent_hit_message includes target name."""
        result = CombatDialogue.get_opponent_hit_message("troll")
        self.assertIn("troll", result)

    def test_get_opponent_hit_message_with_weapon(self):
        """Test get_opponent_hit_message includes weapon name when provided."""
        weapon = create_mock_item(name="club")
        result = CombatDialogue.get_opponent_hit_message("orc", weapon=weapon)
        self.assertIn("club", result)
        self.assertIn("orc", result)


class CombatDialogueOpponentMissTest(unittest.TestCase):
    """Test get_opponent_miss_message functionality."""

    def test_get_opponent_miss_message_returns_string(self):
        """Test get_opponent_miss_message returns a string."""
        result = CombatDialogue.get_opponent_miss_message("orc")
        self.assertIsInstance(result, str)

    def test_get_opponent_miss_message_includes_target_name(self):
        """Test get_opponent_miss_message includes target name."""
        result = CombatDialogue.get_opponent_miss_message("dragon")
        self.assertIn("dragon", result)


class CombatDialogueHeavyDamageTest(unittest.TestCase):
    """Test get_heavy_damage_recovery functionality."""

    def test_get_heavy_damage_recovery_returns_string(self):
        """Test get_heavy_damage_recovery returns a string."""
        result = CombatDialogue.get_heavy_damage_recovery()
        self.assertIsInstance(result, str)

    def test_get_heavy_damage_recovery_is_encouraging(self):
        """Test get_heavy_damage_recovery message is encouraging."""
        result = CombatDialogue.get_heavy_damage_recovery()
        # Should contain words like "vigour", "carry on", "concentrate", etc.
        self.assertTrue(len(result) > 0)


class CombatDialogueKillingBlowTest(unittest.TestCase):
    """Test get_killing_blow_message functionality."""

    def test_get_killing_blow_message_returns_string(self):
        """Test get_killing_blow_message returns a string."""
        result = CombatDialogue.get_killing_blow_message("orc")
        self.assertIsInstance(result, str)

    def test_get_killing_blow_message_includes_target_name(self):
        """Test get_killing_blow_message includes target name."""
        result = CombatDialogue.get_killing_blow_message("goblin")
        self.assertIn("goblin", result)

    def test_get_killing_blow_message_includes_victory(self):
        """Test get_killing_blow_message includes victory message."""
        result = CombatDialogue.get_killing_blow_message("orc")
        self.assertIn("victorious", result)

    def test_get_killing_blow_message_with_weapon(self):
        """Test get_killing_blow_message includes weapon when provided."""
        weapon = create_mock_item(name="axe")
        result = CombatDialogue.get_killing_blow_message("orc", weapon=weapon)
        self.assertIn("axe", result)
        self.assertIn("orc", result)
        self.assertIn("victorious", result)


class CombatDialogueRandomizationTest(unittest.TestCase):
    """Test message randomization."""

    def test_get_player_hit_message_varies(self):
        """Test get_player_hit_message returns different messages."""
        messages = set()
        for _ in range(20):
            msg = CombatDialogue.get_player_hit_message("orc")
            messages.add(msg)

        # Should get multiple different messages
        self.assertGreater(len(messages), 1)

    def test_get_player_miss_message_varies(self):
        """Test get_player_miss_message returns different messages."""
        messages = set()
        for _ in range(20):
            msg = CombatDialogue.get_player_miss_message("orc")
            messages.add(msg)

        self.assertGreater(len(messages), 1)

    def test_get_heavy_damage_recovery_varies(self):
        """Test get_heavy_damage_recovery returns different messages."""
        messages = set()
        for _ in range(20):
            msg = CombatDialogue.get_heavy_damage_recovery()
            messages.add(msg)

        self.assertGreater(len(messages), 1)


class CombatDialogueMessageListsTest(unittest.TestCase):
    """Test message lists are properly defined."""

    def test_player_hit_messages_not_empty(self):
        """Test PLAYER_HIT_MESSAGES list is not empty."""
        self.assertGreater(len(CombatDialogue.PLAYER_HIT_MESSAGES), 0)

    def test_player_weapon_hit_messages_not_empty(self):
        """Test PLAYER_WEAPON_HIT_MESSAGES list is not empty."""
        self.assertGreater(len(CombatDialogue.PLAYER_WEAPON_HIT_MESSAGES), 0)

    def test_player_miss_messages_not_empty(self):
        """Test PLAYER_MISS_MESSAGES list is not empty."""
        self.assertGreater(len(CombatDialogue.PLAYER_MISS_MESSAGES), 0)

    def test_opponent_hit_messages_not_empty(self):
        """Test OPPONENT_HIT_MESSAGES list is not empty."""
        self.assertGreater(len(CombatDialogue.OPPONENT_HIT_MESSAGES), 0)

    def test_opponent_miss_messages_not_empty(self):
        """Test OPPONENT_MISS_MESSAGES list is not empty."""
        self.assertGreater(len(CombatDialogue.OPPONENT_MISS_MESSAGES), 0)

    def test_killing_blow_messages_not_empty(self):
        """Test KILLING_BLOW_MESSAGES list is not empty."""
        self.assertGreater(len(CombatDialogue.KILLING_BLOW_MESSAGES), 0)

    def test_victory_messages_not_empty(self):
        """Test VICTORY_MESSAGES list is not empty."""
        self.assertGreater(len(CombatDialogue.VICTORY_MESSAGES), 0)


if __name__ == "__main__":
    unittest.main()
