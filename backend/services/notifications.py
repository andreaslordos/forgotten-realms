# backend/services/notifications.py

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables initialized as None
SESSIONS = None
send_msg = None

def set_context(online_sessions, send_message):
    """
    Sets global variables for notifications. This is one way to inject
    dependencies from your server setup.
    """
    global SESSIONS, send_msg
    logger.debug("Setting notification context")
    SESSIONS = online_sessions
    send_msg = send_message
    logger.info("Notification context set successfully")

async def broadcast_arrival(player):
    """
    Notify all players in the player's current room that the player has arrived.
    """
    global SESSIONS, send_msg
    if not SESSIONS or not send_msg:
        logger.warning("Attempted to broadcast arrival but context not initialized")
        return
        
    room_id = player.current_room
    display_name = player.name
    logger.debug(f"Broadcasting arrival of {display_name} to room {room_id}")
    
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
    global SESSIONS, send_msg
    if not SESSIONS or not send_msg:
        logger.warning("Attempted to broadcast departure but context not initialized")
        return
        
    logger.debug(f"Broadcasting departure of {departing_player.name} from room {room_id}")
    
    for sid, session_data in SESSIONS.items():
        if ('player' in session_data and 
            session_data['player'] is not None and 
            session_data['player'].current_room == room_id and 
            session_data['player'] != departing_player):
            await send_msg(sid, f"{departing_player.name} has left")