# backend/services/zone_injector.py
"""
Inject a validated pocket-dimension zone into the live world: create the
rooms, spawn its mobs, and wire the golden door to the entry room (with the
way back out).
"""

import logging
from typing import Any, Dict

from services.zone_schema import spec_to_rooms

logger = logging.getLogger(__name__)


def _custom_mob_definition(custom: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": custom["name"],
        "description": custom["description"],
        "strength": int(custom.get("strength", 20)),
        "dexterity": int(custom.get("dexterity", 20)),
        "max_stamina": int(custom.get("max_stamina", 60)),
        "damage": int(custom.get("damage", 6)),
        "aggressive": bool(custom.get("aggressive", False)),
        "aggro_delay_min": 1,
        "aggro_delay_max": 3,
        "patrol_rooms": [],
        "movement_interval": 0,
        "loot_table": [],
        "instant_death": False,
        "point_value": int(custom.get("point_value", 25)),
        "pronouns": str(custom.get("pronouns", "it")),
    }


def inject_zone(
    spec: Dict[str, Any],
    prefix: str,
    game_state: Any,
    mob_manager: Any,
    door_room_id: str,
    door_direction: str = "in",
) -> str:
    """
    Materialize a validated zone spec into the world.

    Returns the (namespaced) entry room id. The door room gains
    `door_direction` -> entry, and the zone's exit room gains "out" -> door
    room, so there is always exactly one way back.
    """
    rooms = spec_to_rooms(spec, prefix)
    for room in rooms.values():
        game_state.add_room(room)

    entry_id = f"{prefix}{spec['entry_room_id']}"
    exit_id = f"{prefix}{spec['exit_room_id']}"

    door_room = game_state.get_room(door_room_id)
    if door_room is not None:
        door_room.exits[door_direction] = entry_id
    rooms[exit_id].exits["out"] = door_room_id

    if mob_manager is not None:
        for index, mob_spec in enumerate(spec.get("mobs") or []):
            room_id = f"{prefix}{mob_spec['room_id']}"
            template_id = mob_spec.get("template_id")
            if not template_id:
                template_id = f"{prefix}mob_{index}"
                mob_manager.add_mob_definition(
                    template_id, _custom_mob_definition(mob_spec["custom"])
                )
            mob_manager.spawn_mob(template_id, room_id, game_state)

    logger.info(
        "Injected pocket dimension '%s' (%d rooms) behind %s",
        spec.get("zone_name", prefix),
        len(rooms),
        door_room_id,
    )
    return entry_id
