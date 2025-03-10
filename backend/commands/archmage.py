# backend/commands/archmage.py

from commands.registry import command_registry
import logging
import sys
import os
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_set_points(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle setting points for another player. Archmage-only command.
    Usage: set <player_name> <points>
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player executing the command
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Confirmation message
    """
    # Check if the player is an Archmage
    if player.level != "Archmage":
        return "You do not have the authority to use this command."
    
    # Parse the command string - expected format: "set player_name points"
    command_parts = cmd.get("original", "").split()
    
    # Remove the "set" verb
    if command_parts and command_parts[0].lower() == "set":
        command_parts = command_parts[1:]
    
    # Need at least two parts: player_name and points
    if len(command_parts) < 2:
        return "Set points for whom? (Usage: set <player_name> <points>)"
    
    # Last part should be the points, everything before is the player name
    points_str = command_parts[-1]
    player_name = " ".join(command_parts[:-1])
    
    if not player_name or not points_str:
        return "Specify both player name and points. (Usage: set <player_name> <points>)"
    
    # Try to get the target player from online_sessions or player_manager
    target_player = None
    target_sid = None
    
    # First check online players
    for sid, session_data in online_sessions.items():
        other_player = session_data.get('player')
        if other_player and other_player.name.lower() == player_name.lower():
            target_player = other_player
            target_sid = sid
            break
    
    # If not found online, try player_manager
    if not target_player:
        target_player = player_manager.login(player_name)
    
    if not target_player:
        return f"Player '{player_name}' not found."
    
    # Parse points
    try:
        points = int(points_str)
        if points < 0:
            return "Points cannot be negative."
    except ValueError:
        return f"Points must be a number, got '{points_str}'."
    
    # Store original level
    original_level = target_player.level
    
    # Set points directly and recalculate level
    target_player.points = points
    target_player.level_up()  # Directly call level_up after setting points
    
    # Save the updated player
    player_manager.save_players()
    
    # If player is online, update their stats
    if target_sid and sio and utils:
        await utils.send_stats_update(sio, target_sid, target_player)
        await utils.send_message(sio, target_sid, 
                               f"A powerful mage has set your points to {points}.\nYour level of experience is now {target_player.level}.")
    
    # Confirmation message for the Archmage
    if original_level != target_player.level:
        return f"Points for {target_player.name} set to {points}. Level changed from {original_level} to {target_player.level}."
    else:
        return f"Points for {target_player.name} set to {points}. Level remains {target_player.level}."
        
# ===== RESET COMMAND =====
async def handle_reset(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle world reset. Archmage-only command.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player executing the command
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Confirmation message
    """
    # Check if the player is an Archmage
    if player.level != "Archmage":
        return "You do not have the authority to use this command."
    
    # Confirm intent
    subject = cmd.get("subject")
    if subject and subject.lower() == "confirm":
        # Notify all players
        if online_sessions and sio and utils:
            for sid, session_data in online_sessions.items():
                other_player = session_data.get('player')
                if other_player:
                    await utils.send_message(sio, sid, 
                                         f"----------------------------\nWORLD RESET INITIATED\n----------------------------\n"
                                         f"Your vision begins to blur as powerful forces tamper with time...\n"
                                         f"Slowly, you sense everything returning to how it once was...\n"
                                         f"You will be disconnected and can reconnect in a moment.")
        
        # Log the reset
        logger.info(f"Mid-week reset initiated by Archmage {player.name}")
        
        # Give a brief delay for messages to be sent
        await asyncio.sleep(2)
        
        # Perform some basic cleanup
        for sid in list(online_sessions.keys()):
            try:
                await sio.disconnect(sid)
            except Exception as e:
                logger.error(f"Error disconnecting client {sid}: {e}")
        
        # Option 1: Restart the program (Python process)
        # This is the most reliable way to reset everything
        logger.info("Restarting the server process...")
        python = sys.executable
        os.execl(python, python, *sys.argv)
        
        # We'll never reach this point due to the process restart
        return "Resetting the world..."
    else:
        return "This will reset the entire world and disconnect all players.\nType 'reset confirm' to proceed."

# Register Archmage commands
command_registry.register("set", handle_set_points, "Set points for a player (Archmage only).")
command_registry.register("reset", handle_reset, "Reset the world to its start-of-week condition (Archmage only).")