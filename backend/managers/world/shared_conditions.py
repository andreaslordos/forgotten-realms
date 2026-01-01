# backend/managers/world/shared_conditions.py
"""
Shared condition functions for puzzles and stateful items.

These functions are used by StatefulItem.add_interaction(conditional_fn=...)
to check if an interaction should succeed based on game state.
"""

from typing import Any, Dict, Optional


# ============================================================================
# PLAYER INVENTORY CONDITIONS
# ============================================================================


def has_sunsword(player: Any, game_state: Any) -> bool:
    """Check if player has the sunsword in their inventory."""
    return any(
        hasattr(item, "id") and item.id == "sunsword" for item in player.inventory
    )


def has_any_weapon(player: Any, game_state: Any) -> bool:
    """Check if player has any weapon in their inventory."""
    from models.Weapon import Weapon

    return any(isinstance(item, Weapon) for item in player.inventory)


def player_has_light(player: Any, game_state: Any) -> bool:
    """Check if player has a light source in their inventory."""
    for item in player.inventory:
        if getattr(item, "emits_light", False):
            return True
    return False


def has_item_by_id(item_id: str) -> Any:
    """
    Create a condition function that checks if player has an item by ID.

    Args:
        item_id: The ID of the item to check for.

    Returns:
        A condition function that checks for the item.
    """

    def check(player: Any, game_state: Any) -> bool:
        return any(
            hasattr(item, "id") and item.id == item_id for item in player.inventory
        )

    return check


# ============================================================================
# PLAYER LEVEL CONDITIONS
# ============================================================================


def player_is_novice_or_below(player: Any, game_state: Any) -> bool:
    """Check if player is at Novice level or below (< 400 points)."""
    return getattr(player, "points", 0) < 400


def player_level_at_most(max_points: int) -> Any:
    """
    Create a condition function that checks if player has at most N points.

    Args:
        max_points: Maximum points threshold (exclusive).

    Returns:
        A condition function that checks the player's points.
    """

    def check(player: Any, game_state: Any) -> bool:
        return getattr(player, "points", 0) < max_points

    return check


# ============================================================================
# ROOM/ITEM STATE CONDITIONS
# ============================================================================


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


def beacon_has_skull(player: Any, game_state: Any) -> bool:
    """Check if the dragon skull has been placed on the beacon."""
    room = game_state.get_room("hall")
    if not room:
        return False
    for item in room.items:
        if hasattr(item, "id") and item.id == "dragon_beacon":
            return getattr(item, "state", None) == "skull_placed"
    return False


def treasury_unlocked(player: Any, game_state: Any) -> bool:
    """Check if the treasury pedestal dials are correctly set."""
    room = game_state.get_room("treasury")
    if not room:
        return False

    dial_states: Dict[str, Optional[str]] = {}
    for item in room.items:
        if hasattr(item, "id") and item.id in ("dial1", "dial2", "dial3"):
            dial_states[item.id] = getattr(item, "state", None)

    # Correct sequence: sun, star, moon (hinted in tome)
    return (
        dial_states.get("dial1") == "sun"
        and dial_states.get("dial2") == "star"
        and dial_states.get("dial3") == "moon"
    )


def knight_honored(player: Any, game_state: Any) -> bool:
    """Check if player has shown respect to the knights (knelt before inscription)."""
    room = game_state.get_room("quarters")
    if not room:
        return False
    for item in room.items:
        if hasattr(item, "id") and item.id == "knight_inscription":
            return getattr(item, "state", None) == "honored"
    return False


def altar_restored(player: Any, game_state: Any) -> bool:
    """Check if the Argynvostholt altar has been restored."""
    room = game_state.get_room("argchapel")
    if not room:
        return False
    for item in room.items:
        if hasattr(item, "id") and item.id == "arg_altar":
            return getattr(item, "state", None) == "restored"
    return False


def altar_restored_and_skull_placed(player: Any, game_state: Any) -> bool:
    """Check if altar is restored AND skull is placed on beacon."""
    return altar_restored(player, game_state) and beacon_has_skull(player, game_state)


# ============================================================================
# MAZE PUZZLE CONDITIONS
# ============================================================================


def player_visited_vallaki_church(player: Any, game_state: Any) -> bool:
    """Check if player has visited St. Andral's Church in Vallaki."""
    return "vallakichurch" in getattr(player, "visited", set())


def mirrors_aligned(player: Any, game_state: Any) -> bool:
    """Check if the mirrors in the Hall of Mirrors are correctly touched in sequence."""
    room = game_state.get_room("maze_mirror")
    if not room:
        return False
    # Check the mirror sequence stored on the room
    sequence = getattr(room, "mirror_sequence", [])
    return sequence == ["east", "south", "west", "north"]


# ============================================================================
# LEVEL TRANSITION CONDITIONS
# ============================================================================


def has_mist_token(player: Any, game_state: Any) -> bool:
    """Check if player has the mist token to pass through the mist barrier."""
    return any(
        hasattr(item, "id") and item.id == "mist_token" for item in player.inventory
    )


def has_priest_blessing(player: Any, game_state: Any) -> bool:
    """Check if player has been blessed by the priest."""
    return getattr(player, "has_blessing", False)


def can_pass_mist_barrier(player: Any, game_state: Any) -> bool:
    """Check if player can pass the mist barrier (token OR blessing)."""
    return has_mist_token(player, game_state) or has_priest_blessing(player, game_state)


def has_knight_medallion(player: Any, game_state: Any) -> bool:
    """Check if player has the ghostly knight's medallion."""
    return any(
        hasattr(item, "id") and item.id == "knight_medallion"
        for item in player.inventory
    )


def has_shadow_key(player: Any, game_state: Any) -> bool:
    """Check if player has the shadow key from the hag."""
    return any(
        hasattr(item, "id") and item.id == "shadow_key" for item in player.inventory
    )


def beacon_lit(player: Any, game_state: Any) -> bool:
    """Check if the dragon beacon has been lit."""
    room = game_state.get_room("hall")
    if not room:
        return False
    for item in room.items:
        if hasattr(item, "id") and item.id == "dragon_beacon":
            return getattr(item, "state", None) == "lit"
    return False


def has_all_three_artifacts(player: Any, game_state: Any) -> bool:
    """Check if player has all three artifacts needed for Strahd's domain."""
    has_sunsword_item = any(
        hasattr(item, "id") and item.id == "sunsword" for item in player.inventory
    )
    has_tome = any(
        hasattr(item, "id") and item.id == "tome_of_strahd" for item in player.inventory
    )
    has_icon = any(
        hasattr(item, "id") and item.id == "icon_of_ravenloft"
        for item in player.inventory
    )
    return has_sunsword_item and has_tome and has_icon
