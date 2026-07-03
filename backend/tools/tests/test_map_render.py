# backend/tools/tests/test_map_render.py
"""Tests for tools.map_render."""

import unittest
from typing import Dict

from models.Room import Room
from tools.map_render import render_ascii
from tools.map_validation import OPPOSITE_DIRECTIONS, validate_world


def make_rooms(exits_by_room: Dict[str, Dict[str, str]]) -> Dict[str, Room]:
    return {
        room_id: Room(room_id, room_id.title(), f"The {room_id}.", exits=dict(exits))
        for room_id, exits in exits_by_room.items()
    }


def two_way(spec: Dict[str, Dict[str, str]], a: str, direction: str, b: str) -> None:
    spec.setdefault(a, {})[direction] = b
    spec.setdefault(b, {})[OPPOSITE_DIRECTIONS[direction]] = a


class RenderGridTest(unittest.TestCase):
    """Test the ASCII grid rendering."""

    def test_render_ascii_two_way_horizontal_connector(self) -> None:
        """Test a reciprocal east-west pair renders a solid connector."""
        # Arrange
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "square", "east", "field")
        rooms = make_rooms(spec)
        report = validate_world(rooms, spawn="square")

        # Act
        output = render_ascii(report, rooms)

        # Assert
        self.assertIn("[   square   ]----[   field    ]", output)
        self.assertIn("SUMMARY: OK", output)

    def test_render_ascii_one_way_horizontal_connector(self) -> None:
        """Test a one-way east exit renders an arrow connector."""
        # Arrange
        rooms = make_rooms({"square": {"east": "field"}, "field": {}})
        report = validate_world(rooms, spawn="square")

        # Act
        output = render_ascii(report, rooms)

        # Assert
        self.assertIn("[   square   ] -> [   field    ]", output)

    def test_render_ascii_vertical_connector(self) -> None:
        """Test a reciprocal north-south pair renders a pipe between rows."""
        # Arrange
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "square", "north", "church")
        rooms = make_rooms(spec)
        report = validate_world(rooms, spawn="square")

        # Act
        lines = render_ascii(report, rooms).splitlines()

        # Assert
        church_row = next(i for i, line in enumerate(lines) if "church" in line)
        self.assertIn("|", lines[church_row + 1])
        self.assertIn("square", lines[church_row + 2])

    def test_render_ascii_marks_up_down_and_stacked(self) -> None:
        """Test up/down markers and stacked-room suffix render."""
        # Arrange: two rooms forced onto one coordinate plus an up exit.
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "square", "east", "smith")
        two_way(spec, "plaza", "east", "smith")  # plaza collides with square
        two_way(spec, "square", "up", "loft")
        rooms = make_rooms(spec)
        report = validate_world(rooms, spawn="square")

        # Act
        output = render_ascii(report, rooms)

        # Assert
        self.assertIn("+1", output)
        self.assertIn("stacked at same coordinate", output)
        self.assertIn("^", output)  # up marker on square's cell

    def test_render_ascii_only_z_filters_levels(self) -> None:
        """Test only_z restricts which grid levels are rendered."""
        # Arrange
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "square", "up", "loft")
        rooms = make_rooms(spec)
        report = validate_world(rooms, spawn="square")

        # Act
        output = render_ascii(report, rooms, only_z=1)

        # Assert
        self.assertIn("z=1", output)
        self.assertNotIn("z=0", output)

    def test_render_ascii_compresses_long_gaps(self) -> None:
        """Test long vertical gaps collapse into a distance marker."""
        # Arrange: two rooms six steps apart connected by a chain we delete.
        spec: Dict[str, Dict[str, str]] = {}
        chain = ["a", "b", "c", "d", "e", "f", "g"]
        for near, far in zip(chain, chain[1:]):
            two_way(spec, near, "south", far)
        rooms = make_rooms(spec)
        # Hide the middle rooms from rendering by pushing them to another z.
        report = validate_world(rooms, spawn="a")
        for mid in chain[1:-1]:
            report.coords[mid] = (
                report.coords[mid][0],
                report.coords[mid][1],
                5,
            )

        # Act
        output = render_ascii(report, rooms, only_z=0)

        # Assert
        self.assertIn("~ ~ ~", output)


class RenderFindingsTest(unittest.TestCase):
    """Test the findings sections of the render."""

    def test_render_ascii_lists_suspect_bugs_and_error_summary(self) -> None:
        """Test suspect one-ways appear with an error summary."""
        # Arrange
        rooms = make_rooms({"a": {"north": "b"}, "b": {}})
        report = validate_world(rooms, spawn="a")

        # Act
        output = render_ascii(report, rooms)

        # Assert
        self.assertIn("NON-RECIPROCAL [ERROR]", output)
        self.assertIn("a --north--> b", output)
        self.assertIn("ERROR(S)", output)

    def test_render_ascii_lists_portal_exits(self) -> None:
        """Test in/out exits are listed in the portal section."""
        # Arrange
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "camp", "in", "tent")
        rooms = make_rooms(spec)
        report = validate_world(rooms, spawn="camp")

        # Act
        output = render_ascii(report, rooms)

        # Assert
        self.assertIn("PORTAL EXITS", output)
        self.assertIn("camp --in--> tent", output)

    def test_render_ascii_lists_disconnected_components(self) -> None:
        """Test unreachable rooms appear in the disconnected section."""
        # Arrange
        rooms = make_rooms({"a": {}, "island": {}})
        report = validate_world(rooms, spawn="a")

        # Act
        output = render_ascii(report, rooms)

        # Assert
        self.assertIn("DISCONNECTED [WARNING]", output)
        self.assertIn("island", output)


if __name__ == "__main__":
    unittest.main()
