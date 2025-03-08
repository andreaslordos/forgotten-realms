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

async def broadcast_room(room_id, message, exclude_player=[]):
    """
    Notify all players in a room that a message has been broadcast.
    """
    global SESSIONS, send_msg
    if not SESSIONS or not send_msg:
        logger.warning("Attempted to broadcast room but context not initialized")
        return
    
    for sid, session_data in SESSIONS.items():
        other_player = session_data.get('player')
        if not other_player:
            continue  # Skip sessions that haven't authenticated.
        if other_player.current_room == room_id and other_player.name not in exclude_player:
            await send_msg(sid, message)

async def broadcast_arrival(player):
    """
    Notify all players in the player's current room that the player has arrived.
    """        
    room_id = player.current_room
    display_name = player.name
    display_level = player.level
    logger.debug(f"Broadcasting arrival of {display_name} to room {room_id}")
    await broadcast_room(room_id, f"{display_name} the {display_level} has just arrived.", exclude_player=[player.name])

async def broadcast_departure(room_id, departing_player):
    """
    Notify all players in the room that someone has left.
    """
    display_name = departing_player.name
    display_level = departing_player.level
    logger.debug(f"Broadcasting departure of {display_name} from room {room_id}")
    await broadcast_room(room_id, f"{display_name} the {display_level} has left.", exclude_player=[departing_player.name])

async def broadcast_logout(player):
    """
    Notify all players in a room that a player in that room has logged out.
    """    
    room_id = player.current_room
    display_name = player.name
    logger.debug(f"Broadcasting logout of {display_name} from room {room_id}")
    await broadcast_room(room_id, f"{display_name} the {player.level} has just passed on.", exclude_player=[player.name])