from commands.parser import parse_command
from services.notifications import broadcast_arrival, broadcast_departure
from commands.parser import parse_item_command
import asyncio
from globals import online_sessions

def build_look_description(player, game_state):
    current_room = game_state.get_room(player.current_room)
    
    # Build the room description.
    room_desc = f"{current_room.name}\n{current_room.description}\n"
    
    # List items in the room, each on a new line.
    if current_room.items:
        for item in current_room.items:
            room_desc += f"{item.name}: {item.description}\n"
    
    # List other players present in the room, with a brief summary of their inventory.
    players_here = []
    for sid, session_data in online_sessions.items():
        other_player = session_data['player']
        if other_player.current_room == current_room.room_id and other_player != player:
            inv_summary = ", ".join(item.name for item in other_player.inventory) if other_player.inventory else "nothing"
            players_here.append(f"{other_player.name} is here, carrying {inv_summary}")
    
    if players_here:
        room_desc += "\n" + "\n".join(players_here)
    
    return room_desc.strip()

def execute_command(command, player, game_state, player_manager, visited):
    command = command.strip()
    
    # Quit command:
    if command.lower() in ("quit", "exit"):
        return "quit"
    
    # Movement command handling.
    direction = parse_command(command)
    if direction:
        old_room = game_state.get_room(player.current_room)
        if direction in old_room.exits:
            new_room_id = old_room.exits[direction]
            
            # Notify departure from the old room.
            asyncio.create_task(broadcast_departure(old_room.room_id, player))
            
            # Update player's room.
            player.set_current_room(new_room_id)
            player_manager.save_players()
            
            new_room = game_state.get_room(new_room_id)
            
            # Notify arrival in the new room.
            asyncio.create_task(broadcast_arrival(player))
            
            # Use build_look_description to include other players immediately.
            visited.add(new_room.room_id)
            return build_look_description(player, game_state)
        else:
            return "You can't go that way."
    
    # Handle "look" command.
    if command.lower() in ("look", "*look"):
        return build_look_description(player, game_state)
    
    # Handle exits command.
    if command.lower() in ("x", "exits"):
        current_room = game_state.get_room(player.current_room)
        exit_list = []
        for direction, dest_room_id in current_room.exits.items():
            dest_room = game_state.get_room(dest_room_id)
            dest_name = dest_room.name if dest_room else "Unknown"
            exit_list.append(f"{direction}: {dest_name}")
        return "Exits:\n" + "\n".join(sorted(exit_list))
    
    if command.lower() in ("inv", "i", "inventory"):
        if not player.inventory:
            return "You aren't carrying anything!"
        else:
            return_str = "You are currently holding the following: "
            for item in player.inventory:
                return_str += f"{item.name}, "
            return return_str
    
    # Handle item commands (take/get and drop).
    action, item_name = parse_item_command(command)
    if action == "take":
        current_room = game_state.get_room(player.current_room)
        if not item_name:
            return "Specify the item to take (e.g., 'get sword' or 'g all')."
        if item_name == "all":
            picked_up = []
            for item in list(current_room.items):
                success, message = player.add_item(item)
                if success:
                    current_room.remove_item(item)
                    picked_up.append(item.name)
            return f"Picked up: {', '.join(picked_up)}." if picked_up else "Couldn't pick up anything."
        elif item_name == "treasure":
            picked_up = []
            for item in list(current_room.items):
                if item.value > 0:
                    success, message = player.add_item(item)
                    if success:
                        current_room.remove_item(item)
                        picked_up.append(item.name)
            return f"Treasure picked up: {', '.join(picked_up)}." if picked_up else "No treasure items available."
        else:
            found_item = next((i for i in current_room.items if item_name in i.name.lower()), None)
            if found_item:
                success, message = player.add_item(found_item)
                if success:
                    current_room.remove_item(found_item)
                return message
            else:
                return "No such item found."
    
    elif action == "drop":
        current_room = game_state.get_room(player.current_room)
        if not item_name:
            return "Specify the item to drop (e.g., 'drop shield' or 'dr all')."
        if item_name == "all":
            dropped_items = list(player.inventory)
            if dropped_items:
                for item in dropped_items:
                    player.remove_item(item)
                    current_room.add_item(item)
                return f"Dropped all items: {', '.join(i.name for i in dropped_items)}."
            else:
                return "You aren't carrying anything."
        elif item_name == "treasure":
            dropped_items = [i for i in player.inventory if i.value > 0]
            if dropped_items:
                for i in dropped_items:
                    player.remove_item(i)
                    current_room.add_item(i)
                return f"Dropped all treasure: {', '.join(i.name for i in dropped_items)}."
            else:
                return "You have no treasure items to drop."
        else:
            found_item = next((i for i in player.inventory if item_name in i.name.lower()), None)
            if found_item:
                success, message = player.remove_item(found_item)
                if success:
                    current_room.add_item(found_item)
                return message
            else:
                return "You do not have that item in your inventory."
    
    return "Command not recognized."
