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
    # Extract item and target names from the parsed command.
    item_name = cmd.get("instrument")
    target_name = cmd.get("subject")
    
    logger.debug(f"Give command parsed: item={item_name}, target={target_name}")
    
    if not item_name or not target_name:
        return "Usage: give <item> to <player>"
    
    # Look for the item in your (the giver's) inventory.
    item = None
    for it in player.inventory:
        if item_name.lower() in it.name.lower():
            item = it
            break
    if not item:
        return f"You don't have '{item_name}' in your inventory."
    
    # Find the target player in the same room.
    target_player = None
    target_sid = None
    for sid, session in online_sessions.items():
        other = session.get("player")
        if other and other.current_room == player.current_room and other != player:
            if target_name.lower() in other.name.lower():
                target_player = other
                target_sid = sid
                break
    if not target_player:
        return f"You don't see '{target_name}' here."
    
    # Attempt to add the item to the target's inventory.
    success, message = target_player.add_item(item)
    if not success:
        return f"{target_player.name} cannot carry '{item.name}': {message}"
    
    # Remove the item from your inventory and save the change.
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
    
    # Return confirmation to you.
    return f"{item.name} given to {target_player.name} the {target_player.level}."

async def handle_steal(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Steal an item from another player in the same room.
    Syntax: steal <item> from <player>
    """
    # Log the full command details for debugging
    logger.debug(f"Full Steal Command: {cmd}")
    
    # Standard approach using the parser's output
    item_name = cmd.get("instrument")
    target_name = cmd.get("subject")
    
    logger.debug(f"Parsed item: {item_name}, Parsed target: {target_name}")
    
    if not item_name or not target_name:
        return "Usage: steal <item> from <player>"
    
    # Find the target player in the same room.
    target_player = None
    target_sid = None
    for sid, session in online_sessions.items():
        other = session.get("player")
        if other and other.current_room == player.current_room and other != player:
            if target_name.lower() in other.name.lower():
                target_player = other
                target_sid = sid
                break
    
    if not target_player:
        return f"You don't see '{target_name}' here."
    
    # Log player and target details for debugging
    logger.debug(f"Thief: {player.name} (Dex: {player.dexterity})")
    logger.debug(f"Target: {target_player.name} (Dex: {target_player.dexterity})")
    
    # Look for the item in the target's inventory.
    item = None
    for it in target_player.inventory:
        if item_name.lower() in it.name.lower():
            item = it
            break
    
    if not item:
        return f"{target_player.name} doesn't have '{item_name}'."
    
    # Calculate steal chance based on ratio of dexterities
    # Chance = (your_dexterity / (your_dexterity + target_dexterity)) * 100
    total_dex = player.dexterity + target_player.dexterity
    steal_chance = (player.dexterity / total_dex) * 100 if total_dex > 0 else 50
    
    # Ensure a minimum chance of 10% and maximum of 90%
    steal_chance = max(10, min(90, steal_chance))
    
    # Roll for steal attempt
    roll = random.randint(1, 100)
    
    if roll <= steal_chance:
        # Successful steal
        # Attempt to add the item to the stealing player's inventory
        success, message = player.add_item(item)
        if not success:
            return f"You can't carry the {item.name}: {message}"
        
        # Remove the item from target's inventory
        target_player.remove_item(item)
        player_manager.save_players()
        
        # Prepare messages
        steal_msg_target = f"{player.name} the {player.level} has stolen the {item.name} from you!"
        steal_msg_thief = f"{item.name} stolen from {target_player.name} the {target_player.level}!"
        steal_msg_others = f"{player.name} the {player.level} steals the {item.name} from {target_player.name} the {target_player.level}!"
        
        # Send messages to target
        if target_sid and sio and utils:
            await utils.send_message(sio, target_sid, steal_msg_target)
        
        # Broadcast to others in the room
        if online_sessions and sio and utils:
            for sid, session_data in online_sessions.items():
                other_player = session_data.get('player')
                if (other_player and 
                    other_player.current_room == player.current_room and 
                    other_player != player and 
                    other_player != target_player):
                    await utils.send_message(sio, sid, steal_msg_others)
        
        return steal_msg_thief
    else:
        # Failed steal attempt
        # Prepare messages
        caught_msg_thief = f"{target_player.name} the {target_player.level} discovers your attempt to steal the {item.name}!"
        caught_msg_target = f"You catch {player.name} the {player.level} trying to steal the {item.name} from you!"
        caught_msg_others = f"{player.name} the {player.level} attempted to steal from {target_player.name} the {target_player.level}!"
        
        # Send messages to target
        if target_sid and sio and utils:
            await utils.send_message(sio, target_sid, caught_msg_target)
        
        # Broadcast to others in the room
        if online_sessions and sio and utils:
            for sid, session_data in online_sessions.items():
                other_player = session_data.get('player')
                if (other_player and 
                    other_player.current_room == player.current_room and 
                    other_player != player and 
                    other_player != target_player):
                    await utils.send_message(sio, sid, caught_msg_others)
        
        return caught_msg_thief

# Register commands
command_registry.register("steal", handle_steal, "Steal an item from another player in the same room. Usage: steal <item> from <player>")

# Register commands
command_registry.register("give", handle_give, "Give an item to another player in the same room. Usage: give <item> to <player>")
