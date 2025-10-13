"""
Comprehensive tests for Levels module.

Tests cover:
- Level data structure validation
- Level thresholds
- Level progression
- Stat distribution
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models.Levels import levels


class LevelsDataStructureTest(unittest.TestCase):
    """Test levels data structure."""

    def test_levels_is_dict(self):
        """Test levels is a dictionary."""
        self.assertIsInstance(levels, dict)

    def test_levels_has_all_tiers(self):
        """Test levels has all expected tier thresholds."""
        expected_thresholds = [0, 400, 800, 1600, 3200, 6400, 12800, 25600, 51200, 102400]
        for threshold in expected_thresholds:
            self.assertIn(threshold, levels)

    def test_levels_count_is_ten(self):
        """Test levels has exactly 10 level tiers."""
        self.assertEqual(len(levels), 10)


class LevelsAttributesTest(unittest.TestCase):
    """Test level attributes."""

    def test_all_levels_have_name(self):
        """Test all levels have a name attribute."""
        for points, level_data in levels.items():
            self.assertIn('name', level_data)
            self.assertIsInstance(level_data['name'], str)
            self.assertTrue(len(level_data['name']) > 0)

    def test_all_levels_have_stamina(self):
        """Test all levels have stamina attribute."""
        for points, level_data in levels.items():
            self.assertIn('stamina', level_data)
            self.assertIsInstance(level_data['stamina'], int)
            self.assertGreater(level_data['stamina'], 0)

    def test_all_levels_have_strength(self):
        """Test all levels have strength attribute."""
        for points, level_data in levels.items():
            self.assertIn('strength', level_data)
            self.assertIsInstance(level_data['strength'], int)
            self.assertGreater(level_data['strength'], 0)

    def test_all_levels_have_dexterity(self):
        """Test all levels have dexterity attribute."""
        for points, level_data in levels.items():
            self.assertIn('dexterity', level_data)
            self.assertIsInstance(level_data['dexterity'], int)
            self.assertGreater(level_data['dexterity'], 0)

    def test_all_levels_have_magic(self):
        """Test all levels have magic attribute."""
        for points, level_data in levels.items():
            self.assertIn('magic', level_data)
            self.assertIsInstance(level_data['magic'], int)
            self.assertGreaterEqual(level_data['magic'], 0)

    def test_all_levels_have_carrying_capacity(self):
        """Test all levels have carrying_capacity_num attribute."""
        for points, level_data in levels.items():
            self.assertIn('carrying_capacity_num', level_data)
            self.assertIsInstance(level_data['carrying_capacity_num'], int)
            self.assertGreater(level_data['carrying_capacity_num'], 0)


class LevelsNameTest(unittest.TestCase):
    """Test level names."""

    def test_level_names_are_correct(self):
        """Test level names match expected values."""
        expected_names = {
            0: "Neophyte",
            400: "Novice",
            800: "Acolyte",
            1600: "Scholar",
            3200: "Magister",
            6400: "Archon",
            12800: "Warlock",
            25600: "Guardian",
            51200: "Sovereign",
            102400: "Archmage"
        }
        for points, expected_name in expected_names.items():
            self.assertEqual(levels[points]['name'], expected_name)

    def test_all_level_names_are_unique(self):
        """Test all level names are unique."""
        names = [level_data['name'] for level_data in levels.values()]
        self.assertEqual(len(names), len(set(names)))


class LevelsProgressionTest(unittest.TestCase):
    """Test level progression."""

    def test_stamina_increases_with_level(self):
        """Test stamina increases with each level."""
        sorted_levels = sorted(levels.items())
        for i in range(len(sorted_levels) - 1):
            current_stamina = sorted_levels[i][1]['stamina']
            next_stamina = sorted_levels[i + 1][1]['stamina']
            self.assertLess(current_stamina, next_stamina)

    def test_strength_increases_with_level(self):
        """Test strength increases with each level."""
        sorted_levels = sorted(levels.items())
        for i in range(len(sorted_levels) - 1):
            current_strength = sorted_levels[i][1]['strength']
            next_strength = sorted_levels[i + 1][1]['strength']
            self.assertLess(current_strength, next_strength)

    def test_dexterity_increases_with_level(self):
        """Test dexterity increases with each level."""
        sorted_levels = sorted(levels.items())
        for i in range(len(sorted_levels) - 1):
            current_dexterity = sorted_levels[i][1]['dexterity']
            next_dexterity = sorted_levels[i + 1][1]['dexterity']
            self.assertLess(current_dexterity, next_dexterity)

    def test_magic_increases_with_level(self):
        """Test magic increases with each level."""
        sorted_levels = sorted(levels.items())
        for i in range(len(sorted_levels) - 1):
            current_magic = sorted_levels[i][1]['magic']
            next_magic = sorted_levels[i + 1][1]['magic']
            self.assertLessEqual(current_magic, next_magic)

    def test_carrying_capacity_increases_with_level(self):
        """Test carrying capacity increases with each level."""
        sorted_levels = sorted(levels.items())
        for i in range(len(sorted_levels) - 1):
            current_capacity = sorted_levels[i][1]['carrying_capacity_num']
            next_capacity = sorted_levels[i + 1][1]['carrying_capacity_num']
            self.assertLess(current_capacity, next_capacity)


class LevelsThresholdTest(unittest.TestCase):
    """Test level thresholds."""

    def test_first_level_starts_at_zero(self):
        """Test first level starts at 0 points."""
        self.assertIn(0, levels)

    def test_final_level_is_archmage(self):
        """Test final level is Archmage."""
        max_threshold = max(levels.keys())
        self.assertEqual(levels[max_threshold]['name'], 'Archmage')

    def test_thresholds_double_each_level_after_first_two(self):
        """Test thresholds approximately double after initial levels."""
        # After first two levels, thresholds roughly double
        thresholds = sorted(levels.keys())
        # Start from index 2 (800)
        for i in range(2, len(thresholds) - 1):
            current = thresholds[i]
            next_threshold = thresholds[i + 1]
            self.assertEqual(next_threshold, current * 2)


class LevelsStatBalanceTest(unittest.TestCase):
    """Test stat balance across levels."""

    def test_neophyte_has_lowest_stats(self):
        """Test Neophyte has lowest overall stats."""
        neophyte = levels[0]
        self.assertEqual(neophyte['stamina'], 45)
        self.assertEqual(neophyte['strength'], 45)
        self.assertEqual(neophyte['dexterity'], 45)
        self.assertEqual(neophyte['magic'], 0)

    def test_archmage_has_highest_stats(self):
        """Test Archmage has highest overall stats."""
        archmage = levels[102400]
        self.assertEqual(archmage['stamina'], 100)
        self.assertEqual(archmage['strength'], 100)
        self.assertEqual(archmage['dexterity'], 100)
        self.assertEqual(archmage['magic'], 100)

    def test_stats_are_balanced_at_same_level(self):
        """Test stamina, strength, and dexterity are equal at each level."""
        for points, level_data in levels.items():
            self.assertEqual(level_data['stamina'], level_data['strength'])
            self.assertEqual(level_data['stamina'], level_data['dexterity'])


class LevelsCarryingCapacityTest(unittest.TestCase):
    """Test carrying capacity progression."""

    def test_carrying_capacity_starts_at_six(self):
        """Test carrying capacity starts at 6 for Neophyte."""
        self.assertEqual(levels[0]['carrying_capacity_num'], 6)

    def test_carrying_capacity_ends_at_fifteen(self):
        """Test carrying capacity ends at 15 for Archmage."""
        self.assertEqual(levels[102400]['carrying_capacity_num'], 15)

    def test_carrying_capacity_increases_by_one_per_level(self):
        """Test carrying capacity increases by 1 each level."""
        sorted_levels = sorted(levels.items())
        for i in range(len(sorted_levels) - 1):
            current_capacity = sorted_levels[i][1]['carrying_capacity_num']
            next_capacity = sorted_levels[i + 1][1]['carrying_capacity_num']
            self.assertEqual(next_capacity, current_capacity + 1)


if __name__ == "__main__":
    unittest.main()
