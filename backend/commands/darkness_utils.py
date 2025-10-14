"""
Utility functions for handling darkness and visibility in rooms.
"""

from typing import Any, Dict


def room_is_visible(
    room: Any, online_sessions: Dict[str, Dict[str, Any]], game_state: Any
) -> bool:
    """
    Check if a room is visible.

    Room is visible if:
    1. Room is not dark, OR
    2. Any item on the ground emits light, OR
    3. Any player in room has a light source in inventory

    Args:
        room: The room to check
        online_sessions: All online sessions
        game_state: Game state

    Returns:
        bool: True if room is visible
    """
    # Room is naturally lit
    if not hasattr(room, "is_dark") or not room.is_dark:
        return True

    # Check items on the ground for light sources
    visible_items = room.get_items(game_state)
    for item in visible_items:
        if hasattr(item, "emits_light") and item.emits_light:
            return True

    # Check if any player in this room has a light source
    for sid, session in online_sessions.items():
        other_player = session.get("player")
        if not other_player:
            continue

        if other_player.current_room == room.room_id:
            if (
                hasattr(other_player, "has_light_source")
                and other_player.has_light_source()
            ):
                return True

    # No light source found anywhere
    return False


def get_dark_room_description(room: Any) -> str:
    """
    Get the description shown for a dark room without light.
    Shows ONLY room name and darkness message.

    Args:
        room: The dark room

    Returns:
        str: Minimal room description
    """
    desc = "The room is too dark to see anything."
    return desc
