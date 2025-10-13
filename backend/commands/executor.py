# commands/executor.py (Patched)

import asyncio
import logging
from commands.parser import parse_command_wrapper, is_movement_command
from commands.registry import command_registry
from services.notifications import broadcast_arrival, broadcast_departure

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def execute_command(cmd, player, game_state, player_manager, online_sessions=None, sio=None, utils=None, player_sid=None):
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
        player_sid: Optional player's session ID

    Returns:
        The result of the command execution
    """
    # Check if player is awaiting respawn
    if online_sessions and player_sid and online_sessions.get(player_sid, {}).get('awaiting_respawn', False):
        # Player is awaiting respawn - intercept their input
        from commands.combat import handle_respawn_choice

        # Get the raw input (verb or original)
        choice = cmd.get("verb") or cmd.get("original", "")
        combat_death = online_sessions.get(player_sid, {}).get('combat_death', True)

        result = await handle_respawn_choice(
            player, choice, player_sid, game_state, player_manager,
            online_sessions, sio, utils, combat_death=combat_death
        )

        # If result is None, player chose to disconnect
        if result is None:
            return "quit"

        return result

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
    # Check if player is in combat
    from commands.combat import is_in_combat
    if is_in_combat(player.name):
        return "You can't move while in combat! Use 'flee <direction>' to escape."

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

        # Check for aggressive mobs in the new room and trigger immediate attack if needed
        mob_manager = getattr(utils, 'mob_manager', None) if hasattr(utils, '__dict__') else None
        if mob_manager:
            mobs_in_room = mob_manager.get_mobs_in_room(new_room_id)
            for mob in mobs_in_room:
                if mob.can_attack_player():
                    # Found an aggressive mob - initiate combat
                    from commands.combat import mob_initiate_attack, is_in_combat
                    # Only attack if not already in combat
                    if not is_in_combat(player.name) and not is_in_combat(mob.id):
                        player_sid = None
                        for sid, session_data in online_sessions.items():
                            if session_data.get('player') == player:
                                player_sid = sid
                                break
                        if player_sid:
                            await mob_initiate_attack(mob, player, player_sid, player_manager, game_state, online_sessions, sio, utils)
                            break  # Only one mob attacks at a time

        return build_look_description(player, game_state, online_sessions, mob_manager=mob_manager)
    else:
        return "You can't go that way."

def build_look_description(player, game_state, online_sessions=None, look=False, mob_manager=None):
    """Build a description of the current room (including mobs)."""
    # This function remains largely unchanged
    current_room = game_state.get_room(player.current_room)

    # Build the room description
    room_desc = f"{current_room.name}"

    if current_room.room_id not in player.visited or look:
        room_desc += f"\n{current_room.description}"
        player.visited.add(current_room.room_id)

    # Get all visible items (excluding mobs - they're listed separately)
    visible_items = current_room.get_items(game_state)

    # Filter out mobs from items (mobs are StatefulItems but we list them separately)
    from models.Mobile import Mobile
    non_mob_items = [item for item in visible_items if not isinstance(item, Mobile)]

    # List items in the room
    if non_mob_items:
        items_desc = []
        for item in non_mob_items:
            items_desc.append(item.description)
        if items_desc:
            room_desc += "\n" + "\n".join(items_desc)

    # List mobs in the room
    if mob_manager:
        mobs_in_room = mob_manager.get_mobs_in_room(current_room.room_id)
        if mobs_in_room:
            for mob in mobs_in_room:
                # Check if mob is in combat
                from commands.combat import is_in_combat
                combat_status = " (in combat)" if is_in_combat(mob.id) else ""
                room_desc += f"\n{mob.description}{combat_status}"
    
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