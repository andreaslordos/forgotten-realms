"""Pathfinding commands for quick navigation.

Commands:
- swamp (alias: zw): Move one room toward the swamp (outdoor rooms only)
"""

from typing import Any, Dict

from commands.registry import command_registry
from commands.executor import handle_movement
from commands.combat import is_in_combat
from services.affliction_service import find_player_sid, has_affliction


async def handle_swamp(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """Move one room toward the swamp (outdoor rooms only).

    Uses the precomputed swamp_direction on the current room to move
    the player one step closer to Lake Zarovich.

    Args:
        cmd: The parsed command dictionary
        player: The player executing the command
        game_state: The current game state
        player_manager: The player manager
        online_sessions: Dictionary of online sessions
        sio: Socket.IO server instance
        utils: Utility functions

    Returns:
        str: Result message or room description after movement
    """
    # Check combat blocking
    if is_in_combat(player.name):
        return "You can't move while in combat! Use 'flee <direction>' to escape."

    # Check affliction blocking
    player_sid = find_player_sid(player, online_sessions)
    if player_sid and has_affliction(online_sessions.get(player_sid, {}), "cripple"):
        return "You are crippled and cannot move!"

    current_room = game_state.get_room(player.current_room)
    if not current_room:
        return "You are lost in the void."

    if not getattr(current_room, "is_outdoor", False):
        return "You can only use this command outdoors."

    if player.current_room == "lake":
        return "You're already here, stupid!"

    swamp_dir = getattr(current_room, "swamp_direction", None)
    if not swamp_dir:
        return "You can't find a way to the swamp from here."

    # Delegate to handle_movement for the actual move
    return await handle_movement(
        {"verb": swamp_dir},
        player,
        game_state,
        player_manager,
        online_sessions,
        sio,
        utils,
    )


# Register commands
command_registry.register(
    "swamp", handle_swamp, "Move one room toward the swamp (outdoor rooms only)."
)
command_registry.register_aliases(["zw"], "swamp")
