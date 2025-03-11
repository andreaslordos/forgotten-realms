# backend/commands/player_interaction.py
from commands.registry import command_registry

async def handle_give(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Give an item to another player in the same room.
    Syntax: give <item> to <player>
    """
    # Extract item and target names from the parsed command.
    item_name = cmd.get("instrument")
    target_name = cmd.get("subject")
    
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
    
    # Send a message to the target.
    if target_sid and sio and utils:
        await utils.send_message(sio, target_sid, f"{player.name} the {player.level} has given you the {item.name}.")
    
    # Return confirmation to you.
    return f"{item.name} given to {target_player.name} the {target_player.level}."

command_registry.register("give", handle_give, "Give an item to another player in the same room. Usage: give <item> to <player>")
