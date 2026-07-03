# backend/managers/world/shared_conditions.py
"""
Shared condition functions for puzzles, gates and quest-item checks.

Interaction/speech-trigger conditions use the (player, game_state) signature;
quest-item done-checks use (game_state) only — build those with item_state_is.
"""

from typing import Any, Callable

# ============================================================================
# PLAYER CONDITIONS
# ============================================================================


def player_is_novice_or_below(player: Any, game_state: Any) -> bool:
    """Check if player is at Novice level or below (< 400 points)."""
    return getattr(player, "points", 0) < 400


def has_dawnfather_blessing(player: Any, game_state: Any) -> bool:
    """Check if player carries the Dawnfather's blessing (persisted flag)."""
    return bool(player.flags.get("dawnfather_blessing"))


def bears_watchfire_mark(player: Any, game_state: Any) -> bool:
    """Check if player bears Sir Aldric's Watchfire mark (persisted flag)."""
    return bool(player.flags.get("watchfire_mark"))


# ============================================================================
# ROOM/ITEM STATE CONDITIONS
# ============================================================================


def item_state_is(room_id: str, item_id: str, state: str) -> Callable[[Any], bool]:
    """
    Build a (game_state) -> bool check that an item in a room is in a state.

    Used for quest-item done-checks and anywhere world state gates behavior.
    Wrap with a lambda for (player, game_state) interaction conditions.
    """

    def check(game_state: Any) -> bool:
        room = game_state.get_room(room_id)
        if not room:
            return False
        for item in room.items:
            if getattr(item, "id", None) == item_id:
                return bool(getattr(item, "state", None) == state)
        return False

    return check


def stones_aligned(player: Any, game_state: Any) -> bool:
    """Check if all three standing stones are correctly aligned."""
    room = game_state.get_room("clearing")
    if not room:
        return False

    east_state = None
    west_state = None
    north_state = None

    for item in room.items:
        if hasattr(item, "id"):
            if item.id == "eastern_stone":
                east_state = getattr(item, "state", None)
            elif item.id == "western_stone":
                west_state = getattr(item, "state", None)
            elif item.id == "northern_stone":
                north_state = getattr(item, "state", None)

    return east_state == "sunrise" and west_state == "sunset" and north_state == "noon"
