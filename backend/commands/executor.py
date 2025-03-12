# commands/executor.py (Patched)

import asyncio
import logging
from commands.parser import parse_command_wrapper, is_movement_command
from commands.registry import command_registry
from services.notifications import broadcast_arrival, broadcast_departure

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def execute_command(cmd, player, game_state, player_manager, online_sessions=None, sio=None, utils=None):
    """
    Execute a command.
    
    Args:
        cmd: The parsed command dictionary
        player: The player executing the command
        game_state: The current game state
        player_manager: The player manager
        online_sessions: Optional online sessions dictionary
        sio: Optional Socket.IO instance
        utils: Optional utilities module
        
    Returns:
        The result of the command execution
    """
    # Get the verb from the command dictionary
    verb = cmd.get("verb")
    
    # Special case for "quit"
    if verb and verb.lower() == "quit":
        return "quit"
    
    # Check if it's a movement command
    if verb and is_movement_command(verb):
        result = await handle_movement(cmd, player, game_state, player_manager, online_sessions, sio, utils)
        return result
    
    # Get the handler for this verb
    handler = command_registry.get_handler(verb)
    
    if handler:
        # Call the handler with the parsed command and appropriate context
        logger.debug("Calling handler")
        result = await handler(cmd, player, game_state, player_manager, online_sessions, sio, utils)
        return result
    else:
        logger.debug("Did not find handler, checking if player name")
        # New code: Check if verb is a player name for a private message
        if online_sessions and verb:
            # Look for players with matching names
            recipient_found = False
            for sid, session_data in online_sessions.items():
                other_player = session_data.get('player')
                if other_player and verb.lower() in other_player.name.lower():
                    recipient_found = True
                    # It's a private message! Route to the tell handler
                    from commands.communication import handle_tell
                    # Reformat the command to use the correct fields
                    pm_cmd = {
                        "verb": verb,              # Use the player name as is
                        "subject": cmd.get("subject"),  # Use the message text
                        "original": cmd.get("original")
                    }
                    result = await handle_tell(pm_cmd, player, game_state, player_manager, online_sessions, sio, utils)
                    return result
            
            if recipient_found:
                return ""  # Return empty string if recipient found (handler will send messages)
        
        return f"I don't know how to '{verb}'."

async def handle_movement(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle movement commands.
    
    Args:
        cmd: The parsed command
        player: The player executing the command
        game_state: The current game state
        player_manager: The player manager
        online_sessions: Optional online sessions dictionary
        sio: Optional Socket.IO instance
        utils: Optional utilities module
        
    Returns:
        The result of the movement
    """
    direction = cmd["verb"]
    old_room = game_state.get_room(player.current_room)
    
    if direction in old_room.exits:
        new_room_id = old_room.exits[direction]
        
        # Notify departure from the old room
        if online_sessions and sio and utils:
            await broadcast_departure(old_room.room_id, player)
        
        # Update player's room
        player.set_current_room(new_room_id)
        player_manager.save_players()
        
        new_room = game_state.get_room(new_room_id)
        
        # Notify arrival in the new room
        if online_sessions and sio and utils:
            await broadcast_arrival(player)
        
        return build_look_description(player, game_state, online_sessions)
    else:
        return "You can't go that way."

def build_look_description(player, game_state, online_sessions=None, look=False):
    """Build a description of the current room."""
    # This function remains largely unchanged
    current_room = game_state.get_room(player.current_room)
    
    # Build the room description
    room_desc = f"{current_room.name}"
    
    if current_room.room_id not in player.visited or look:
        room_desc += f"\n{current_room.description}"
        player.visited.add(current_room.room_id)
    
    # Get all visible items
    visible_items = current_room.get_items(game_state)
    
    # List items in the room
    if visible_items:
        items_desc = []
        for item in visible_items:
            items_desc.append(item.description)
        if items_desc:
            room_desc += "\n" + "\n".join(items_desc)
    
    # List other players present in the room
    players_here = []
    if online_sessions:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if not other_player:
                continue
            if other_player.current_room == current_room.room_id and other_player != player:
                from commands.utils import get_player_inventory
                inv_summary = get_player_inventory(other_player)
                if inv_summary == "":
                    inv_summary = "nothing"
                
                # Check player states
                statuses = []
                
                # Check if the player is in combat
                from commands.combat import is_in_combat
                if is_in_combat(other_player.name):
                    statuses.append("in combat")
                
                # Check if the player is sleeping
                if session_data.get('sleeping', False):
                    statuses.append("asleep")
                
                status_text = f" ({', '.join(statuses)})" if statuses else ""
                
                players_here.append(
                    f"{other_player.name} the {other_player.level}{status_text} is here, carrying {inv_summary}"
                )
    
    if players_here:
        room_desc += "\n" + "\n".join(players_here)
    
    return room_desc.strip()