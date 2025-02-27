# backend/services/notifications.py

from socketio import AsyncServer

# Assuming online_sessions and send_message are passed in or imported appropriately.
# You may need to adjust how you reference these depending on your architecture.

def set_context(online_sessions, send_message):
    """
    Sets global variables for notifications. This is one way to inject
    dependencies from your server setup.
    """
    global SESSIONS, send_msg
    SESSIONS = online_sessions
    send_msg = send_message

async def broadcast_arrival(player):
    """
    Notify all players in the player's current room that the player has arrived.
    """
    room_id = player.current_room
    display_name = player.name
    for sid, session_data in SESSIONS.items():
        other_player = session_data.get('player')
        if not other_player:
            continue  # Skip sessions that haven't authenticated.
        if other_player.current_room == room_id and other_player != player:
            await send_msg(sid, f"{display_name} has just arrived.")

async def broadcast_departure(room_id, departing_player):
    """
    Notify all players in the room that someone has left.
    """
    for sid, session_data in SESSIONS.items():
        if ('player' in session_data and 
            session_data['player'] is not None and 
            session_data['player'].current_room == room_id and 
            session_data['player'] != departing_player):
            await send_msg(sid, f"{departing_player.name} has left")
