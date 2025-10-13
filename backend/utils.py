# backend/utils.py
from typing import Any, Dict, Optional, Tuple
from models.StatefulItem import StatefulItem


async def send_message(sio: Any, sid: str, message: str) -> None:
    await sio.emit("message", message, room=sid)


async def send_stats_update(sio: Any, sid: str, player: Any) -> None:
    if not player:
        return

    # Defensive: some call sites may pass non-player objects (e.g., mobs).
    required_attrs = ("points", "stamina", "max_stamina")
    if any(not hasattr(player, attr) for attr in required_attrs):
        return
    stats_data: Dict[str, Any] = {
        "name": player.name,
        "score": player.points,
        "stamina": player.stamina,
        "max_stamina": player.max_stamina,
    }
    await sio.emit("statsUpdate", stats_data, room=sid)


# utils/door_utils.py


def create_linked_doors(
    room1_id: str,
    room2_id: str,
    door1_id: str,
    door2_id: str,
    door_name: str,
    dir1to2: str,
    dir2to1: str,
    initial_state: str = "closed",
    game_state: Optional[Any] = None,
    rooms: Optional[Dict[str, Any]] = None,
) -> Tuple[StatefulItem, StatefulItem]:
    """
    Create a pair of linked doors between two rooms with explicit directions.

    Args:
        room1_id (str): ID of the first room
        room2_id (str): ID of the second room
        door1_id (str): ID for the door in the first room
        door2_id (str): ID for the door in the second room
        door_name (str): Name for both doors
        dir1to2 (str): Direction from room1 to room2 (e.g., "north", "in")
        dir2to1 (str): Direction from room2 to room1 (e.g., "south", "out")
        initial_state (str): Initial state of the doors ("open" or "closed")
        game_state (GameState): Game state for adding to rooms
        rooms (dict): Dictionary of rooms if game_state is not provided

    Returns:
        tuple: The two door objects created
    """
    # Create door for room 1
    door1: StatefulItem = StatefulItem(
        name=door_name,
        id=door1_id,
        description=f"A {door_name} stands {initial_state}.",
        weight=100,
        value=0,
        takeable=False,
        state=initial_state,
    )
    door1.add_state_description("closed", f"A {door_name} stands closed.")
    door1.add_state_description("open", f"A {door_name} stands open.")
    door1.set_room_id(room1_id)

    # Create door for room 2
    door2: StatefulItem = StatefulItem(
        name=door_name,
        id=door2_id,
        description=f"A {door_name} stands {initial_state}.",
        weight=100,
        value=0,
        takeable=False,
        state=initial_state,
    )
    door2.add_state_description("closed", f"A {door_name} stands closed.")
    door2.add_state_description("open", f"A {door_name} stands open.")
    door2.set_room_id(room2_id)

    # Link the doors together
    door1.link_item(door2_id)
    door2.link_item(door1_id)

    # Register door interactions
    door1.add_interaction(
        verb="open",
        target_state="open",
        message=f"You open the {door_name}.",
        add_exit=(dir1to2, room2_id),
        from_state="closed",
    )
    door1.add_interaction(
        verb="close",
        target_state="closed",
        message=f"You close the {door_name}.",
        remove_exit=dir1to2,
        from_state="open",
    )

    door2.add_interaction(
        verb="open",
        target_state="open",
        message=f"You open the {door_name}.",
        add_exit=(dir2to1, room1_id),
        from_state="closed",
    )
    door2.add_interaction(
        verb="close",
        target_state="closed",
        message=f"You close the {door_name}.",
        remove_exit=dir2to1,
        from_state="open",
    )

    # Add doors to rooms
    if game_state:
        room1: Optional[Any] = game_state.get_room(room1_id)
        room2: Optional[Any] = game_state.get_room(room2_id)
        if room1:
            room1.add_item(door1)
        if room2:
            room2.add_item(door2)
    elif rooms:
        if room1_id in rooms:
            rooms[room1_id].add_item(door1)
        if room2_id in rooms:
            rooms[room2_id].add_item(door2)

    # Add exits if doors are open
    if initial_state == "open":
        if game_state:
            room1 = game_state.get_room(room1_id)
            room2 = game_state.get_room(room2_id)
            if room1:
                room1.exits[dir1to2] = room2_id
            if room2:
                room2.exits[dir2to1] = room1_id
        elif rooms:
            if room1_id in rooms:
                rooms[room1_id].exits[dir1to2] = room2_id
            if room2_id in rooms:
                rooms[room2_id].exits[dir2to1] = room1_id

    return door1, door2
