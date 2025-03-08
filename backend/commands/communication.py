# backend/commands/communication.py

from commands.registry import command_registry
import logging

logger = logging.getLogger(__name__)

# ===== SHOUT COMMAND =====
async def handle_shout(cmd, player, game_state, player_manager, online_sessions, sio, utils):
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
    subject = cmd.get("subject")
    
    # Get the current sid from the online_sessions
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get('player') == player:
            current_sid = sid
            break
    
    if not current_sid:
        return "Error: Session not found"
    
    # If no message provided, prompt for one
    if not subject:
        if 'pending_comm' not in online_sessions.get(current_sid, {}):
            online_sessions[current_sid]['pending_comm'] = {'type': 'shout'}
            return "OK, tell me the message:"
        return "You need to provide a message to shout."
    
    # Broadcast the shout to all players
    shout_text = f"{player.name} the {player.level} shouts \"{subject}\""
    
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            if 'player' in session_data and sid != current_sid:
                await utils.send_message(sio, sid, shout_text)
    
    return ""


# ===== SAY COMMAND (ROOM MESSAGE) =====
async def handle_say(cmd, player, game_state, player_manager, online_sessions, sio, utils):
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
    subject = cmd.get("subject")
    
    # If no message provided, return an error
    if not subject:
        return "What do you want to say?"
    
    # Get the current sid from the online_sessions
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get('player') == player:
            current_sid = sid
            break
    
    if not current_sid:
        return "Error: Session not found"
    
    # Format the message
    room_msg = f"{player.name} the {player.level} says \"{subject}\""
    
    # Send to all players in the same room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == player.current_room and 
                sid != current_sid):
                await utils.send_message(sio, sid, room_msg)
    
    return ""


# ===== TELL COMMAND (PRIVATE MESSAGE) =====
async def handle_tell(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle sending a private message to another player.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player sending the message
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Confirmation message
    """
    subject = cmd.get("subject")  # recipient
    instrument = cmd.get("instrument")  # message
    
    # Check if recipient and message are provided
    if not subject:
        return "Who do you want to tell something to?"
    
    # Get the current sid from the online_sessions
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get('player') == player:
            current_sid = sid
            break
    
    if not current_sid:
        return "Error: Session not found"
    
    if not instrument:
        # If no message provided, prompt for one
        if 'pending_comm' not in online_sessions.get(current_sid, {}):
            online_sessions[current_sid]['pending_comm'] = {
                'type': 'private', 
                'recipient': subject
            }
            return f"OK, tell me your message for {subject}:"
        return f"What do you want to tell {subject}?"
    
    # Find the recipient
    recipient_sid = None
    recipient_name = subject.lower()
    for sid, session_data in online_sessions.items():
        other_player = session_data.get('player')
        if other_player and other_player.name.lower() == recipient_name:
            recipient_sid = sid
            break
    
    if recipient_sid:
        if sio and utils:
            # Send the private message
            await utils.send_message(
                sio, 
                recipient_sid, 
                f"{player.name} the {player.level} tells you \"{instrument}\""
            )
        return f""
    else:
        return f"Player '{subject}' is not online."


# ===== ACT COMMAND =====
async def handle_act(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle acting out an emote in the current room.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player acting
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Confirmation message
    """
    subject = cmd.get("subject")
    
    # If no action provided, return an error
    if not subject:
        return "What do you want to do?"
    
    # Get the current sid from the online_sessions
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get('player') == player:
            current_sid = sid
            break
    
    if not current_sid:
        return "Error: Session not found"
    
    # Format the action message
    action_msg = f"**{player.name} {subject}**"
    
    # Send to all players in the same room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == player.current_room and 
                sid != current_sid):
                await utils.send_message(sio, sid, action_msg)
    
    return action_msg


# ===== CONVERSE COMMAND =====
async def handle_converse(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Toggle converse mode for a player.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player
        online_sessions (dict): Online sessions dictionary
        
    Returns:
        str: Confirmation message
    """
    # Get the current sid from the online_sessions
    current_sid = None
    for sid, session in online_sessions.items():
        if session.get('player') == player:
            current_sid = sid
            break
    
    if not current_sid:
        return "Error: Session not found"
    
    if online_sessions and current_sid in online_sessions:
        session = online_sessions[current_sid]
        current_mode = session.get('converse_mode', False)
        session['converse_mode'] = not current_mode
        
        if session['converse_mode']:
            return ("Converse mode ON. Everything you type will be spoken in the room.\n"
                   "Use * or > to exit, or use (command) for special commands.")
        else:
            return "Converse mode OFF."
    
    return "Could not toggle converse mode."


# ===== HANDLE PENDING COMMUNICATION =====
async def handle_pending_communication(pending, message_text, player, sid, online_sessions, sio, utils):
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
        del online_sessions[sid]['pending_comm']
        return "Communication cancelled."
    
    if pending['type'] == 'shout':
        # Handle pending shout
        shout_text = f"{player.name} the {player.level} shouts \"{message_text}\""
        
        for osid, osession in online_sessions.items():
            if 'player' in osession and osid != sid:
                await utils.send_message(sio, osid, shout_text)
        
        del online_sessions[sid]['pending_comm']
        return message_text
    
    elif pending['type'] == 'private':
        # Handle pending private message
        recipient_name = pending['recipient'].lower()
        recipient_sid = None
        
        for osid, osession in online_sessions.items():
            other_player = osession.get('player')
            if other_player and other_player.name.lower() == recipient_name:
                recipient_sid = osid
                break
        
        if recipient_sid:
            await utils.send_message(
                sio, 
                recipient_sid, 
                f"{player.name} the {player.level} tells you \"{message_text}\""
            )
            del online_sessions[sid]['pending_comm']
            return ""
        else:
            del online_sessions[sid]['pending_comm']
            return f"Player '{pending['recipient']}' is not online."
    
    # Unknown pending type
    del online_sessions[sid]['pending_comm']
    return "Communication cancelled."


# Register communication commands
command_registry.register("shout", handle_shout, "Broadcast a message to all players.")
command_registry.register("say", handle_say, "Say something to everyone in your current room.")
command_registry.register("tell", handle_tell, "Send a private message to another player.")
command_registry.register("act", handle_act, "Perform an action or emote in the current room.")
command_registry.register("converse", handle_converse, "Toggle converse mode (auto-say).")

# Register aliases
command_registry.register_alias("sh", "shout")
command_registry.register_alias('"', "say")  # Starting with a quote is a say command
command_registry.register_alias("whisper", "tell")