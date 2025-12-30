# backend/commands/communication.py

from typing import Dict, Any, Optional
from commands.registry import command_registry
import logging
from commands.rest import wake_player

logger = logging.getLogger(__name__)


# ===== SHOUT COMMAND =====
async def handle_shout(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle global shout command.

    Args:
        cmd (dict): The parsed command
        player (Player): The player shouting
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module

    Returns:
        str: Confirmation message
    """
    # Get the subject (shout message)
    subject: Optional[str] = cmd.get("subject")

    # Get the current sid from the online_sessions
    current_sid: Optional[str] = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found"

    # Check if player is DUMB (cannot speak)
    from services.affliction_service import has_affliction

    if has_affliction(online_sessions.get(current_sid, {}), "dumb"):
        return "You try to shout but no words come out!"

    # If no message provided, prompt for one
    if not subject:
        if "pending_comm" not in online_sessions.get(current_sid, {}):
            online_sessions[current_sid]["pending_comm"] = {"type": "shout"}
            return "OK, tell me the message:"
        return "You need to provide a message to shout."

    # Broadcast the shout to all players
    shout_text = f'{player.name} the {player.level} shouts "{subject}"'

    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            if "player" in session_data and sid != current_sid:
                # Skip players who are DEAF (cannot hear)
                if has_affliction(session_data, "deaf"):
                    continue

                # Wake up sleeping players before sending the message
                if session_data.get("sleeping"):
                    sleeping_player = session_data.get("player")
                    # Wake them up with the combat=False flag
                    await wake_player(
                        sleeping_player, sid, online_sessions, sio, utils, combat=False
                    )

                    # Send a special message to indicate they were woken by the shout
                    await utils.send_message(
                        sio, sid, "You are awakened by a loud shout!"
                    )

                # Send the shout message
                await utils.send_message(sio, sid, shout_text)

    return ""


# ===== SAY COMMAND (ROOM MESSAGE) =====
async def handle_say(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle saying something in the current room.

    Args:
        cmd (dict): The parsed command
        player (Player): The player saying
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module

    Returns:
        str: Confirmation message
    """
    # Get the subject (say message)
    subject: Optional[str] = cmd.get("subject")

    # If no message provided, return an error
    if not subject:
        return "What do you want to say?"

    # Get the current sid from the online_sessions
    current_sid: Optional[str] = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found"

    # Check if player is DUMB (cannot speak)
    from services.affliction_service import has_affliction

    if has_affliction(online_sessions.get(current_sid, {}), "dumb"):
        return "You try to speak but no words come out!"

    # Format the message
    room_msg = f'{player.name} the {player.level} says "{subject}"'

    # Send to all players in the same room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get("player")
            if (
                other_player
                and other_player.current_room == player.current_room
                and sid != current_sid
            ):
                # Skip players who are DEAF (cannot hear)
                if has_affliction(session_data, "deaf"):
                    continue
                await utils.send_message(sio, sid, room_msg)

    return ""


# ===== TELL COMMAND (PRIVATE MESSAGE) =====
async def handle_tell(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle sending a private message to another player.
    """
    # Check if the "verb" is actually a player name (for "name message" pattern)
    recipient_name: Optional[str] = None
    message: Optional[str] = None

    # Check the most common format: "<player_name> <message>"
    if cmd.get("verb") and cmd.get("subject") and not cmd.get("instrument"):
        recipient_name = cmd.get("verb")
        message = cmd.get("subject")
    # Check standard format: "tell <player> <message>"
    else:
        recipient_name = cmd.get("subject")
        message = cmd.get("instrument")

    # Get the current sid from the online_sessions
    current_sid: Optional[str] = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found"

    # Check if player is DUMB (cannot speak)
    from services.affliction_service import has_affliction

    if has_affliction(online_sessions.get(current_sid, {}), "dumb"):
        return "You try to speak but no words come out!"

    if not recipient_name:
        return "Who do you want to tell something to?"

    if not message:
        # If no message provided, prompt for one
        if "pending_comm" not in online_sessions.get(current_sid, {}):
            online_sessions[current_sid]["pending_comm"] = {
                "type": "private",
                "recipient": recipient_name,
            }
            return f"OK, tell me your message for {recipient_name}:"
        return f"What do you want to tell {recipient_name}?"

    # Find the recipient
    recipient_sid: Optional[str] = None

    for sid, session_data in online_sessions.items():
        other_player = session_data.get("player")
        if other_player and other_player.name.lower() == recipient_name.lower():
            recipient_sid = sid
            break

    if recipient_sid:
        # Check if recipient is DEAF (cannot hear)
        recipient_session = online_sessions.get(recipient_sid, {})
        if has_affliction(recipient_session, "deaf"):
            return f"{recipient_name} cannot hear you - they are deafened!"

        if sio and utils:
            # Send the private message
            await utils.send_message(
                sio,
                recipient_sid,
                f'{player.name} the {player.level} tells you "{message}"',
            )
        return f'You tell {recipient_name}, "{message}"'
    else:
        return f"Player '{recipient_name}' is not online."


# ===== ACT COMMAND =====
async def handle_act(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """
    Handle acting out an emote in the current room.
    """
    # Get the subject (action text)
    subject: Optional[str] = cmd.get("subject")

    # If no action provided, return an error
    if not subject:
        return "What do you want to do?"

    # Get the current sid from the online_sessions
    current_sid: Optional[str] = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found"

    # Format the action message
    action_msg = f"**{player.name} {subject}**"

    # Send to all players in the same room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get("player")
            if (
                other_player
                and other_player.current_room == player.current_room
                and sid != current_sid
            ):
                await utils.send_message(sio, sid, action_msg)

    return action_msg


# ===== CONVERSE COMMAND =====
async def handle_converse(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """
    Toggle converse mode for a player.
    """
    # Get the current sid from the online_sessions
    current_sid: Optional[str] = None
    for sid, session in online_sessions.items():
        if session.get("player") == player:
            current_sid = sid
            break

    if not current_sid:
        return "Error: Session not found"

    if online_sessions and current_sid in online_sessions:
        session = online_sessions[current_sid]
        current_mode = session.get("converse_mode", False)
        session["converse_mode"] = not current_mode

        if session["converse_mode"]:
            return (
                "Converse mode ON. Everything you type will be spoken in the room.\n"
                "Use * or > to exit, or use (command) for special commands."
            )
        else:
            return "Converse mode OFF."

    return "Could not toggle converse mode."


# ===== HANDLE PENDING COMMUNICATION =====
async def handle_pending_communication(
    pending: Dict[str, Any],
    message_text: str,
    player: Any,
    sid: str,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """
    Process a pending communication request.

    Args:
        pending (dict): The pending communication info
        message_text (str): The message text
        player (Player): The player
        sid (str): The session ID
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module

    Returns:
        str: Confirmation message
    """
    if not message_text.strip():
        del online_sessions[sid]["pending_comm"]
        return "Communication cancelled."

    if pending["type"] == "shout":
        # Handle pending shout
        shout_text = f'{player.name} the {player.level} shouts "{message_text}"'

        for osid, osession in online_sessions.items():
            if "player" in osession and osid != sid:
                await utils.send_message(sio, osid, shout_text)

        del online_sessions[sid]["pending_comm"]
        return message_text

    elif pending["type"] == "private":
        # Handle pending private message
        recipient_name: str = pending["recipient"].lower()
        recipient_sid: Optional[str] = None

        for osid, osession in online_sessions.items():
            other_player = osession.get("player")
            if other_player and other_player.name.lower() == recipient_name:
                recipient_sid = osid
                break

        if recipient_sid:
            await utils.send_message(
                sio,
                recipient_sid,
                f'{player.name} the {player.level} tells you "{message_text}"',
            )
            del online_sessions[sid]["pending_comm"]
            return ""
        else:
            del online_sessions[sid]["pending_comm"]
            return f"Player '{pending['recipient']}' is not online."

    # Unknown pending type
    del online_sessions[sid]["pending_comm"]
    return "Communication cancelled."


# Register communication commands
command_registry.register("shout", handle_shout, "Broadcast a message to all players.")
command_registry.register(
    "say", handle_say, "Say something to everyone in your current room."
)
command_registry.register(
    "tell", handle_tell, "Send a private message to another player."
)
command_registry.register(
    "act", handle_act, "Perform an action or emote in the current room."
)
command_registry.register(
    "converse", handle_converse, "Toggle converse mode (auto-say)."
)

# Register aliases
command_registry.register_alias("sh", "shout")
command_registry.register_alias('"', "say")  # Starting with a quote is a say command
command_registry.register_alias("whisper", "tell")
