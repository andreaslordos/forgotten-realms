# backend/commands/archmage.py

from typing import Any, Callable, Dict, Iterator, Optional, Tuple
from commands.registry import command_registry
from managers.world.shared_items import (
    create_bone,
    create_coin,
    create_holy_bones,
    create_knight_medallion,
    create_lantern,
    create_mist_token,
    create_rusty_dagger,
    create_shadow_key,
    create_short_sword,
    create_silver_dagger,
    create_torch,
    create_wine,
    create_wooden_club,
)
import logging
import sys
import os
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_set_points(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle setting points for another player. Archmage-only command.
    Usage: set <player_name> <points>

    Args:
        cmd (dict): The parsed command
        player (Player): The player executing the command
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module

    Returns:
        str: Confirmation message
    """
    # Check if the player is an Archmage
    if player.level != "Archmage":
        return "You do not have the authority to use this command."

    # Get the subject and instrument from the parsed command
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")

    # If we have a bound player object, use it
    target_player = None
    if subject_obj and hasattr(subject_obj, "name"):
        target_player = subject_obj
    else:
        # Parse command string to extract player name and points
        command_parts = cmd.get("original", "").split()

        # Remove the "set" verb
        if command_parts and command_parts[0].lower() == "set":
            command_parts = command_parts[1:]

        # Need at least two parts: player_name and points
        if len(command_parts) < 2:
            return "Set points for whom? (Usage: set <player_name> <points>)"

        # Last part should be the points, everything before is the player name
        points_str = command_parts[-1]
        player_name = " ".join(command_parts[:-1])

        if not player_name or not points_str:
            return "Specify both player name and points. (Usage: set <player_name> <points>)"

        # Find player in online sessions or player manager
        target_sid = None

        # First check online players
        for sid, session_data in online_sessions.items():
            other_player = session_data.get("player")
            if other_player and other_player.name.lower() == player_name.lower():
                target_player = other_player
                target_sid = sid
                break

        # If not found online, try player_manager
        if not target_player:
            target_player = player_manager.login(player_name)

    if not target_player:
        return f"Player '{subject}' not found."

    # Parse points from command_parts (it should be the last part)
    try:
        command_parts = cmd.get("original", "").split()
        points_str = command_parts[-1]
        points = int(points_str)
        if points < 0:
            return "Points cannot be negative."
    except ValueError:
        return f"Points must be a number, got '{points_str}'."

    # Store original level
    original_level = target_player.level

    # Set points directly and recalculate level
    target_player.points = points
    target_player.level_up()  # Directly call level_up after setting points

    # Save the updated player
    player_manager.save_players()

    # Find target player's session
    target_sid = None
    for sid, session in online_sessions.items():
        if session.get("player") == target_player:
            target_sid = sid
            break

    # If player is online, update their stats
    if target_sid and sio and utils:
        await utils.send_stats_update(sio, target_sid, target_player)
        await utils.send_message(
            sio,
            target_sid,
            f"A powerful mage has set your points to {points}.\nYour level of experience is now {target_player.level}.",
        )

    # Confirmation message for the Archmage
    if original_level != target_player.level:
        return f"Points for {target_player.name} set to {points}. Level changed from {original_level} to {target_player.level}."
    else:
        return f"Points for {target_player.name} set to {points}. Level remains {target_player.level}."


async def handle_reset(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle world reset. Archmage-only command.
    """
    # Check if the player is an Archmage
    if player.level != "Archmage":
        return "You do not have the authority to use this command."

    # Confirm intent
    subject = cmd.get("subject")
    if subject and subject.lower() == "confirm":
        # Notify all players
        if online_sessions and sio and utils:
            for sid, session_data in online_sessions.items():
                other_player = session_data.get("player")
                if other_player:
                    await utils.send_message(
                        sio,
                        sid,
                        "----------------------------\nWORLD RESET INITIATED\n----------------------------\n"
                        "Your vision begins to blur as powerful forces tamper with time...\n"
                        "Slowly, you sense everything returning to how it once was...\n"
                        "You will be disconnected and can reconnect in a moment.",
                    )

        # Log the reset
        logger.info(f"Mid-week reset initiated by Archmage {player.name}")

        # Give a brief delay for messages to be sent
        await asyncio.sleep(2)

        # Perform some basic cleanup
        for sid in list(online_sessions.keys()):
            try:
                await sio.disconnect(sid)
            except Exception as e:
                logger.error(f"Error disconnecting client {sid}: {e}")

        # Option 1: Restart the program (Python process)
        # This is the most reliable way to reset everything
        logger.info("Restarting the server process...")
        python = sys.executable
        os.execl(python, python, *sys.argv)  # nosec B606

        # We'll never reach this point due to the process restart
        return "Resetting the world..."
    else:
        return "This will reset the entire world and disconnect all players.\nType 'reset confirm' to proceed."


async def handle_invisible(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle making the player invisible. Archmage-only command.
    Usage: invis or invisible
    """
    # Check if the player is an Archmage
    if player.level != "Archmage":
        return "You do not have the authority to use this command."

    # Find player's session
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found."

    # Check if already invisible
    if online_sessions[current_sid].get("invisible", False):
        return "You are already invisible."

    # Set invisible flag
    online_sessions[current_sid]["invisible"] = True

    return "You fade from view. You are now invisible."


async def handle_visible(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle making the player visible again. Archmage-only command.
    Usage: vis or visible
    """
    # Check if the player is an Archmage
    if player.level != "Archmage":
        return "You do not have the authority to use this command."

    # Find player's session
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found."

    # Check if already visible
    if not online_sessions[current_sid].get("invisible", False):
        return "You are already visible."

    # Clear invisible flag
    online_sessions[current_sid]["invisible"] = False

    return "You shimmer back into view. You are now visible."


async def handle_godmode(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Secret cheat code that grants 100,000 points.
    Usage: godmodeplz
    """
    # Find player's session for stats update
    player_sid = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            player_sid = sid
            break

    # Grant the points
    player.add_points(100000, player_manager)
    player_manager.save_players()

    # Send stats update
    if player_sid and utils:
        await utils.send_stats_update(sio, player_sid, player)

    return "A divine force surges through you. You feel immensely powerful!"


# Zero-argument factories for items that may not be placed anywhere in
# the live world (e.g. wine) but should still be conjurable.
_ITEM_FACTORIES: Tuple[Callable[[], Any], ...] = (
    create_torch,
    create_lantern,
    create_coin,
    create_bone,
    create_holy_bones,
    create_wine,
    create_mist_token,
    create_knight_medallion,
    create_shadow_key,
    create_rusty_dagger,
    create_wooden_club,
    create_short_sword,
    create_silver_dagger,
)


def _iter_candidate_items(game_state: Any, utils: Any) -> Iterator[Any]:
    """Yield every item in the live world, then factory templates.

    Covers room items, container contents, hidden items, mob loot
    tables and mob shop stock.
    """
    rooms = getattr(game_state, "rooms", None) or {}
    for room in rooms.values():
        for item in list(getattr(room, "items", None) or []):
            yield item
            for inner in list(getattr(item, "items", None) or []):
                yield inner
        hidden = getattr(room, "hidden_items", None) or {}
        for hidden_item, _condition in hidden.values():
            yield hidden_item
            for inner in list(getattr(hidden_item, "items", None) or []):
                yield inner

    mob_manager = getattr(utils, "mob_manager", None)
    if mob_manager is not None:
        mobs = getattr(mob_manager, "mobs", None) or {}
        for mob in mobs.values():
            entries = list(getattr(mob, "loot_table", None) or [])
            entries += list(getattr(mob, "shop_stock", None) or [])
            for entry in entries:
                item = entry.get("item")
                if item is not None:
                    yield item

    for factory in _ITEM_FACTORIES:
        yield factory()


def _find_item_template(name: str, game_state: Any, utils: Any) -> Optional[Any]:
    """Find a takeable item matching name.

    An exact name/id match wins immediately; otherwise the first
    synonym/substring match is used.
    """
    lowered = name.lower()
    partial: Optional[Any] = None
    for item in _iter_candidate_items(game_state, utils):
        if not getattr(item, "takeable", False):
            continue
        item_id = str(getattr(item, "id", "") or "")
        if item.name.lower() == lowered or item_id.lower() == lowered:
            return item
        if partial is None and item.matches_name(lowered):
            partial = item
    return partial


async def handle_conjure(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Conjure a fresh copy of any item defined in the world. Archmage-only.
    Usage: conjure <item name>
    """
    if player.level != "Archmage":
        return "You do not have the authority to use this command."

    parts = cmd.get("original", "").split()
    if parts and parts[0].lower() == "conjure":
        parts = parts[1:]
    item_name = " ".join(parts).strip() or (cmd.get("subject") or "")
    if not item_name:
        return "Conjure what? (Usage: conjure <item name>)"

    template = _find_item_template(item_name, game_state, utils)
    if template is None:
        return f"Nothing in this world matches '{item_name}'."

    # Clone so the live world never hands out a shared instance.
    conjured = type(template).from_dict(template.to_dict())
    success, message = player.add_item(conjured)
    if not success:
        return str(message)

    player_manager.save_players()
    logger.info(f"Archmage {player.name} conjured '{conjured.name}'")
    return f"The mists coalesce in your hands - you conjure the {conjured.name}."


# Register Archmage commands
command_registry.register(
    "set", handle_set_points, "Set points for a player (Archmage only)."
)
command_registry.register(
    "reset",
    handle_reset,
    "Reset the world to its start-of-week condition (Archmage only).",
)
command_registry.register(
    "invisible", handle_invisible, "Become invisible (Archmage only)."
)
command_registry.register_alias("invis", "invisible")
command_registry.register(
    "visible", handle_visible, "Become visible again (Archmage only)."
)
command_registry.register_alias("vis", "visible")
command_registry.register(
    "conjure", handle_conjure, "Conjure any item into your hands (Archmage only)."
)

# Secret cheat code - not listed in help
command_registry.register("godmodeplz", handle_godmode, hidden=True)
