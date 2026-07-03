# backend/services/zone_schema.py
"""
Pocket-dimension zone specs: JSON schema (doubles as the Anthropic tool
input schema) and validation.

A zone is a small self-contained dimension behind a golden door: 4-10 rooms
with local coordinates, at most one internal puzzle owning the only permitted
one-way exit, a bounded mob population, and a capped treasure budget.
Geometry is verified with the same validators the world map tool uses.
"""

from typing import Any, Dict, List, Optional, Tuple

from models.Item import Item
from models.Room import Room
from models.StatefulItem import StatefulItem
from tools.map_validation import (
    DIRECTION_VECTORS,
    assign_coordinates,
    collect_latent_exits,
    find_components,
    find_dangling,
    find_non_reciprocal,
)

MIN_ROOMS = 4
MAX_ROOMS = 10
MAX_MOBS = 4
MAX_AGGRESSIVE_MOBS = 2
MAX_TOTAL_ITEM_VALUE = 150

# Mob templates the generator may reuse (hostile/ambient only — no quest NPCs)
ALLOWED_MOB_TEMPLATES = frozenset(
    {
        "bats",
        "gargoyle",
        "ghoul",
        "skeleton",
        "spawn",
        "specter",
        "wolf",
        "wraith",
        "zombie",
    }
)

CUSTOM_MOB_LIMITS: Dict[str, Tuple[int, int]] = {
    "strength": (5, 40),
    "dexterity": (5, 40),
    "max_stamina": (20, 150),
    "damage": (1, 12),
    "point_value": (10, 150),
}

_ID_PATTERN = r"^[a-z][a-z0-9_]*$"

# Puzzle verbs must route to the interaction handler (see
# commands/interaction.py common_interaction_verbs) — a generated verb
# outside this list would be untypeable.
ALLOWED_PUZZLE_VERBS = [
    "touch",
    "push",
    "pull",
    "turn",
    "move",
    "ring",
    "read",
    "pray",
    "light",
    "raise",
    "lower",
    "spin",
    "knock",
    "search",
]

ZONE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "zone_name": {"type": "string", "maxLength": 60},
        "theme": {"type": "string", "maxLength": 200},
        "rooms": {
            "type": "array",
            "minItems": MIN_ROOMS,
            "maxItems": MAX_ROOMS,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "pattern": _ID_PATTERN},
                    "name": {"type": "string", "maxLength": 60},
                    "description": {"type": "string", "maxLength": 600},
                    "coords": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "is_dark": {"type": "boolean"},
                    "exits": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["id", "name", "description", "coords", "exits"],
            },
        },
        "entry_room_id": {"type": "string"},
        "exit_room_id": {"type": "string"},
        "mobs": {
            "type": "array",
            "maxItems": MAX_MOBS,
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "template_id": {"type": "string"},
                    "custom": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "maxLength": 40},
                            "description": {"type": "string", "maxLength": 400},
                            "strength": {"type": "integer"},
                            "dexterity": {"type": "integer"},
                            "max_stamina": {"type": "integer"},
                            "damage": {"type": "integer"},
                            "point_value": {"type": "integer"},
                            "aggressive": {"type": "boolean"},
                            "pronouns": {"type": "string"},
                        },
                        "required": ["name", "description"],
                    },
                },
                "required": ["room_id"],
            },
        },
        "items": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "name": {"type": "string", "maxLength": 40},
                    "description": {"type": "string", "maxLength": 400},
                    "weight": {"type": "integer", "minimum": 0, "maximum": 20},
                    "value": {"type": "integer", "minimum": 0},
                    "takeable": {"type": "boolean"},
                    "synonyms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 4,
                    },
                },
                "required": ["room_id", "name", "description", "value"],
            },
        },
        "puzzle": {
            "type": "object",
            "properties": {
                "room_id": {"type": "string"},
                "item_name": {"type": "string", "maxLength": 40},
                "item_description": {"type": "string", "maxLength": 400},
                "trigger_verb": {"type": "string", "enum": ALLOWED_PUZZLE_VERBS},
                "success_message": {"type": "string", "maxLength": 600},
                "hint": {"type": "string", "maxLength": 400},
                "blocked_exit": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string"},
                        "direction": {"type": "string"},
                        "to": {"type": "string"},
                    },
                    "required": ["from", "direction", "to"],
                },
            },
            "required": [
                "room_id",
                "item_name",
                "item_description",
                "trigger_verb",
                "success_message",
                "hint",
                "blocked_exit",
            ],
        },
    },
    "required": ["zone_name", "theme", "rooms", "entry_room_id", "exit_room_id"],
}


def _local(room_id: str, prefix: str) -> str:
    return f"{prefix}{room_id}"


def spec_to_rooms(spec: Dict[str, Any], prefix: str) -> Dict[str, Room]:
    """
    Build namespaced Room objects (with items and the puzzle StatefulItem)
    from a zone spec. Used by validation (throwaway build) and injection.

    The puzzle's blocked exit is NOT wired statically — it is added by the
    puzzle item's interaction, which the map validators see as a latent exit.
    """
    puzzle = spec.get("puzzle") or {}
    blocked = puzzle.get("blocked_exit") or {}

    rooms: Dict[str, Room] = {}
    for room_spec in spec.get("rooms", []):
        room = Room(
            _local(room_spec["id"], prefix),
            room_spec["name"],
            room_spec["description"],
            exits={},
            is_dark=bool(room_spec.get("is_dark", False)),
            is_outdoor=False,  # pocket dimensions have no sky
        )
        rooms[room.room_id] = room

    for room_spec in spec.get("rooms", []):
        room = rooms[_local(room_spec["id"], prefix)]
        for direction, target in room_spec.get("exits", {}).items():
            if (
                room_spec["id"] == blocked.get("from")
                and direction == blocked.get("direction")
                and target == blocked.get("to")
            ):
                continue  # opened by the puzzle interaction
            room.exits[direction.lower()] = _local(target, prefix)

    for item_spec in spec.get("items", []):
        item_room = rooms.get(_local(item_spec["room_id"], prefix))
        if item_room is None:
            continue
        item_room.add_item(
            Item(
                name=item_spec["name"],
                id=f"{prefix}item_{len(item_room.items)}_{item_spec['room_id']}",
                description=item_spec["description"],
                weight=int(item_spec.get("weight", 1)),
                value=int(item_spec.get("value", 0)),
                takeable=bool(item_spec.get("takeable", True)),
                synonyms=item_spec.get("synonyms"),
            )
        )

    if puzzle:
        puzzle_room = rooms.get(_local(puzzle["room_id"], prefix))
        if puzzle_room is not None:
            puzzle_item = StatefulItem(
                name=puzzle["item_name"],
                id=f"{prefix}puzzle",
                description=puzzle["item_description"],
                takeable=False,
                state="dormant",
                room_id=puzzle_room.room_id,
            )
            puzzle_item.add_state_description("dormant", puzzle["item_description"])
            puzzle_item.add_state_description(
                "triggered", f"{puzzle['item_description']} It has been disturbed."
            )
            puzzle_item.add_interaction(
                verb=puzzle["trigger_verb"].lower(),
                from_state="dormant",
                target_state="triggered",
                message=puzzle["success_message"],
                add_exit=(
                    blocked["direction"].lower(),
                    _local(blocked["to"], prefix),
                ),
                points_awarded=50,
            )
            puzzle_item.add_interaction(
                verb="examine",
                message=puzzle["hint"],
            )
            puzzle_room.add_item(puzzle_item)

    return rooms


def _structural_errors(spec: Dict[str, Any]) -> List[str]:
    import re

    errors: List[str] = []
    rooms = spec.get("rooms")
    if not isinstance(rooms, list) or not (MIN_ROOMS <= len(rooms) <= MAX_ROOMS):
        errors.append(f"zone must have {MIN_ROOMS}-{MAX_ROOMS} rooms")
        return errors

    ids = [r.get("id") for r in rooms]
    for room_id in ids:
        if not isinstance(room_id, str) or not re.match(_ID_PATTERN, room_id):
            errors.append(f"invalid room id: {room_id!r}")
    if len(set(ids)) != len(ids):
        errors.append("duplicate room ids")

    id_set = set(ids)
    for r in rooms:
        coords = r.get("coords")
        if (
            not isinstance(coords, list)
            or len(coords) != 3
            or not all(isinstance(c, int) for c in coords)
        ):
            errors.append(f"room {r.get('id')}: coords must be [x, y, z]")
        for direction, target in (r.get("exits") or {}).items():
            if direction.lower() not in DIRECTION_VECTORS:
                errors.append(
                    f"room {r.get('id')}: nonstandard direction '{direction}'"
                )
            if target not in id_set:
                errors.append(f"room {r.get('id')}: exit to unknown room '{target}'")

    for key in ("entry_room_id", "exit_room_id"):
        if spec.get(key) not in id_set:
            errors.append(f"{key} is not a room in the zone")

    for mob in spec.get("mobs") or []:
        if mob.get("room_id") not in id_set:
            errors.append(f"mob placed in unknown room '{mob.get('room_id')}'")
    for item_spec in spec.get("items") or []:
        if item_spec.get("room_id") not in id_set:
            errors.append(f"item placed in unknown room '{item_spec.get('room_id')}'")

    puzzle = spec.get("puzzle")
    if puzzle:
        blocked = puzzle.get("blocked_exit") or {}
        if puzzle.get("room_id") not in id_set:
            errors.append("puzzle room_id is not a room in the zone")
        if str(puzzle.get("trigger_verb", "")).lower() not in ALLOWED_PUZZLE_VERBS:
            errors.append(
                f"puzzle trigger_verb '{puzzle.get('trigger_verb')}' is not a "
                "playable verb"
            )
        if blocked.get("from") not in id_set or blocked.get("to") not in id_set:
            errors.append("puzzle blocked_exit references unknown rooms")
        elif str(blocked.get("direction", "")).lower() not in DIRECTION_VECTORS:
            errors.append("puzzle blocked_exit direction is nonstandard")

    return errors


def _budget_errors(spec: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    mobs = spec.get("mobs") or []
    if len(mobs) > MAX_MOBS:
        errors.append(f"too many mobs (max {MAX_MOBS})")
    aggressive = 0
    for mob in mobs:
        template_id = mob.get("template_id")
        custom = mob.get("custom")
        if template_id and template_id not in ALLOWED_MOB_TEMPLATES:
            errors.append(f"mob template '{template_id}' not allowed")
        if not template_id and not custom:
            errors.append("mob needs template_id or custom")
        if custom:
            if custom.get("aggressive", False):
                aggressive += 1
            for field, (low, high) in CUSTOM_MOB_LIMITS.items():
                value = custom.get(field)
                if value is not None and not (low <= int(value) <= high):
                    errors.append(
                        f"custom mob {custom.get('name')}: {field} outside "
                        f"[{low}, {high}]"
                    )
        elif template_id in ("wolf", "zombie", "ghoul", "spawn", "wraith", "gargoyle"):
            aggressive += 1
    if aggressive > MAX_AGGRESSIVE_MOBS:
        errors.append(f"too many aggressive mobs (max {MAX_AGGRESSIVE_MOBS})")

    total_value = sum(int(i.get("value", 0)) for i in spec.get("items") or [])
    if total_value > MAX_TOTAL_ITEM_VALUE:
        errors.append(
            f"total item value {total_value} exceeds budget {MAX_TOTAL_ITEM_VALUE}"
        )
    return errors


def validate_zone_spec(
    spec: Dict[str, Any],
    prefix: str,
    existing_room_ids: Optional[Any] = None,
) -> List[str]:
    """
    Validate a zone spec. Returns a list of error strings ([] = valid).

    Runs structural and budget checks, then builds the namespaced rooms and
    verifies geometry with the world map validators: declared coordinates
    must agree with exit directions, every exit reciprocal (except the
    puzzle's latent one-way), one connected component, no collisions.
    """
    errors = _structural_errors(spec)
    if errors:
        return errors
    errors.extend(_budget_errors(spec))

    if existing_room_ids:
        for room_spec in spec["rooms"]:
            namespaced = _local(room_spec["id"], prefix)
            if namespaced in existing_room_ids:
                errors.append(f"room id collision with existing world: {namespaced}")
    if errors:
        return errors

    rooms = spec_to_rooms(spec, prefix)
    entry = _local(spec["entry_room_id"], prefix)
    latent = collect_latent_exits(rooms)

    declared = {_local(r["id"], prefix): tuple(r["coords"]) for r in spec["rooms"]}
    if len(set(declared.values())) != len(declared):
        errors.append("two rooms share the same coords")

    placement = assign_coordinates(rooms, entry, extra_edges=latent)
    for contradiction in placement.contradictions:
        errors.append(
            f"exit direction disagrees with layout: "
            f"{contradiction.source_room_id} --{contradiction.direction}--> "
            f"{contradiction.target_room_id}"
        )
    # BFS places entry at origin; declared coords must match up to the
    # entry room's own declared offset.
    entry_declared = declared.get(entry, (0, 0, 0))
    for room_id, coord in placement.coords.items():
        expected = tuple(c + e for c, e in zip(coord, entry_declared))
        if room_id in declared and declared[room_id] != expected:
            errors.append(
                f"declared coords for {room_id} disagree with exits: "
                f"declared {declared[room_id]}, derived {expected}"
            )

    for a, direction, b in find_dangling(rooms, latent):
        errors.append(f"dangling exit {a} --{direction}--> {b}")
    for finding in find_non_reciprocal(rooms, latent):
        if finding.classification != "puzzle_gated":
            errors.append(
                f"non-reciprocal exit {finding.source_room_id} "
                f"--{finding.direction}--> {finding.target_room_id}"
            )
    if len(find_components(rooms, latent)) != 1:
        errors.append("zone is not a single connected area")

    return errors
