# backend/commands/executor.py

from commands.parser import parse_command, is_movement_command
from commands.registry import command_registry
from services.notifications import broadcast_arrival, broadcast_departure
from commands.combat import check_command_restrictions, is_in_combat
import asyncio
import logging
from commands.utils import get_player_inventory

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def execute_command(cmd, player, game_state, player_manager, online_sessions=None, sio=None, utils=None):
    """
    Execute a command.
    
    Args:
        cmd (dict): The parsed command dictionary
        player (Player): The player executing the command
        game_state (GameState): The current game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Optional online sessions dictionary
        sio (SocketIO): Optional Socket.IO instance
        utils (module): Optional utilities module
        
    Returns:
        str: The result of the command execution
    """
    # Get the verb from the command dictionary
    verb = cmd.get("verb")
    
    # Special case for "quit"
    if verb and verb.lower() == "quit":
        # Check if player is in combat
        if is_in_combat(player.name):
            return "You can't quit while in combat! That would be cowardice."
        return "quit"
    
    # Get session ID if available
    sid = None
    if online_sessions:
        for s, session in online_sessions.items():
            if session.get('player') == player:
                sid = s
                break
    
    # Check command restrictions (combat, etc.)
    allowed, message = check_command_restrictions(cmd, player, sio, sid, utils)
    if not allowed:
        return message
    
    # Check if it's a movement command
    if verb and is_movement_command(verb):
        result = await handle_movement(cmd, player, game_state, player_manager, online_sessions, sio, utils)
        return result
    
    # Get the handler for this verb
    handler = command_registry.get_handler(verb)
    if handler:
        # Call the handler with the parsed command and appropriate context
        result = await handler(cmd, player, game_state, player_manager, online_sessions, sio, utils)
        return result
    else:
        return f"I don't know how to '{verb}'."


async def handle_movement(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle movement commands.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player executing the command
        game_state (GameState): The current game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Optional online sessions dictionary
        sio (SocketIO): Optional Socket.IO instance
        utils (module): Optional utilities module
        
    Returns:
        str: The result of the movement
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
    """
    Build a description of the current room, including items and other players.
    
    Args:
        player (Player): The player looking
        game_state (GameState): The current game state
        online_sessions (dict): Optional online sessions dictionary
        look (bool): Whether this is from an explicit "look" command
        
    Returns:
        str: The room description
    """
    current_room = game_state.get_room(player.current_room)
    
    # Build the room description
    room_desc = f"{current_room.name}"
    
    if current_room.room_id not in player.visited or look:
        room_desc += f"\n{current_room.description}"
        player.visited.add(current_room.room_id)
    
    # Get all visible items (including those that become visible due to conditions)
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
                continue  # Skip sessions without a player
            if other_player.current_room == current_room.room_id and other_player != player:
                inv_summary = get_player_inventory(other_player)
                if inv_summary == "":
                    inv_summary = "nothing"
                
                # Check if the player is in combat
                from commands.combat import is_in_combat
                combat_status = ""
                if is_in_combat(other_player.name):
                    combat_status = " (in combat)"
                
                # Check if the player is sleeping
                sleep_status = ""
                if session_data.get('sleeping', False):
                    sleep_status = ", asleep"
                
                players_here.append(f"{other_player.name} the {other_player.level}{combat_status} is here{sleep_status}, carrying {inv_summary}")
    
    if players_here:
        room_desc += "\n" + "\n".join(players_here)
    
    return room_desc.strip()
