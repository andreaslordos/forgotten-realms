# backend/tools/map_validation.py
"""
World-graph validation: coordinate assignment, reciprocity and consistency
checks. Pure logic, no I/O — reused by the map CLI and (later) by generated
zone validation. This module only REPORTS problems; it never mutates rooms.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

Coord = Tuple[int, int, int]
Edge = Tuple[str, str, str]  # (source_room_id, direction, target_room_id)

DIRECTION_VECTORS: Dict[str, Coord] = {
    "north": (0, 1, 0),
    "south": (0, -1, 0),
    "east": (1, 0, 0),
    "west": (-1, 0, 0),
    "northeast": (1, 1, 0),
    "northwest": (-1, 1, 0),
    "southeast": (1, -1, 0),
    "southwest": (-1, -1, 0),
    "up": (0, 0, 1),
    "down": (0, 0, -1),
}

OPPOSITE_DIRECTIONS: Dict[str, str] = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
    "up": "down",
    "down": "up",
    "in": "out",
    "out": "in",
}

# Portal directions connect rooms without implying spatial adjacency.
PORTAL_DIRECTIONS = frozenset({"in", "out"})

CLASS_PUZZLE_GATED = "puzzle_gated"
CLASS_WRONG_DIRECTION = "wrong_direction"
CLASS_SUSPECT_BUG = "suspect_bug"
CLASS_ONE_WAY_PUZZLE = "one_way_puzzle"

# Classifications that count as hard errors (vs. intentional/informational).
ERROR_CLASSIFICATIONS = frozenset({CLASS_WRONG_DIRECTION, CLASS_SUSPECT_BUG})


@dataclass(frozen=True)
class LatentExit:
    """An exit that does not exist yet but can be added by an interaction."""

    source_room_id: str
    direction: str
    target_room_id: str
    item_id: str
    verb: str


@dataclass(frozen=True)
class Contradiction:
    """An exit whose direction disagrees with the rooms' assigned coordinates."""

    source_room_id: str
    direction: str
    target_room_id: str
    expected: Coord
    actual: Coord


@dataclass(frozen=True)
class NonReciprocalExit:
    """An exit with no matching return exit, classified by likely intent."""

    source_room_id: str
    direction: str
    target_room_id: str
    classification: str
    evidence: str


@dataclass
class MapReport:
    """Aggregated validation results for a world graph."""

    spawn: str
    coords: Dict[str, Coord] = field(default_factory=dict)
    approx_placed: Set[str] = field(default_factory=set)
    unplaced: List[str] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    non_reciprocal: List[NonReciprocalExit] = field(default_factory=list)
    collisions: Dict[Coord, List[str]] = field(default_factory=dict)
    dangling: List[Edge] = field(default_factory=list)
    components: List[Set[str]] = field(default_factory=list)
    nonstandard_directions: List[Edge] = field(default_factory=list)
    latent_exits: List[LatentExit] = field(default_factory=list)

    @property
    def suspect_non_reciprocal(self) -> List[NonReciprocalExit]:
        return [
            f for f in self.non_reciprocal if f.classification in ERROR_CLASSIFICATIONS
        ]

    @property
    def has_errors(self) -> bool:
        return bool(
            self.suspect_non_reciprocal
            or self.dangling
            or self.collisions
            or self.contradictions
        )


def _iter_room_items(room: Any) -> Iterator[Any]:
    for item in getattr(room, "items", []):
        yield item
    for item, _condition in getattr(room, "hidden_items", {}).values():
        yield item


def static_edges(rooms: Dict[str, Any]) -> List[Edge]:
    """All exits currently present on rooms, as (source, direction, target)."""
    edges: List[Edge] = []
    for room_id, room in rooms.items():
        for direction, target in room.exits.items():
            edges.append((room_id, direction.lower(), target))
    return edges


def collect_latent_exits(rooms: Dict[str, Any]) -> List[LatentExit]:
    """
    Find exits that interactions can add later (`add_exit` / `reciprocal_exit`
    on StatefulItem interactions). These make one-way static exits legitimate.
    """
    seen: Set[Tuple[str, str, str]] = set()
    latent: List[LatentExit] = []

    def add(source: str, direction: str, target: str, owner: str, verb: str) -> None:
        key = (source, direction, target)
        if key not in seen:
            seen.add(key)
            latent.append(LatentExit(source, direction, target, owner, verb))

    for room_id, room in rooms.items():
        for triggers in getattr(room, "speech_triggers", {}).values():
            trigger_list = triggers if isinstance(triggers, list) else [triggers]
            for trigger in trigger_list:
                if not isinstance(trigger, dict):
                    continue
                if "add_exit" in trigger:
                    direction, target = trigger["add_exit"]
                    add(room_id, direction, target, "speech trigger", "speak")
                if "reciprocal_exit" in trigger:
                    source, direction, target = trigger["reciprocal_exit"]
                    add(source, direction, target, "speech trigger", "speak")
        for item in _iter_room_items(room):
            interactions = getattr(item, "interactions", None)
            if not isinstance(interactions, dict):
                continue
            item_id = str(getattr(item, "id", "?"))
            item_room = getattr(item, "room_id", None) or room_id
            for verb, entries in interactions.items():
                entry_list = entries if isinstance(entries, list) else [entries]
                for entry in entry_list:
                    if not isinstance(entry, dict):
                        continue
                    if "add_exit" in entry:
                        direction, target = entry["add_exit"]
                        add(item_room, direction, target, item_id, verb)
                    if "reciprocal_exit" in entry:
                        source, direction, target = entry["reciprocal_exit"]
                        add(source, direction, target, item_id, verb)
    return latent


def _add_coords(a: Coord, b: Coord) -> Coord:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _sub_coords(a: Coord, b: Coord) -> Coord:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _nearest_free(origin: Coord, occupied: Set[Coord]) -> Coord:
    """First unoccupied coordinate in an expanding ring around origin (same z)."""
    ox, oy, oz = origin
    for radius in range(1, 100):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                candidate = (ox + dx, oy + dy, oz)
                if candidate not in occupied:
                    return candidate
    return (ox, oy, oz + 1000)  # pragma: no cover - defensive


@dataclass
class CoordinateResult:
    coords: Dict[str, Coord]
    approx_placed: Set[str]
    contradictions: List[Contradiction]
    unplaced: List[str]


def assign_coordinates(
    rooms: Dict[str, Any],
    start: str,
    extra_edges: Sequence[LatentExit] = (),
) -> CoordinateResult:
    """
    BFS-place every room on an integer grid starting from `start` at (0,0,0).

    Vector directions constrain placement (target = source + direction vector);
    first placement wins and later disagreeing edges are reported as
    contradictions. Portal edges (in/out) and nonstandard directions imply no
    geometry: their targets are placed at the nearest free coordinate and
    marked approximate. Fully disconnected rooms are placed in offset clusters
    so they still render, and are also marked approximate.
    """
    edges: List[Edge] = static_edges(rooms)
    edges.extend((e.source_room_id, e.direction, e.target_room_id) for e in extra_edges)
    edges = [(a, d, b) for (a, d, b) in edges if a in rooms and b in rooms]

    vector_from: Dict[str, List[Tuple[str, str]]] = {}
    vector_to: Dict[str, List[Tuple[str, str]]] = {}
    portal_edges: List[Edge] = []
    for a, direction, b in edges:
        if direction in DIRECTION_VECTORS:
            vector_from.setdefault(a, []).append((direction, b))
            vector_to.setdefault(b, []).append((direction, a))
        else:
            portal_edges.append((a, direction, b))

    coords: Dict[str, Coord] = {}
    approx: Set[str] = set()
    contradictions: List[Contradiction] = []
    seen_contradictions: Set[Edge] = set()

    def record_contradiction(
        a: str, direction: str, b: str, expected: Coord, actual: Coord
    ) -> None:
        key = (a, direction, b)
        if key in seen_contradictions:
            return
        seen_contradictions.add(key)
        # A misplaced two-way pair would otherwise report once per direction.
        opposite = OPPOSITE_DIRECTIONS.get(direction)
        if opposite is not None:
            seen_contradictions.add((b, opposite, a))
        contradictions.append(Contradiction(a, direction, b, expected, actual))

    def bfs(seed: str) -> List[str]:
        """Propagate placement from seed; returns rooms newly placed."""
        placed: List[str] = []
        queue: deque[str] = deque([seed])
        while queue:
            current = queue.popleft()
            here = coords[current]
            for direction, target in vector_from.get(current, []):
                expected = _add_coords(here, DIRECTION_VECTORS[direction])
                if target in coords:
                    if coords[target] != expected:
                        record_contradiction(
                            current, direction, target, expected, coords[target]
                        )
                else:
                    coords[target] = expected
                    placed.append(target)
                    queue.append(target)
            for direction, source in vector_to.get(current, []):
                expected = _sub_coords(here, DIRECTION_VECTORS[direction])
                if source in coords:
                    if coords[source] != expected:
                        record_contradiction(
                            source, direction, current, here, coords[source]
                        )
                else:
                    coords[source] = expected
                    placed.append(source)
                    queue.append(source)
        return placed

    if start in rooms:
        coords[start] = (0, 0, 0)
        bfs(start)

    # Attach portal-connected rooms near their counterpart, then keep BFS-ing.
    # Everything placed from an approximate seed has an arbitrary absolute
    # position (relative geometry within the cluster is still validated).
    progress = True
    while progress:
        progress = False
        for a, _direction, b in portal_edges:
            if a in coords and b not in coords:
                placed_room, new_room = a, b
            elif b in coords and a not in coords:
                placed_room, new_room = b, a
            else:
                continue
            coords[new_room] = _nearest_free(coords[placed_room], set(coords.values()))
            approx.add(new_room)
            approx.update(bfs(new_room))
            progress = True

    # Place remaining disconnected clusters at offset columns so they render.
    unplaced_snapshot = [room_id for room_id in rooms if room_id not in coords]
    offset_x = max((c[0] for c in coords.values()), default=0) + 4
    for room_id in unplaced_snapshot:
        if room_id in coords:
            continue
        coords[room_id] = (offset_x, 0, 0)
        approx.add(room_id)
        approx.update(bfs(room_id))
        offset_x = max(c[0] for c in coords.values()) + 4

    return CoordinateResult(coords, approx, contradictions, unplaced_snapshot)


def find_dangling(
    rooms: Dict[str, Any], extra_edges: Sequence[LatentExit] = ()
) -> List[Edge]:
    """Exits (static or latent) whose target room does not exist."""
    dangling: List[Edge] = []
    for a, direction, b in static_edges(rooms):
        if b not in rooms:
            dangling.append((a, direction, b))
    for e in extra_edges:
        if e.target_room_id not in rooms:
            dangling.append((e.source_room_id, e.direction, e.target_room_id))
        if e.source_room_id not in rooms:
            dangling.append((e.source_room_id, e.direction, e.target_room_id))
    return dangling


def find_nonstandard_directions(rooms: Dict[str, Any]) -> List[Edge]:
    """Static exits using directions that are neither vectors nor portals."""
    return [
        (a, d, b)
        for (a, d, b) in static_edges(rooms)
        if d not in DIRECTION_VECTORS and d not in PORTAL_DIRECTIONS
    ]


def find_non_reciprocal(
    rooms: Dict[str, Any], latent: Sequence[LatentExit] = ()
) -> List[NonReciprocalExit]:
    """
    Classify every exit lacking a proper return exit.

    - puzzle_gated: an interaction can add the return exit later (intentional).
    - wrong_direction: a return exit exists but not in the opposite direction.
    - suspect_bug: no return exit exists at all.
    - one_way_puzzle: a LATENT exit whose target has no way back at all.
    """
    latent_by_pair: Dict[Tuple[str, str], List[LatentExit]] = {}
    for e in latent:
        latent_by_pair.setdefault((e.source_room_id, e.target_room_id), []).append(e)

    findings: List[NonReciprocalExit] = []

    for a, direction, b in static_edges(rooms):
        if b not in rooms:
            continue  # reported by find_dangling
        opposite = OPPOSITE_DIRECTIONS.get(direction)
        if opposite is None:
            continue  # reported by find_nonstandard_directions
        if rooms[b].exits.get(opposite) == a:
            continue
        gated = latent_by_pair.get((b, a))
        if gated:
            e = gated[0]
            findings.append(
                NonReciprocalExit(
                    a,
                    direction,
                    b,
                    CLASS_PUZZLE_GATED,
                    f"return exit added by '{e.verb}' on item '{e.item_id}'",
                )
            )
            continue
        wrong_dirs = [d for d, t in rooms[b].exits.items() if t == a]
        if wrong_dirs:
            findings.append(
                NonReciprocalExit(
                    a,
                    direction,
                    b,
                    CLASS_WRONG_DIRECTION,
                    f"{b} returns via '{wrong_dirs[0]}' instead of '{opposite}'",
                )
            )
            continue
        findings.append(
            NonReciprocalExit(
                a, direction, b, CLASS_SUSPECT_BUG, f"{b} has no exit back to {a}"
            )
        )

    for e in latent:
        a, direction, b = e.source_room_id, e.direction, e.target_room_id
        if b not in rooms or a not in rooms:
            continue
        opposite = OPPOSITE_DIRECTIONS.get(direction)
        has_static_return = any(t == a for t in rooms[b].exits.values())
        has_latent_return = (b, a) in latent_by_pair
        if not has_static_return and not has_latent_return:
            findings.append(
                NonReciprocalExit(
                    a,
                    direction,
                    b,
                    CLASS_ONE_WAY_PUZZLE,
                    f"puzzle exit ('{e.verb}' on '{e.item_id}') leads to a room "
                    f"with no way back{'' if opposite else ' (portal)'}",
                )
            )
    return findings


def find_collisions(
    coords: Dict[str, Coord], approx_placed: Optional[Set[str]] = None
) -> Dict[Coord, List[str]]:
    """
    Coordinates occupied by more than one precisely-placed room. Rooms placed
    approximately (portal targets, disconnected clusters) are excluded — their
    absolute positions are arbitrary, so overlap with them is not a content bug.
    """
    skip = approx_placed or set()
    by_coord: Dict[Coord, List[str]] = {}
    for room_id, coord in coords.items():
        if room_id in skip:
            continue
        by_coord.setdefault(coord, []).append(room_id)
    return {coord: sorted(ids) for coord, ids in by_coord.items() if len(ids) > 1}


def find_components(
    rooms: Dict[str, Any], extra_edges: Sequence[LatentExit] = ()
) -> List[Set[str]]:
    """Connected components over the undirected graph (static + latent edges)."""
    adjacency: Dict[str, Set[str]] = {room_id: set() for room_id in rooms}
    all_edges: List[Edge] = static_edges(rooms)
    all_edges.extend(
        (e.source_room_id, e.direction, e.target_room_id) for e in extra_edges
    )
    for a, _direction, b in all_edges:
        if a in adjacency and b in adjacency:
            adjacency[a].add(b)
            adjacency[b].add(a)

    components: List[Set[str]] = []
    visited: Set[str] = set()
    for room_id in rooms:
        if room_id in visited:
            continue
        component: Set[str] = set()
        queue: deque[str] = deque([room_id])
        visited.add(room_id)
        while queue:
            current = queue.popleft()
            component.add(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    components.sort(key=len, reverse=True)
    return components


def validate_world(
    rooms: Dict[str, Any],
    spawn: str = "square",
    include_latent: bool = True,
) -> MapReport:
    """Run every check and aggregate the results into a MapReport."""
    latent = collect_latent_exits(rooms) if include_latent else []
    placement = assign_coordinates(rooms, spawn, extra_edges=latent)
    report = MapReport(
        spawn=spawn,
        coords=placement.coords,
        approx_placed=placement.approx_placed,
        unplaced=placement.unplaced,
        contradictions=placement.contradictions,
        non_reciprocal=find_non_reciprocal(rooms, latent),
        collisions=find_collisions(placement.coords, placement.approx_placed),
        dangling=find_dangling(rooms, latent),
        components=find_components(rooms, latent),
        nonstandard_directions=find_nonstandard_directions(rooms),
        latent_exits=latent,
    )
    return report
