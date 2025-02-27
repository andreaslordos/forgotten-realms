# backend/commands/communication.py

async def process_communication_command(cmd, player, session, sid, online_sessions, sio, utils):
    """
    Processes communication commands:
      - Global shout: "shout <message>" or "shout" + prompt
      - Room message: "<message>" (starts with quote)
      - Private message: "<player> <message>" or "<player>" + prompt
    """
    # Handle pending communications first
    if 'pending_comm' in session:
        return await handle_pending_communication(session.pop('pending_comm'), cmd, player, sid, online_sessions, sio, utils)

    # Parse and handle new communications
    if cmd.lower().startswith("shout"):
        return await handle_shout(cmd, player, session, sid, online_sessions, sio, utils)
    
    if cmd.startswith('"'):
        return await handle_room_message(cmd[1:].strip(), player, sid, online_sessions, sio, utils)
    
    # Try to handle as private message
    tokens = cmd.split(maxsplit=1)
    recipient_sid = find_recipient_sid(tokens[0], online_sessions)
    if recipient_sid is not None:
        return await handle_private_message(tokens, player, session, sid, recipient_sid, sio, utils)

    return False

async def handle_pending_communication(pending, cmd, player, sid, online_sessions, sio, utils):
    message = cmd.strip()
    if not message:
        return True

    if pending['type'] == 'shout':
        await broadcast_message(f"{player.name} the {player.level} shouts \"{message}\"",
                              sid, online_sessions, sio, utils)
    elif pending['type'] == 'private':
        recipient_sid = find_recipient_sid(pending['recipient'], online_sessions)
        if recipient_sid:
            await utils.send_message(sio, recipient_sid,
                                   f"{player.name} the {player.level} tells you \"{message}\"")
    return True

async def handle_shout(cmd, player, session, sid, online_sessions, sio, utils):
    parts = cmd.split(maxsplit=1)
    if len(parts) == 1 or not parts[1].strip():
        session['pending_comm'] = {'type': 'shout'}
        await utils.send_message(sio, sid, "OK, tell me the message:")
    else:
        await broadcast_message(f"{player.name} the {player.level} shouts \"{parts[1].strip()}\"",
                              sid, online_sessions, sio, utils)
    return True

async def handle_room_message(message, player, sid, online_sessions, sio, utils):
    if not message:
        return True
    room_msg = f"{player.name} the {player.level} says \"{message}\""
    for osid, osession in online_sessions.items():
        other_player = osession.get('player')
        if other_player and other_player.current_room == player.current_room and osid != sid:
            await utils.send_message(sio, osid, room_msg)
    return True

async def handle_private_message(tokens, player, session, sid, recipient_sid, sio, utils):
    if len(tokens) == 1 or not tokens[1].strip():
        session['pending_comm'] = {'type': 'private', 'recipient': tokens[0]}
        await utils.send_message(sio, sid, "OK, tell me your message:")
    else:
        await utils.send_message(sio, recipient_sid,
                               f"{player.name} the {player.level} tells you \"{tokens[1].strip()}\"")
    return True

def find_recipient_sid(name, online_sessions):
    """Find a player's session ID by their name (case-insensitive)"""
    name = name.lower()
    for osid, osession in online_sessions.items():
        other_player = osession.get('player')
        if other_player and other_player.name.lower() == name:
            return osid
    return None

async def broadcast_message(message, sender_sid, online_sessions, sio, utils):
    """Broadcast a message to all players except the sender"""
    for osid in online_sessions:
        if osid != sender_sid:
            await utils.send_message(sio, osid, message)
