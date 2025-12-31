# backend/managers/world/__init__.py
"""
World generation package.

This package contains modular level generators for the game world.
Each level is implemented in its own module (level_1_village.py, level_2_woods.py, etc.)
and inherits from LevelGenerator base class.

The main entry point is generate_world() which orchestrates all level generators.
"""

from typing import Dict, Optional, Any, List
from models.Room import Room
from .level_base import LevelGenerator

# Import level generators as they are implemented
from .level_1_village import Level1Village
from .level_2_woods import Level2Woods

# from .level_3_bonegrinder import Level3Bonegrinder
# from .level_4_argynvost_vallaki import Level4ArgynvostVallaki
# from .level_5_castle_exterior import Level5CastleExterior
# from .level_6_strahd_domain import Level6StrahdDomain

# List of all level generators in order
# NOTE: Keep this empty until ALL levels are implemented to use legacy generator
# Once all levels are done, add them here and remove the fallback
LEVEL_GENERATORS: List[LevelGenerator] = [
    Level1Village(),
    Level2Woods(),
    # Level3Bonegrinder(),
    # Level4ArgynvostVallaki(),
    # Level5CastleExterior(),
    # Level6StrahdDomain(),
]


def generate_world(mob_manager: Optional[Any] = None) -> Dict[str, Room]:
    """
    Generate the complete game world with all levels.

    This function orchestrates the level generators to build the world in phases:
    1. Generate all rooms from each level
    2. Connect internal exits within each level
    3. Configure cross-level transitions
    4. Add items to all rooms
    5. Spawn mobs if mob_manager is provided

    Args:
        mob_manager: Optional MobManager instance for spawning mobs.

    Returns:
        Dict mapping room_id to Room objects for the entire world.
    """
    all_rooms: Dict[str, Room] = {}

    # If no level generators are configured yet, fall back to legacy generator
    if not LEVEL_GENERATORS:
        # Temporary: use the legacy generator until levels are implemented
        from managers.village_generator import generate_valley_of_barovia

        return generate_valley_of_barovia(mob_manager)

    # Phase 1: Generate all rooms from each level
    for level in LEVEL_GENERATORS:
        level_rooms = level.generate_rooms()
        all_rooms.update(level_rooms)

    # Phase 2: Connect internal exits within each level
    for level in LEVEL_GENERATORS:
        level.connect_internal_exits()

    # Phase 3: Configure cross-level transitions
    configure_level_transitions(all_rooms)

    # Phase 4: Add items to all rooms
    for level in LEVEL_GENERATORS:
        level.add_items()

    # Phase 5: Compute swamp paths for outdoor rooms
    compute_swamp_paths(all_rooms)

    # Phase 6: Spawn mobs if mob_manager is provided
    if mob_manager:
        for level in LEVEL_GENERATORS:
            level.spawn_mobs(mob_manager)
            level.configure_npc_interactions(mob_manager)

    return all_rooms


def configure_level_transitions(all_rooms: Dict[str, Room]) -> None:
    """
    Configure the transitions between levels.

    This sets up the barriers, puzzles, and hidden exits that
    control access between different level zones.

    Args:
        all_rooms: Dict of all rooms in the game world.
    """
    # Level transitions will be configured here
    # Each transition defines:
    # - The source room and direction
    # - The target room
    # - Any conditional requirements (items, puzzles, etc.)
    # - Whether the exit is hidden initially

    # Level 1 -> Level 2: Mist barrier at road south
    # The road south from the village leads to the crossroads,
    # but requires the mist token or priest's blessing
    pass  # Transitions will be added as levels are implemented


def compute_swamp_paths(rooms: Dict[str, Room]) -> None:
    """
    Precompute paths to the swamp/lake for outdoor rooms.

    Uses BFS to find the nearest direction toward the lake
    from each outdoor room.

    Args:
        rooms: Dict of all rooms in the game world.
    """
    from collections import deque

    # Find the lake room
    lake_room_id = "lake"
    if lake_room_id not in rooms:
        return

    # BFS from the lake to all outdoor rooms
    visited = {lake_room_id}
    queue: deque[tuple[str, Optional[str]]] = deque([(lake_room_id, None)])

    # Direction opposites for reversing paths
    opposites = {
        "north": "south",
        "south": "north",
        "east": "west",
        "west": "east",
        "northeast": "southwest",
        "northwest": "southeast",
        "southeast": "northwest",
        "southwest": "northeast",
        "up": "down",
        "down": "up",
        "in": "out",
        "out": "in",
    }

    while queue:
        current_id, direction_to_lake = queue.popleft()
        current = rooms.get(current_id)
        if not current:
            continue

        # Set the swamp direction for this room (direction toward lake)
        # Only set if direction leads to another outdoor room (for continuous swamp nav)
        if direction_to_lake and getattr(current, "is_outdoor", False):
            # Verify the direction leads to an outdoor room
            next_room_id = current.exits.get(direction_to_lake)
            next_room = rooms.get(next_room_id) if next_room_id else None
            if next_room and getattr(next_room, "is_outdoor", False):
                current.swamp_direction = direction_to_lake

        # Explore neighbors - only follow outdoor-to-outdoor paths
        # (skip "in"/"out" as they are shortcuts, not navigable paths)
        for direction, neighbor_id in current.exits.items():
            if direction in ("in", "out"):
                continue
            if neighbor_id not in visited:
                neighbor = rooms.get(neighbor_id)
                # Only explore outdoor neighbors for swamp path computation
                if neighbor and getattr(neighbor, "is_outdoor", False):
                    visited.add(neighbor_id)
                    direction_toward_lake = opposites.get(direction, direction)
                    queue.append((neighbor_id, direction_toward_lake))


# Export public interface
__all__ = [
    "generate_world",
    "LevelGenerator",
    "LEVEL_GENERATORS",
]
