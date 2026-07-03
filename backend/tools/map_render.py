# backend/tools/map_render.py
"""ASCII rendering of a validated world map, for reading in a terminal."""

from typing import Any, Dict, List, Optional, Tuple

from tools.map_validation import (
    CLASS_ONE_WAY_PUZZLE,
    CLASS_PUZZLE_GATED,
    CLASS_SUSPECT_BUG,
    CLASS_WRONG_DIRECTION,
    DIRECTION_VECTORS,
    PORTAL_DIRECTIONS,
    Coord,
    MapReport,
)

CELL_INNER = 12  # characters inside [ ]
CELL_W = CELL_INNER + 2
GAP_W = 4
STRIDE = CELL_W + GAP_W

LEGEND = (
    "legend: [room] grid cell   -- <-> both-way   -> <- one-way   | ^ v n/s   "
    "/ \\ diagonal   cell marks: ^ up  v down  * portal  ~ approx position"
)


def _cell_label(room_id: str, room: Any, approx: bool) -> str:
    marks = ""
    exits = getattr(room, "exits", {})
    if "up" in exits:
        marks += "^"
    if "down" in exits:
        marks += "v"
    if any(d in PORTAL_DIRECTIONS for d in exits):
        marks += "*"
    if approx:
        marks += "~"
    base = room_id[: CELL_INNER - len(marks)]
    return f"{base}{marks}"


def _horizontal_connector(
    rooms: Dict[str, Any], left: Optional[str], right: Optional[str]
) -> str:
    if left is None or right is None:
        return " " * GAP_W
    east = rooms[left].exits.get("east") == right
    west = rooms[right].exits.get("west") == left
    if east and west:
        return "-" * GAP_W
    if east:
        return " -> "
    if west:
        return " <- "
    return " " * GAP_W


def _vertical_connector(
    rooms: Dict[str, Any], upper: Optional[str], lower: Optional[str]
) -> str:
    """Connector between a cell and the cell directly south of it."""
    if upper is None or lower is None:
        return " "
    north = rooms[lower].exits.get("north") == upper
    south = rooms[upper].exits.get("south") == lower
    if north and south:
        return "|"
    if north:
        return "^"
    if south:
        return "v"
    return " "


def _render_level(
    z: int,
    placed: Dict[str, Coord],
    rooms: Dict[str, Any],
    approx: set[str],
) -> List[str]:
    level_rooms = {rid: c for rid, c in placed.items() if c[2] == z and rid in rooms}
    if not level_rooms:
        return []
    xs = [c[0] for c in level_rooms.values()]
    ys = [c[1] for c in level_rooms.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    n_cols = max_x - min_x + 1
    n_rows = max_y - min_y + 1

    cell_at: Dict[Tuple[int, int], List[str]] = {}
    for level_rid, (x, y, _z) in sorted(level_rooms.items()):
        cell_at.setdefault((x - min_x, max_y - y), []).append(level_rid)

    def room_at(col: int, row: int) -> Optional[str]:
        stacked = cell_at.get((col, row))
        return stacked[0] if stacked else None

    line_width = n_cols * STRIDE - GAP_W
    lines: List[str] = [f"=== z={z} ({len(level_rooms)} rooms) ==="]
    for row in range(n_rows):
        cell_line = [" "] * line_width
        for col in range(n_cols):
            cell_rid = room_at(col, row)
            start = col * STRIDE
            if cell_rid is not None:
                label = _cell_label(cell_rid, rooms[cell_rid], cell_rid in approx)
                stacked = len(cell_at[(col, row)])
                if stacked > 1:
                    suffix = f"+{stacked - 1}"
                    label = label[: CELL_INNER - len(suffix)] + suffix
                text = f"[{label:^{CELL_INNER}}]"
            else:
                text = " " * CELL_W
            cell_line[start : start + CELL_W] = list(text)
            if col + 1 < n_cols:
                gap = _horizontal_connector(rooms, cell_rid, room_at(col + 1, row))
                cell_line[start + CELL_W : start + STRIDE] = list(gap)
        lines.append("".join(cell_line).rstrip())

        if row + 1 < n_rows:
            conn_line = [" "] * line_width
            for col in range(n_cols):
                center = col * STRIDE + CELL_W // 2
                conn_line[center] = _vertical_connector(
                    rooms, room_at(col, row), room_at(col, row + 1)
                )
                # Diagonals meeting between this row and the next.
                upper_right = room_at(col + 1, row)
                lower_left = room_at(col, row + 1)
                upper_left = room_at(col, row)
                lower_right = room_at(col + 1, row + 1)
                boundary = col * STRIDE + CELL_W + 1
                if boundary < line_width:
                    if _diagonal_exists(rooms, lower_left, upper_right, "northeast"):
                        conn_line[boundary] = "/"
                    if _diagonal_exists(rooms, upper_left, lower_right, "southeast"):
                        conn_line[boundary] = (
                            "X" if conn_line[boundary] == "/" else "\\"
                        )
            lines.append("".join(conn_line).rstrip())

    stacked_notes = [
        f"  stacked at same coordinate: {', '.join(ids)}"
        for ids in cell_at.values()
        if len(ids) > 1
    ]
    lines.extend(stacked_notes)
    return _compress_blank_runs(lines)


def _compress_blank_runs(lines: List[str]) -> List[str]:
    """Collapse runs of 3+ empty grid lines into a single distance marker."""
    out: List[str] = []
    blanks = 0
    for line in lines:
        if line.strip() == "":
            blanks += 1
            continue
        if blanks:
            out.extend([""] * blanks if blanks < 3 else ["      ~ ~ ~"])
            blanks = 0
        out.append(line)
    return out


def _diagonal_exists(
    rooms: Dict[str, Any], a: Optional[str], b: Optional[str], direction: str
) -> bool:
    """True if a->b via `direction` or b->a via its opposite exists."""
    if a is None or b is None:
        return False
    from tools.map_validation import OPPOSITE_DIRECTIONS

    if rooms[a].exits.get(direction) == b:
        return True
    return bool(rooms[b].exits.get(OPPOSITE_DIRECTIONS[direction]) == a)


def _section(title: str, entries: List[str]) -> List[str]:
    if not entries:
        return []
    return [f"{title} ({len(entries)}):"] + [f"  {e}" for e in entries] + [""]


def render_ascii(
    report: MapReport,
    rooms: Dict[str, Any],
    only_z: Optional[int] = None,
) -> str:
    """Render the per-level grids followed by classified findings."""
    lines: List[str] = [LEGEND, ""]

    z_levels = sorted({c[2] for c in report.coords.values()}, reverse=True)
    if only_z is not None:
        z_levels = [z for z in z_levels if z == only_z]
    for z in z_levels:
        level = _render_level(z, report.coords, rooms, report.approx_placed)
        if level:
            lines.extend(level)
            lines.append("")

    portal_edges = [
        f"{a} --{d}--> {b}"
        for (a, d, b) in (
            (rid, d, t)
            for rid, room in sorted(rooms.items())
            for d, t in room.exits.items()
            if d in PORTAL_DIRECTIONS
        )
    ]
    lines.extend(_section("PORTAL EXITS (in/out, no geometry implied)", portal_edges))

    lines.extend(
        _section(
            "CONTRADICTIONS [ERROR] (exit direction disagrees with layout)",
            [
                f"{c.source_room_id} --{c.direction}--> {c.target_room_id}: "
                f"expected {c.expected}, placed at {c.actual}"
                for c in report.contradictions
            ],
        )
    )
    by_class: Dict[str, List[str]] = {}
    for f in report.non_reciprocal:
        by_class.setdefault(f.classification, []).append(
            f"{f.source_room_id} --{f.direction}--> {f.target_room_id}: {f.evidence}"
        )
    lines.extend(
        _section(
            "NON-RECIPROCAL [ERROR] (no way back)",
            by_class.get(CLASS_SUSPECT_BUG, []),
        )
    )
    lines.extend(
        _section(
            "WRONG-DIRECTION RETURN [ERROR]",
            by_class.get(CLASS_WRONG_DIRECTION, []),
        )
    )
    lines.extend(
        _section(
            "COLLISIONS [ERROR] (rooms sharing a coordinate)",
            [f"{coord}: {', '.join(ids)}" for coord, ids in report.collisions.items()],
        )
    )
    lines.extend(
        _section(
            "DANGLING EXITS [ERROR] (target room does not exist)",
            [f"{a} --{d}--> {b}" for (a, d, b) in report.dangling],
        )
    )
    lines.extend(
        _section(
            "ONE-WAY PUZZLE EXITS [WARNING] (no way back even after the puzzle)",
            by_class.get(CLASS_ONE_WAY_PUZZLE, []),
        )
    )
    lines.extend(
        _section(
            "NONSTANDARD DIRECTIONS [WARNING]",
            [f"{a} --{d}--> {b}" for (a, d, b) in report.nonstandard_directions],
        )
    )
    if len(report.components) > 1:
        others = [
            f"component of {len(comp)}: {', '.join(sorted(comp)[:8])}"
            + (" ..." if len(comp) > 8 else "")
            for comp in report.components[1:]
        ]
        lines.extend(
            _section(
                f"DISCONNECTED [WARNING] (unreachable from '{report.spawn}')", others
            )
        )
    lines.extend(
        _section(
            "PUZZLE-GATED ONE-WAYS [OK] (return exit appears via interaction)",
            by_class.get(CLASS_PUZZLE_GATED, []),
        )
    )

    error_count = (
        len(report.suspect_non_reciprocal)
        + len(report.contradictions)
        + len(report.collisions)
        + len(report.dangling)
    )
    warning_count = (
        len(by_class.get(CLASS_ONE_WAY_PUZZLE, []))
        + len(report.nonstandard_directions)
        + max(0, len(report.components) - 1)
    )
    if error_count:
        lines.append(f"SUMMARY: {error_count} ERROR(S), {warning_count} warning(s)")
    else:
        lines.append(
            f"SUMMARY: OK — 0 errors, {warning_count} warning(s), "
            f"{len(by_class.get(CLASS_PUZZLE_GATED, []))} puzzle-gated one-way(s)"
        )
    return "\n".join(lines)
