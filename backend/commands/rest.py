# backend/commands/rest.py

from commands.registry import command_registry
from typing import Any, Dict, Optional

from services.affliction_service import has_affliction
from services.notifications import broadcast_room
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Number of ticks between each healing point while sleeping
SLEEP_HEALING_INTERVAL = 2  # Healing occurs every 2 ticks


async def handle_sleep(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle the sleep command.

    If a target is provided, cast the SLEEP spell on them.
    Otherwise, go to sleep for healing.
    """
    # If a target is specified, this is the SLEEP spell (magic)
    target = cmd.get("subject")
    if target:
        from commands.magic import handle_sleep_spell

        return await handle_sleep_spell(
            cmd,
            player,
            game_state,
            player_manager,
            online_sessions,
            sio,
            utils,
        )

    # No target - this is rest/healing sleep
    # Check if player is already sleeping
    for sid, session in online_sessions.items():
        if session.get("player") == player and session.get("sleeping"):
            return "You are already asleep."

    # Check if player is in combat
    from commands.combat import is_in_combat

    if is_in_combat(player.name):
        return "You can't sleep while in combat!"

    # Check if player is already at max health
    if player.stamina >= player.max_stamina:
        return (
            f"You are already at full stamina ({player.stamina}/{player.max_stamina})."
        )

    # Find the player's session ID
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found"

    # Mark the player as sleeping
    online_sessions[current_sid]["sleeping"] = True
    online_sessions[current_sid]["sleep_tick_counter"] = 0

    # Broadcast to room that player has fallen asleep
    await broadcast_room(
        player.current_room,
        f"{player.name} the {player.level} has fallen asleep.",
        exclude_player=[player.name],
    )

    # Send the specific sleep message to the player
    return "ZZZzzz..."


async def handle_wake(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle the wake command, waking up a sleeping player.
    """
    # Get subject (target player)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")

    # Find the player's session ID
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found"

    # If the player wants to wake someone else up
    target_player = None
    target_sid = None

    # If we have a bound player object, use it
    if (
        subject_obj
        and hasattr(subject_obj, "name")
        and hasattr(subject_obj, "current_room")
    ):
        if subject_obj.current_room == player.current_room and subject_obj != player:
            target_player = subject_obj
            # Find their session ID
            for sid, session in online_sessions.items():
                if session.get("player") == target_player:
                    target_sid = sid
                    break
    elif subject:
        # Find the target player by name in the same room
        for sid, session in online_sessions.items():
            other_player = session.get("player")
            if (
                other_player
                and other_player.current_room == player.current_room
                and other_player != player
                and subject.lower() in other_player.name.lower()
            ):
                target_player = other_player
                target_sid = sid
                break

    if target_player and target_sid:
        # Check if player is asleep (can't wake others if you're asleep)
        if online_sessions[current_sid].get("sleeping"):
            return "You can't wake others while you're asleep."

        # Check if the target player is sleeping
        if not online_sessions[target_sid].get("sleeping"):
            return f"{target_player.name} is already awake."

        # Wake up the target player
        await wake_player(
            target_player,
            target_sid,
            online_sessions,
            sio,
            utils,
            max_stamina_reached=False,
            woken_by=player,
        )

        return f"You wake {target_player.name} up."

    # If player is waking themselves up
    # Check if player is actually sleeping
    if not online_sessions[current_sid].get("sleeping"):
        return "You're not asleep."

    # Call the common wake-up function (can be called from here or from tick processing)
    await wake_player(
        player, current_sid, online_sessions, sio, utils, max_stamina_reached=False
    )

    return "You wake up."


async def wake_player(
    player: Any,
    sid: str,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
    max_stamina_reached: bool = False,
    woken_by: Optional[Any] = None,
    combat: bool = False,
) -> None:
    """
    Common function to wake a player up, either manually or automatically.

    Args:
        player: The player to wake up
        sid: The player's session ID
        online_sessions: Dictionary of online sessions
        sio: Socket.IO instance
        utils: Utilities module
        max_stamina_reached: Whether the player woke up due to max stamina
        woken_by: The player who woke this player up
        combat: Whether the player was awakened by combat
    """
    session = online_sessions[sid]

    # Wake up the player
    session["sleeping"] = False
    if "sleep_tick_counter" in session:
        del session["sleep_tick_counter"]
    if "healing_message_count" in session:
        del session["healing_message_count"]

    # Broadcast to room that player has woken up, with different messages based on cause
    if woken_by:
        # Woken up by another player
        await broadcast_room(
            player.current_room,
            f"{player.name} the {player.level} has been woken up by {woken_by.name}.",
            exclude_player=[player.name, woken_by.name],
        )
        # Notify the player who was woken up
        await utils.send_message(sio, sid, f"You are awakened by {woken_by.name}!")
    else:
        # Normal wake up
        await broadcast_room(
            player.current_room,
            f"{player.name} the {player.level} has woken up.",
            exclude_player=[player.name],
        )

    # If waking up due to max stamina, send the specific message
    if max_stamina_reached:
        await utils.send_message(
            sio,
            sid,
            f"You are too alert to sleep any more! You wake up.\nYour stamina is now {player.stamina}.",
        )


async def process_sleeping_players(
    sio: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    player_manager: Any,
    utils: Any,
) -> None:
    """
    Process all sleeping players to heal them at regular intervals.
    This should be called by the tick service.
    """
    for sid, session in list(online_sessions.items()):
        player = session.get("player")
        if not player or not session.get("sleeping"):
            continue

        # Skip healing/wake logic for magic sleep - let affliction expiry handle it
        if has_affliction(session, "magic_sleep"):
            continue

        # Increment the sleep counter
        if "sleep_tick_counter" not in session:
            session["sleep_tick_counter"] = 0
        else:
            session["sleep_tick_counter"] += 1

        # Check if it's time to heal
        if session["sleep_tick_counter"] >= SLEEP_HEALING_INTERVAL:
            # Reset counter
            session["sleep_tick_counter"] = 0

            # Check if player is at max stamina already
            if player.stamina >= player.max_stamina:
                # Wake the player up via the common function
                await wake_player(
                    player, sid, online_sessions, sio, utils, max_stamina_reached=True
                )
            elif player.stamina == player.max_stamina - 1:
                # This heal will max out stamina
                player.stamina += 1

                # Send updated stats to the player
                await utils.send_stats_update(sio, sid, player)

                # Wake the player up via the common function
                await wake_player(
                    player, sid, online_sessions, sio, utils, max_stamina_reached=True
                )
            else:
                # Normal healing case - not yet at max stamina
                player.stamina += 1

                # Send updated stats to the player
                await utils.send_stats_update(sio, sid, player)

                # Send healing message periodically (every 3 healing ticks)
                if session.get("healing_message_count", 0) % 3 == 0:
                    await utils.send_message(sio, sid, "ZZZzzz...")

                # Increment healing message counter
                if "healing_message_count" not in session:
                    session["healing_message_count"] = 1
                else:
                    session["healing_message_count"] += 1

                # Save player state
                player_manager.save_players()


# Register sleep and wake commands
command_registry.register(
    "sleep", handle_sleep, "Go to sleep to recover stamina over time."
)
command_registry.register("wake", handle_wake, "Wake up from sleeping.")
command_registry.register_alias("rest", "sleep")
command_registry.register_alias("awake", "wake")
