# backend/services/affliction_service.py

"""
Service for managing player afflictions (DEAF, BLIND, DUMB, CRIPPLE, MAGIC_SLEEP).

Afflictions are stored in online_sessions[sid]["afflictions"] as a dict mapping
affliction type to its data (applied_at, expires_at, caster).
"""

import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Set

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables initialized as None (set via set_context)
SESSIONS: Optional[Dict[str, Dict[str, Any]]] = None
send_msg: Optional[Callable[[str, str], Awaitable[None]]] = None


def set_context(
    online_sessions: Dict[str, Dict[str, Any]],
    send_message: Callable[[str, str], Awaitable[None]],
) -> None:
    """
    Sets global variables for affliction service.

    Args:
        online_sessions: The global online sessions dict
        send_message: Async function to send messages to players
    """
    global SESSIONS, send_msg
    logger.debug("Setting affliction service context")
    SESSIONS = online_sessions
    send_msg = send_message
    logger.info("Affliction service context set successfully")


def apply_affliction(
    session: Dict[str, Any],
    affliction_type: str,
    duration_seconds: int,
    caster_name: str,
) -> bool:
    """
    Apply an affliction to a player's session.

    Args:
        session: The player's session dict
        affliction_type: Type of affliction (deaf, blind, dumb, cripple, magic_sleep)
        duration_seconds: How long the affliction lasts
        caster_name: Name of the caster

    Returns:
        True if affliction was applied successfully
    """
    if "afflictions" not in session:
        session["afflictions"] = {}

    current_time = time.time()
    session["afflictions"][affliction_type] = {
        "applied_at": current_time,
        "expires_at": current_time + duration_seconds,
        "caster": caster_name,
    }
    logger.debug(
        f"Applied {affliction_type} affliction for {duration_seconds}s by {caster_name}"
    )
    return True


def has_affliction(session: Dict[str, Any], affliction_type: str) -> bool:
    """
    Check if player has a specific affliction that hasn't expired.

    Args:
        session: The player's session dict
        affliction_type: Type of affliction to check

    Returns:
        True if player has the active affliction
    """
    afflictions = session.get("afflictions", {})
    if affliction_type not in afflictions:
        return False

    affliction = afflictions[affliction_type]
    expires_at: float = affliction["expires_at"]
    return time.time() < expires_at


def get_active_afflictions(session: Dict[str, Any]) -> Set[str]:
    """
    Get all active affliction types for a player.

    Args:
        session: The player's session dict

    Returns:
        Set of active affliction type names
    """
    active: Set[str] = set()
    current_time = time.time()
    for aff_type, aff_data in session.get("afflictions", {}).items():
        if current_time < aff_data["expires_at"]:
            active.add(aff_type)
    return active


def remove_affliction(session: Dict[str, Any], affliction_type: str) -> bool:
    """
    Remove a specific affliction from a player.

    Args:
        session: The player's session dict
        affliction_type: Type of affliction to remove

    Returns:
        True if affliction was removed, False if it didn't exist
    """
    if "afflictions" in session and affliction_type in session["afflictions"]:
        del session["afflictions"][affliction_type]
        logger.debug(f"Removed {affliction_type} affliction")
        return True
    return False


def cure_all_afflictions(session: Dict[str, Any]) -> int:
    """
    Remove all afflictions from a player.

    Args:
        session: The player's session dict

    Returns:
        Number of afflictions removed
    """
    count = len(session.get("afflictions", {}))
    session["afflictions"] = {}

    # Also clear magic sleep flag if present
    if session.get("magic_sleep"):
        session["magic_sleep"] = False

    logger.debug(f"Cured {count} afflictions")
    return count


def get_affliction_time_remaining(
    session: Dict[str, Any], affliction_type: str
) -> float:
    """
    Get remaining time in seconds for an affliction.

    Args:
        session: The player's session dict
        affliction_type: Type of affliction to check

    Returns:
        Remaining seconds, or 0 if affliction not active
    """
    afflictions = session.get("afflictions", {})
    if affliction_type not in afflictions:
        return 0.0

    expires_at: float = afflictions[affliction_type]["expires_at"]
    remaining: float = expires_at - time.time()
    return max(0.0, remaining)


async def process_affliction_expiry(
    sio: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    utils: Any,
) -> None:
    """
    Process affliction expiration for all players.
    Called by tick service each tick.

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

        afflictions = session.get("afflictions", {})
        if not afflictions:
            continue

        expired = []

        for aff_type, aff_data in afflictions.items():
            if current_time >= aff_data["expires_at"]:
                expired.append(aff_type)

        for aff_type in expired:
            del session["afflictions"][aff_type]

            # Clear magic sleep session flag if that's what expired
            if aff_type == "magic_sleep" and session.get("sleeping"):
                session["sleeping"] = False

            # Notify player
            affliction_messages = {
                "deaf": "Your hearing returns to normal.",
                "blind": "Your vision clears.",
                "dumb": "You find your voice again.",
                "cripple": "You can move freely again.",
                "magic_sleep": "You wake from your magical slumber.",
            }
            message = affliction_messages.get(
                aff_type, f"The {aff_type} spell wears off."
            )
            await utils.send_message(sio, sid, message)
            logger.debug(f"Affliction {aff_type} expired for {player.name}")


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


def find_player_by_name(
    name: str, online_sessions: Dict[str, Dict[str, Any]]
) -> tuple[Optional[Any], Optional[str]]:
    """
    Find a player and their session ID by name.

    Args:
        name: The player name to search for (case-insensitive)
        online_sessions: The global online sessions dict

    Returns:
        Tuple of (player, sid) or (None, None) if not found
    """
    name_lower = name.lower()
    for sid, session in online_sessions.items():
        player = session.get("player")
        if player and player.name.lower() == name_lower:
            return player, sid
    return None, None
