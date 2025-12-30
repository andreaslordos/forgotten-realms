# backend/services/notifications.py

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from services.invisibility_service import is_invisible

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables initialized as None
SESSIONS: Optional[Dict[str, Dict[str, Any]]] = None
send_msg: Optional[Callable[[str, str], Awaitable[None]]] = None


def set_context(
    online_sessions: Dict[str, Dict[str, Any]],
    send_message: Callable[[str, str], Awaitable[None]],
) -> None:
    """
    Sets global variables for notifications. This is one way to inject
    dependencies from your server setup.
    """
    global SESSIONS, send_msg
    logger.debug("Setting notification context")
    SESSIONS = online_sessions
    send_msg = send_message
    logger.info("Notification context set successfully")


async def broadcast_room(
    room_id: str, message: str, exclude_player: List[str] = []
) -> None:
    """
    Notify all players in a room that a message has been broadcast.

    Args:
        room_id (str): The ID of the room to broadcast to
        message (str): The message to broadcast
        exclude_player (list): List of player names to exclude from broadcast
    """
    global SESSIONS, send_msg
    if not SESSIONS or not send_msg:
        logger.warning("Attempted to broadcast room but context not initialized")
        return

    for sid, session_data in SESSIONS.items():
        other_player: Any = session_data.get("player")
        if not other_player:
            continue  # Skip sessions that haven't authenticated.

        # Skip if player is excluded or is sleeping
        if other_player.name in exclude_player or session_data.get("sleeping", False):
            continue

        if other_player.current_room == room_id:
            await send_msg(sid, message)


async def broadcast_arrival(player: Any) -> None:
    """
    Notify all players in the player's current room that the player has arrived.
    Invisible players slip in silently (no broadcast).

    Args:
        player (Player): The player who arrived
    """
    global SESSIONS

    # Invisible players slip in silently
    if SESSIONS and is_invisible(player, SESSIONS):
        logger.debug(f"Skipping arrival broadcast for invisible player {player.name}")
        return

    room_id: str = player.current_room
    display_name: str = player.name
    display_level: str = player.level
    logger.debug(f"Broadcasting arrival of {display_name} to room {room_id}")
    await broadcast_room(
        room_id,
        f"{display_name} the {display_level} has just arrived.",
        exclude_player=[player.name],
    )


async def broadcast_departure(room_id: str, departing_player: Any) -> None:
    """
    Notify all players in the room that someone has left.
    Invisible players slip out silently (no broadcast).

    Args:
        room_id (str): The ID of the room to broadcast to
        departing_player (Player): The player who left
    """
    global SESSIONS

    # Invisible players slip out silently
    if SESSIONS and is_invisible(departing_player, SESSIONS):
        logger.debug(
            f"Skipping departure broadcast for invisible player {departing_player.name}"
        )
        return

    display_name: str = departing_player.name
    display_level: str = departing_player.level
    logger.debug(f"Broadcasting departure of {display_name} from room {room_id}")
    await broadcast_room(
        room_id,
        f"{display_name} the {display_level} has left.",
        exclude_player=[departing_player.name],
    )


async def broadcast_logout(player: Any) -> None:
    """
    Notify all players in a room that a player in that room has logged out.
    Invisible players vanish silently (no broadcast).

    Args:
        player (Player): The player who logged out
    """
    global SESSIONS

    # Invisible players vanish silently
    if SESSIONS and is_invisible(player, SESSIONS):
        logger.debug(f"Skipping logout broadcast for invisible player {player.name}")
        return

    room_id: str = player.current_room
    display_name: str = player.name
    logger.debug(f"Broadcasting logout of {display_name} from room {room_id}")
    await broadcast_room(
        room_id,
        f"{display_name} the {player.level} has just passed on.",
        exclude_player=[player.name],
    )


async def broadcast_item_drop(
    room_id: str,
    player_name: str,
    item_name: str,
    exclude_players: Optional[List[str]] = None,
) -> None:
    """
    Notify all players in a room that a player has dropped an item.

    Args:
        room_id (str): The ID of the room where item was dropped
        player_name (str): The name of the player who dropped the item
        item_name (str): The name of the item dropped
        exclude_players (list): List of player names to exclude from broadcast
    """
    if exclude_players is None:
        exclude_players = [player_name]
    elif player_name not in exclude_players:
        exclude_players = exclude_players + [player_name]

    logger.debug(
        f"Broadcasting item drop: {player_name} dropped {item_name} in {room_id}"
    )
    await broadcast_room(
        room_id,
        f"{player_name} has dropped {item_name}.",
        exclude_player=exclude_players,
    )


async def broadcast_all(
    message: str,
    exclude_players: Optional[List[str]] = None,
) -> None:
    """
    Broadcast a message to all online players in the game.

    Args:
        message (str): The message to broadcast
        exclude_players (list): List of player names to exclude from broadcast
    """
    global SESSIONS, send_msg
    if not SESSIONS or not send_msg:
        logger.warning("Attempted to broadcast_all but context not initialized")
        return

    if exclude_players is None:
        exclude_players = []

    for sid, session_data in SESSIONS.items():
        other_player: Any = session_data.get("player")
        if not other_player:
            continue  # Skip sessions that haven't authenticated.

        # Skip if player is excluded or is sleeping
        if other_player.name in exclude_players or session_data.get("sleeping", False):
            continue

        await send_msg(sid, message)
