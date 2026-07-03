# backend/tools/tests/test_map_validation.py
"""Tests for tools.map_validation."""

import unittest
from typing import Dict, List, Tuple

from models.Room import Room
from models.StatefulItem import StatefulItem
from tools.map_validation import (
    CLASS_ONE_WAY_PUZZLE,
    CLASS_PUZZLE_GATED,
    CLASS_SUSPECT_BUG,
    CLASS_WRONG_DIRECTION,
    DIRECTION_VECTORS,
    OPPOSITE_DIRECTIONS,
    LatentExit,
    assign_coordinates,
    collect_latent_exits,
    find_collisions,
    find_components,
    find_dangling,
    find_non_reciprocal,
    find_nonstandard_directions,
    static_edges,
    validate_world,
)


def make_rooms(
    exits_by_room: Dict[str, Dict[str, str]],
) -> Dict[str, Room]:
    """Build a dict of Rooms from {room_id: {direction: target}}."""
    return {
        room_id: Room(room_id, room_id.title(), f"The {room_id}.", exits=dict(exits))
        for room_id, exits in exits_by_room.items()
    }


def two_way(
    exits_by_room: Dict[str, Dict[str, str]],
    a: str,
    direction: str,
    b: str,
) -> None:
    """Add a reciprocal exit pair to a make_rooms spec."""
    exits_by_room.setdefault(a, {})[direction] = b
    exits_by_room.setdefault(b, {})[OPPOSITE_DIRECTIONS[direction]] = a


class DirectionTablesTest(unittest.TestCase):
    """Test the direction constant tables are internally consistent."""

    def test_direction_vectors_opposites_negate(self) -> None:
        """Test every vector direction's opposite has the negated vector."""
        for direction, vec in DIRECTION_VECTORS.items():
            opposite = OPPOSITE_DIRECTIONS[direction]
            self.assertEqual(
                DIRECTION_VECTORS[opposite],
                (-vec[0], -vec[1], -vec[2]),
                f"{direction}/{opposite} vectors do not negate",
            )

    def test_opposite_directions_are_symmetric(self) -> None:
        """Test OPPOSITE_DIRECTIONS maps back to itself both ways."""
        for direction, opposite in OPPOSITE_DIRECTIONS.items():
            self.assertEqual(OPPOSITE_DIRECTIONS[opposite], direction)


class StaticEdgesTest(unittest.TestCase):
    """Test static_edges extraction."""

    def test_static_edges_lists_all_exits_lowercased(self) -> None:
        """Test static_edges returns every exit with lowercased direction."""
        rooms = make_rooms({"a": {"North": "b"}, "b": {}})
        self.assertEqual(static_edges(rooms), [("a", "north", "b")])


class CollectLatentExitsTest(unittest.TestCase):
    """Test latent-exit introspection of StatefulItem interactions."""

    def _rug_room(self) -> Dict[str, Room]:
        rooms = make_rooms({"tavern": {}, "cellar": {"up": "tavern"}})
        rug = StatefulItem(
            "rug",
            "rug1",
            "A dusty rug.",
            takeable=False,
            state="flat",
            room_id="tavern",
        )
        rug.add_state_description("moved", "The rug has been pulled aside.")
        rug.add_interaction("move", target_state="moved", add_exit=("down", "cellar"))
        rooms["tavern"].add_item(rug)
        return rooms

    def test_collect_latent_exits_finds_add_exit(self) -> None:
        """Test add_exit interactions are collected as latent exits."""
        # Arrange
        rooms = self._rug_room()

        # Act
        latent = collect_latent_exits(rooms)

        # Assert
        self.assertEqual(
            latent,
            [LatentExit("tavern", "down", "cellar", "rug1", "move")],
        )

    def test_collect_latent_exits_finds_reciprocal_exit(self) -> None:
        """Test reciprocal_exit interactions are collected with their source room."""
        # Arrange
        rooms = make_rooms({"gate": {}, "beyond": {}})
        lever = StatefulItem(
            "lever",
            "lever1",
            "A rusted lever.",
            takeable=False,
            state="up",
            room_id="gate",
        )
        lever.add_state_description("down", "The lever is down.")
        lever.add_interaction(
            "pull",
            target_state="down",
            add_exit=("south", "beyond"),
            reciprocal_exit=("beyond", "north", "gate"),
        )
        rooms["gate"].add_item(lever)

        # Act
        latent = collect_latent_exits(rooms)

        # Assert
        self.assertIn(LatentExit("gate", "south", "beyond", "lever1", "pull"), latent)
        self.assertIn(LatentExit("beyond", "north", "gate", "lever1", "pull"), latent)

    def test_collect_latent_exits_inspects_hidden_items(self) -> None:
        """Test items hidden behind conditions still contribute latent exits."""
        # Arrange
        rooms = make_rooms({"crypt": {}, "vault": {}})
        panel = StatefulItem(
            "panel",
            "panel1",
            "A stone panel.",
            takeable=False,
            state="closed",
            room_id="crypt",
        )
        panel.add_state_description("open", "The panel stands open.")
        panel.add_interaction("push", target_state="open", add_exit=("down", "vault"))
        rooms["crypt"].add_hidden_item(panel, lambda gs: True)

        # Act
        latent = collect_latent_exits(rooms)

        # Assert
        self.assertEqual(len(latent), 1)
        self.assertEqual(latent[0].target_room_id, "vault")

    def test_collect_latent_exits_deduplicates(self) -> None:
        """Test the same latent exit from two interactions appears once."""
        # Arrange
        rooms = self._rug_room()
        rug = rooms["tavern"].items[0]
        rug.add_interaction("pull", target_state="moved", add_exit=("down", "cellar"))

        # Act
        latent = collect_latent_exits(rooms)

        # Assert
        self.assertEqual(len(latent), 1)

    def test_collect_latent_exits_ignores_plain_items(self) -> None:
        """Test rooms with non-stateful items produce no latent exits."""
        rooms = make_rooms({"a": {}})
        self.assertEqual(collect_latent_exits(rooms), [])


class AssignCoordinatesTest(unittest.TestCase):
    """Test BFS coordinate assignment."""

    def test_assign_coordinates_places_linear_path(self) -> None:
        """Test a west-east corridor gets increasing x coordinates."""
        # Arrange
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "a", "east", "b")
        two_way(spec, "b", "east", "c")
        rooms = make_rooms(spec)

        # Act
        result = assign_coordinates(rooms, "a")

        # Assert
        self.assertEqual(result.coords["a"], (0, 0, 0))
        self.assertEqual(result.coords["b"], (1, 0, 0))
        self.assertEqual(result.coords["c"], (2, 0, 0))
        self.assertEqual(result.contradictions, [])
        self.assertEqual(result.unplaced, [])

    def test_assign_coordinates_places_room_via_incoming_edge(self) -> None:
        """Test a room reachable only via its own outgoing exit is still placed."""
        # Arrange: barrow has up->clearing but clearing has no down (yet).
        rooms = make_rooms({"clearing": {}, "barrow": {"up": "clearing"}})

        # Act
        result = assign_coordinates(rooms, "clearing")

        # Assert: barrow ends up directly below clearing.
        self.assertEqual(result.coords["barrow"], (0, 0, -1))

    def test_assign_coordinates_reports_contradiction(self) -> None:
        """Test an exit disagreeing with earlier placement is a contradiction."""
        # Arrange: c is east of b (=(2,0)), but a claims c is directly north.
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "a", "east", "b")
        two_way(spec, "b", "east", "c")
        spec["a"]["north"] = "c"
        rooms = make_rooms(spec)

        # Act
        result = assign_coordinates(rooms, "a")

        # Assert
        self.assertEqual(len(result.contradictions), 1)
        self.assertEqual(result.contradictions[0].target_room_id, "c")

    def test_assign_coordinates_places_portal_target_approximately(self) -> None:
        """Test in/out targets are placed nearby and marked approximate."""
        # Arrange
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "camp", "in", "tent")
        rooms = make_rooms(spec)

        # Act
        result = assign_coordinates(rooms, "camp")

        # Assert
        self.assertIn("tent", result.coords)
        self.assertIn("tent", result.approx_placed)
        self.assertNotEqual(result.coords["tent"], result.coords["camp"])

    def test_assign_coordinates_marks_portal_cluster_as_approx(self) -> None:
        """Test rooms placed transitively from a portal seed are approximate."""
        # Arrange: tent connects onward to a back room by vector.
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "camp", "in", "tent")
        two_way(spec, "tent", "north", "backroom")
        rooms = make_rooms(spec)

        # Act
        result = assign_coordinates(rooms, "camp")

        # Assert
        self.assertIn("backroom", result.approx_placed)

    def test_assign_coordinates_places_disconnected_cluster(self) -> None:
        """Test fully disconnected rooms are placed offset and reported unplaced."""
        # Arrange
        spec: Dict[str, Dict[str, str]] = {"a": {}}
        two_way(spec, "island1", "east", "island2")
        rooms = make_rooms(spec)

        # Act
        result = assign_coordinates(rooms, "a")

        # Assert
        self.assertIn("island1", result.coords)
        self.assertIn("island1", result.approx_placed)
        self.assertCountEqual(result.unplaced, ["island1", "island2"])

    def test_assign_coordinates_handles_missing_start(self) -> None:
        """Test a start room that doesn't exist leaves rooms in offset clusters."""
        # Arrange
        rooms = make_rooms({"a": {}})

        # Act
        result = assign_coordinates(rooms, "nope")

        # Assert
        self.assertIn("a", result.coords)
        self.assertEqual(result.unplaced, ["a"])


class FindNonReciprocalTest(unittest.TestCase):
    """Test one-way exit classification."""

    def test_find_non_reciprocal_ignores_proper_pairs(self) -> None:
        """Test reciprocal exits produce no findings."""
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "a", "north", "b")
        self.assertEqual(find_non_reciprocal(make_rooms(spec)), [])

    def test_find_non_reciprocal_flags_suspect_bug(self) -> None:
        """Test a one-way exit with no return at all is a suspect bug."""
        # Arrange
        rooms = make_rooms({"a": {"north": "b"}, "b": {}})

        # Act
        findings = find_non_reciprocal(rooms)

        # Assert
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].classification, CLASS_SUSPECT_BUG)

    def test_find_non_reciprocal_flags_wrong_direction(self) -> None:
        """Test a return exit in a non-opposite direction is classified."""
        # Arrange
        rooms = make_rooms({"a": {"north": "b"}, "b": {"east": "a"}})

        # Act
        findings = find_non_reciprocal(rooms)

        # Assert
        classifications = {f.classification for f in findings}
        self.assertIn(CLASS_WRONG_DIRECTION, classifications)

    def test_find_non_reciprocal_classifies_puzzle_gated(self) -> None:
        """Test a one-way whose return is added by an interaction is gated."""
        # Arrange
        rooms = make_rooms({"tavern": {}, "cellar": {"up": "tavern"}})
        latent = [LatentExit("tavern", "down", "cellar", "rug1", "move")]

        # Act
        findings = find_non_reciprocal(rooms, latent)

        # Assert
        gated = [f for f in findings if f.classification == CLASS_PUZZLE_GATED]
        self.assertEqual(len(gated), 1)
        self.assertEqual(gated[0].source_room_id, "cellar")
        self.assertIn("rug1", gated[0].evidence)

    def test_find_non_reciprocal_flags_one_way_puzzle_exit(self) -> None:
        """Test a latent exit into a room with no way back is flagged."""
        # Arrange
        rooms = make_rooms({"a": {}, "pit": {}})
        latent = [LatentExit("a", "down", "pit", "trapdoor1", "open")]

        # Act
        findings = find_non_reciprocal(rooms, latent)

        # Assert
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].classification, CLASS_ONE_WAY_PUZZLE)


class FindCollisionsTest(unittest.TestCase):
    """Test coordinate collision detection."""

    def test_find_collisions_reports_shared_coordinates(self) -> None:
        """Test two rooms at one coordinate are reported."""
        collisions = find_collisions({"a": (0, 0, 0), "b": (0, 0, 0)})
        self.assertEqual(collisions, {(0, 0, 0): ["a", "b"]})

    def test_find_collisions_ignores_approx_rooms(self) -> None:
        """Test approximately placed rooms don't create collisions."""
        collisions = find_collisions(
            {"a": (0, 0, 0), "b": (0, 0, 0)}, approx_placed={"b"}
        )
        self.assertEqual(collisions, {})


class FindDanglingTest(unittest.TestCase):
    """Test dangling exit detection."""

    def test_find_dangling_reports_missing_static_target(self) -> None:
        """Test a static exit to a nonexistent room is dangling."""
        rooms = make_rooms({"a": {"north": "ghost_room"}})
        self.assertEqual(find_dangling(rooms), [("a", "north", "ghost_room")])

    def test_find_dangling_reports_missing_latent_target(self) -> None:
        """Test a latent exit to a nonexistent room is dangling."""
        rooms = make_rooms({"a": {}})
        latent = [LatentExit("a", "down", "void", "item1", "open")]
        self.assertEqual(find_dangling(rooms, latent), [("a", "down", "void")])


class FindComponentsTest(unittest.TestCase):
    """Test connected component analysis."""

    def test_find_components_partitions_disconnected_graphs(self) -> None:
        """Test two islands form two components, largest first."""
        # Arrange
        spec: Dict[str, Dict[str, str]] = {"solo": {}}
        two_way(spec, "a", "east", "b")
        two_way(spec, "b", "east", "c")
        rooms = make_rooms(spec)

        # Act
        components = find_components(rooms)

        # Assert
        self.assertEqual(len(components), 2)
        self.assertEqual(components[0], {"a", "b", "c"})
        self.assertEqual(components[1], {"solo"})

    def test_find_components_connects_via_latent_edges(self) -> None:
        """Test latent exits count for connectivity."""
        # Arrange
        rooms = make_rooms({"a": {}, "b": {}})
        latent = [LatentExit("a", "down", "b", "item1", "open")]

        # Act
        components = find_components(rooms, latent)

        # Assert
        self.assertEqual(len(components), 1)


class FindNonstandardDirectionsTest(unittest.TestCase):
    """Test nonstandard direction detection."""

    def test_find_nonstandard_directions_flags_unknown_direction(self) -> None:
        """Test an exit direction outside vectors and portals is flagged."""
        rooms = make_rooms({"a": {"warp": "b"}, "b": {}})
        self.assertEqual(find_nonstandard_directions(rooms), [("a", "warp", "b")])

    def test_find_nonstandard_directions_allows_portals(self) -> None:
        """Test in/out exits are not flagged."""
        rooms = make_rooms({"a": {"in": "b"}, "b": {"out": "a"}})
        self.assertEqual(find_nonstandard_directions(rooms), [])


class ValidateWorldTest(unittest.TestCase):
    """Test the aggregated validate_world entry point."""

    def _clean_world(self) -> Dict[str, Room]:
        spec: Dict[str, Dict[str, str]] = {}
        two_way(spec, "square", "east", "tavern")
        two_way(spec, "square", "north", "church")
        return make_rooms(spec)

    def test_validate_world_clean_map_has_no_errors(self) -> None:
        """Test a fully reciprocal connected map reports no errors."""
        report = validate_world(self._clean_world(), spawn="square")
        self.assertFalse(report.has_errors)
        self.assertEqual(report.non_reciprocal, [])

    def test_validate_world_broken_map_has_errors(self) -> None:
        """Test a map with a one-way exit reports errors."""
        # Arrange
        rooms = self._clean_world()
        rooms["tavern"].exits["south"] = "square"  # wrong-direction extra return

        # Act
        report = validate_world(rooms, spawn="square")

        # Assert
        self.assertTrue(report.has_errors)
        self.assertTrue(report.suspect_non_reciprocal)

    def test_validate_world_include_latent_false_reclassifies(self) -> None:
        """Test disabling latent collection turns gated one-ways into bugs."""
        # Arrange
        rooms = make_rooms({"tavern": {}, "cellar": {"up": "tavern"}})
        rug = StatefulItem(
            "rug", "rug1", "A rug.", takeable=False, state="flat", room_id="tavern"
        )
        rug.add_state_description("moved", "Moved.")
        rug.add_interaction("move", target_state="moved", add_exit=("down", "cellar"))
        rooms["tavern"].add_item(rug)

        # Act
        with_latent = validate_world(rooms, spawn="tavern", include_latent=True)
        without_latent = validate_world(rooms, spawn="tavern", include_latent=False)

        # Assert
        self.assertFalse(with_latent.has_errors)
        self.assertTrue(without_latent.has_errors)


if __name__ == "__main__":
    unittest.main()
