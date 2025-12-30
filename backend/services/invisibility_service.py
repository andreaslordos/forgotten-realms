# backend/services/invisibility_service.py

"""
Service for managing player invisibility.

Invisibility can be granted by:
1. Archmage command (session-based, resets on logout)
2. Items with grants_invisibility property (time-limited)

Invisibility is broken by:
- Attacking a player (PvP)
- Attacking a mob
- Casting offensive spells (summon, force, cripple, dumb, blind)
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def is_invisible(player: Any, online_sessions: Dict[str, Dict[str, Any]]) -> bool:
    """
    Check if a player is invisible via session flag OR active invisibility item.

    Args:
        player: The player object to check
        online_sessions: The global online sessions dict

    Returns:
        True if player is invisible
    """
    # Find player's session and check session-based invisibility (archmage)
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            if session.get("invisible", False):
                return True
            break

    # Check inventory for active invisibility-granting items
    current_time = time.time()
    inventory = getattr(player, "inventory", [])

    # Handle cases where inventory might not be iterable (e.g., Mock objects in tests)
    try:
        inventory_list = list(inventory)
    except TypeError:
        inventory_list = []

    for item in inventory_list:
        if getattr(item, "grants_invisibility", False):
            # Check if item is still active (not expired)
            if not getattr(item, "invisibility_expired", False):
                activated_at = getattr(item, "invisibility_activated_at", None)
                duration = getattr(item, "invisibility_duration_seconds", 0)

                # If never activated, activate now
                if activated_at is None:
                    item.invisibility_activated_at = current_time
                    logger.debug(
                        f"Auto-activated invisibility item {item.name} for {player.name}"
                    )
                    return True

                # Check if still within duration
                if current_time < activated_at + duration:
                    return True
                else:
                    # Item has expired, mark it
                    item.invisibility_expired = True
                    logger.debug(f"Invisibility item {item.name} expired for holder")

    return False


def break_invisibility(
    player: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    reason: str = "action",
) -> bool:
    """
    Remove invisibility from a player (clear session flag).

    Note: This only removes session-based invisibility (archmage command).
    Item-based invisibility continues until the item expires.

    Args:
        player: The player object
        online_sessions: The global online sessions dict
        reason: Description of why invisibility was broken (for logging)

    Returns:
        True if invisibility was removed, False if player wasn't invisible via session
    """
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            if session.get("invisible", False):
                session["invisible"] = False
                logger.info(f"Broke invisibility for {player.name} due to {reason}")
                return True
            break
    return False


def get_invisibility_item(player: Any) -> Optional[Any]:
    """
    Get an active (non-expired) invisibility item from player's inventory.

    Args:
        player: The player object

    Returns:
        The invisibility item if found and active, None otherwise
    """
    current_time = time.time()
    inventory = getattr(player, "inventory", [])

    # Handle cases where inventory might not be iterable (e.g., Mock objects in tests)
    try:
        inventory_list = list(inventory)
    except TypeError:
        inventory_list = []

    for item in inventory_list:
        if getattr(item, "grants_invisibility", False):
            if not getattr(item, "invisibility_expired", False):
                activated_at = getattr(item, "invisibility_activated_at", None)
                duration = getattr(item, "invisibility_duration_seconds", 0)

                if activated_at is None:
                    return item

                if current_time < activated_at + duration:
                    return item

    return None


def find_player_sid(
    player: Any, online_sessions: Dict[str, Dict[str, Any]]
) -> Optional[str]:
    """
    Find the session ID for a given player.

    Args:
        player: The player object to find
        online_sessions: The global online sessions dict

    Returns:
        The session ID (sid) or None if not found
    """
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            return sid
    return None


def set_invisible(
    player: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    invisible: bool = True,
) -> bool:
    """
    Set the invisibility state for a player's session.

    Args:
        player: The player object
        online_sessions: The global online sessions dict
        invisible: Whether to make the player invisible (True) or visible (False)

    Returns:
        True if the session was found and updated
    """
    sid = find_player_sid(player, online_sessions)
    if sid:
        online_sessions[sid]["invisible"] = invisible
        logger.debug(f"Set invisibility to {invisible} for {player.name}")
        return True
    return False


async def process_invisibility_expiry(
    sio: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    utils: Any,
) -> None:
    """
    Process invisibility item expiration for all players.
    Called by tick service each tick to notify players when items expire.

    Args:
        sio: Socket.IO server instance
        online_sessions: The global online sessions dict
        utils: Utilities module with send_message
    """
    current_time = time.time()

    for sid, session in online_sessions.items():
        player = session.get("player")
        if not player:
            continue

        # Check all invisibility items in player's inventory
        inventory = getattr(player, "inventory", [])

        # Handle cases where inventory might not be iterable (e.g., Mock objects in tests)
        try:
            inventory_list = list(inventory)
        except TypeError:
            inventory_list = []

        for item in inventory_list:
            if not getattr(item, "grants_invisibility", False):
                continue

            # Skip already expired items
            if getattr(item, "invisibility_expired", False):
                continue

            activated_at = getattr(item, "invisibility_activated_at", None)
            duration = getattr(item, "invisibility_duration_seconds", 0)

            # Skip items that haven't been activated yet
            if activated_at is None:
                continue

            # Check if item has just expired
            if current_time >= activated_at + duration:
                item.invisibility_expired = True
                logger.info(f"Invisibility item {item.name} expired for {player.name}")

                # Notify player
                await utils.send_message(
                    sio,
                    sid,
                    f"Your {item.name} fades and loses its power. You are now visible.",
                )
