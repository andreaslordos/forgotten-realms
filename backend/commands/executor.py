# backend/commands/executor.py

from commands.parser import parse_command, is_movement_command
from commands.registry import command_registry
from services.notifications import broadcast_arrival, broadcast_departure
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def execute_command(command_str, player, game_state, player_manager, visited, online_sessions=None, sio=None, utils=None):
    """
    Execute a command string.
    
    Args:
        command_str (str): The command string to execute
        player (Player): The player executing the command
        game_state (GameState): The current game state
        player_manager (PlayerManager): The player manager
        visited (set): Set of room IDs the player has visited
        online_sessions (dict): Optional online sessions dictionary
        sio (SocketIO): Optional Socket.IO instance
        utils (module): Optional utilities module
        
    Returns:
        str: The result of the command execution
    """
    # Get players in the current room
    players_in_room = []
    if online_sessions:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if other_player and other_player.current_room == player.current_room:
                players_in_room.append(other_player)
    
    # Parse the command string - now passing online_sessions to access all players
    parsed_commands = parse_command(command_str, command_registry.command_context, players_in_room, online_sessions)
    
    if not parsed_commands:
        return "Huh? I didn't understand that."
    
    # Execute each command and collect results
    results = []
    for cmd in parsed_commands:
        verb = cmd["verb"]
        
        # Special case for "quit"
        if verb.lower() == "quit":
            return "quit"
        
        # Check if it's a movement command
        if is_movement_command(verb):
            result = await handle_movement(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils)
            results.append(result)
            continue
        
        # Get the handler for this verb
        handler = command_registry.get_handler(verb)
        if handler:
            # Call the handler with the parsed command and appropriate context
            result = await handler(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils)
            results.append(result)
        else:
            results.append(f"I don't know how to '{verb}'.")
    
    return "\n".join(filter(None, results))  # Filter out empty results


async def handle_movement(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """
    Handle movement commands.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player executing the command
        game_state (GameState): The current game state
        player_manager (PlayerManager): The player manager
        visited (set): Set of room IDs the player has visited
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
        
        # Use build_look_description to include other players immediately
        if visited is not None:
            visited.add(new_room.room_id)
        return build_look_description(player, game_state, online_sessions)
    else:
        return "You can't go that way."


def build_look_description(player, game_state, online_sessions=None):
    """
    Build a description of the current room, including items and other players.
    
    Args:
        player (Player): The player looking
        game_state (GameState): The current game state
        online_sessions (dict): Optional online sessions dictionary
        
    Returns:
        str: The room description
    """
    current_room = game_state.get_room(player.current_room)
    
    # Build the room description
    room_desc = f"{current_room.name}\n{current_room.description}\n"
    
    # List items in the room
    if current_room.items:
        items_desc = []
        for item in current_room.items:
            items_desc.append(item.description)
        if items_desc:
            room_desc += "\n".join(items_desc) + "\n"
    
    # List other players present in the room
    players_here = []
    if online_sessions:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if not other_player:
                continue  # Skip sessions without a player
            if other_player.current_room == current_room.room_id and other_player != player:
                inv_summary = ", ".join(item.name for item in other_player.inventory) if other_player.inventory else "nothing"
                players_here.append(f"{other_player.name} is here, carrying {inv_summary}")
    
    if players_here:
        room_desc += "\n" + "\n".join(players_here)
    
    return room_desc.strip()