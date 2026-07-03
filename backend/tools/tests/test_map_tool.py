# backend/tools/tests/test_map_tool.py
"""Tests for the map_tool CLI."""

import io
import unittest
from contextlib import redirect_stdout
from typing import Dict, List, Tuple

from models.Room import Room
from tools.map_tool import main
from tools.map_validation import OPPOSITE_DIRECTIONS


def clean_world() -> Dict[str, Room]:
    rooms = {
        "square": Room("square", "Square", "The square.", exits={"east": "tavern"}),
        "tavern": Room("tavern", "Tavern", "The tavern.", exits={"west": "square"}),
    }
    return rooms


def broken_world() -> Dict[str, Room]:
    rooms = clean_world()
    rooms["square"].exits["north"] = "tavern"  # contradicts east placement
    return rooms


class MapToolMainTest(unittest.TestCase):
    """Test map_tool.main argument handling and exit codes."""

    def _run(self, argv: List[str], world: Dict[str, Room]) -> Tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(argv, world_loader=lambda: world)
        return code, buffer.getvalue()

    def test_main_renders_map_and_returns_zero(self) -> None:
        """Test main prints the map and returns 0 without --strict."""
        # Act
        code, output = self._run([], clean_world())

        # Assert
        self.assertEqual(code, 0)
        self.assertIn("square", output)
        self.assertIn("SUMMARY: OK", output)

    def test_main_strict_returns_one_on_errors(self) -> None:
        """Test --strict exits 1 when the world has errors."""
        # Act
        code, output = self._run(["--strict"], broken_world())

        # Assert
        self.assertEqual(code, 1)
        self.assertIn("ERROR(S)", output)

    def test_main_strict_returns_zero_on_clean_world(self) -> None:
        """Test --strict exits 0 when the world is clean."""
        code, _ = self._run(["--strict"], clean_world())
        self.assertEqual(code, 0)

    def test_main_z_filter_limits_grid(self) -> None:
        """Test --z renders only the requested level."""
        # Arrange
        rooms = clean_world()
        rooms["loft"] = Room("loft", "Loft", "A loft.", exits={"down": "square"})
        rooms["square"].exits["up"] = "loft"

        # Act
        _, output = self._run(["--z", "1"], rooms)

        # Assert
        self.assertIn("z=1", output)
        self.assertNotIn("z=0", output)

    def test_main_static_only_disables_latent_classification(self) -> None:
        """Test --static-only is accepted and still renders."""
        code, output = self._run(["--static-only"], clean_world())
        self.assertEqual(code, 0)
        self.assertIn("SUMMARY", output)

    def test_main_custom_spawn(self) -> None:
        """Test --spawn anchors the layout at the given room."""
        code, output = self._run(["--spawn", "tavern"], clean_world())
        self.assertEqual(code, 0)
        self.assertIn("tavern", output)


if __name__ == "__main__":
    unittest.main()
