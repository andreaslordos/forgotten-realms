# backend/commands/player_interaction.py
from commands.registry import command_registry
import random
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def handle_give(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Give an item to another player in the same room.
    Syntax: give <item> to <player>
    """
    # Get the subject (target player) and instrument (item) from the parsed command
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    instrument = cmd.get("instrument")
    instrument_obj = cmd.get("instrument_object")
    
    # Check if reversed_syntax is needed (give item to player vs. give player item)
    reversed_syntax = cmd.get("reversed_syntax", False)
    
    # If reversed syntax, swap subject and instrument
    if reversed_syntax:
        temp = subject
        subject = instrument
        instrument = temp
        
        temp_obj = subject_obj
        subject_obj = instrument_obj
        instrument_obj = temp_obj
    
    logger.debug(f"Give command parsed: item={instrument}, target={subject}")
    
    if not instrument and not instrument_obj:
        return "What do you want to give?"
    
    if not subject and not subject_obj:
        return "To whom do you want to give something?"
    
    # Look for the item in the giver's inventory - prefer bound object
    item = None
    if instrument_obj and instrument_obj in player.inventory:
        item = instrument_obj
    else:
        for it in player.inventory:
            if instrument.lower() in it.name.lower():
                item = it
                break
    if not item:
        return f"You don't have '{instrument}' in your inventory."
    
    # Find the target player - prefer bound object
    target_player = None
    target_sid = None
    
    if subject_obj and hasattr(subject_obj, 'name') and hasattr(subject_obj, 'current_room'):
        if subject_obj.current_room == player.current_room:
            target_player = subject_obj
            # Find their session ID
            for sid, session in online_sessions.items():
                if session.get('player') == target_player:
                    target_sid = sid
                    break
    else:
        # Find by name
        for sid, session in online_sessions.items():
            other = session.get("player")
            if other and other.current_room == player.current_room and other != player:
                if subject.lower() in other.name.lower():
                    target_player = other
                    target_sid = sid
                    break
    
    if not target_player:
        return f"You don't see '{subject}' here."
    
    # Attempt to add the item to the target's inventory
    success, message = target_player.add_item(item)
    if not success:
        return f"{target_player.name} cannot carry '{item.name}': {message}"
    
    # Remove the item from your inventory and save the change
    player.remove_item(item)
    player_manager.save_players()
    
    # Prepare messages
    give_msg_target = f"{player.name} the {player.level} has given you the {item.name}."
    give_msg_others = f"{player.name} the {player.level} gives the {item.name} to {target_player.name} the {target_player.level}."
    
    # Send messages to target
    if target_sid and sio and utils:
        await utils.send_message(sio, target_sid, give_msg_target)
    
    # Broadcast to others in the room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == player.current_room and 
                other_player != player and 
                other_player != target_player):
                await utils.send_message(sio, sid, give_msg_others)
    
    # Return confirmation to you
    return f"{item.name} given to {target_player.name} the {target_player.level}."

async def handle_steal(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Steal an item from another player in the same room.
    Syntax: steal <item> from <player>
    """
    # Get the subject (target player) and instrument (item) from the parsed command
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    instrument = cmd.get("instrument")
    instrument_obj = cmd.get("instrument_object")
    
    logger.debug(f"Steal command parsed: subject={subject}, instrument={instrument}")
    logger.debug(f"Bound objects: subject_obj={subject_obj}, instrument_obj={instrument_obj}")
    
    # In steal command, the subject should be the player and instrument should be the item
    # But we need to check if we're parsing a 'steal item from player' format
    if cmd.get("preposition") == "from":
        # This is 'steal item from player', so we need to swap
        temp = subject
        subject = instrument 
        instrument = temp
        
        temp_obj = subject_obj
        subject_obj = instrument_obj
        instrument_obj = temp_obj
    
    if not subject and not subject_obj:
        return "Steal from whom?"
    
    if not instrument and not instrument_obj:
        return "What do you want to steal?"
    
    # Find the target player - prefer bound object
    target_player = None
    target_sid = None
    
    if subject_obj and hasattr(subject_obj, 'name') and hasattr(subject_obj, 'current_room'):
        if subject_obj.current_room == player.current_room:
            target_player = subject_obj
            # Find their session ID
            for sid, session in online_sessions.items():
                if session.get('player') == target_player:
                    target_sid = sid
                    break
    else:
        # Find by name
        for sid, session in online_sessions.items():
            other = session.get("player")
            if other and other.current_room == player.current_room and other != player:
                if subject.lower() in other.name.lower():
                    target_player = other
                    target_sid = sid
                    break
    
    if not target_player:
        return f"You don't see '{subject}' here."
    
    # Log player and target details for debugging
    logger.debug(f"Thief: {player.name} (Dex: {player.dexterity})")
    logger.debug(f"Target: {target_player.name} (Dex: {target_player.dexterity})")
    
    # Look for the item in the target's inventory - prefer bound object
    item = None
    if instrument_obj:
        for it in target_player.inventory:
            if it == instrument_obj:
                item = it
                break
    
    # If not found by object reference, search by name
    if not item:
        for it in target_player.inventory:
            if instrument.lower() in it.name.lower():
                item = it
                break
    
    if not item:
        return f"{target_player.name} doesn't have '{instrument}'."
    
    # Calculate steal chance based on ratio of dexterities
    # Chance = (your_dexterity / (your_dexterity + target_dexterity)) * 100
    total_dex = player.dexterity + target_player.dexterity
    steal_chance = (player.dexterity / total_dex) * 100 if total_dex > 0 else 50
    
    # Ensure a minimum chance of 10% and maximum of 90%
    steal_chance = max(10, min(90, steal_chance))