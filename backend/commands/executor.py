from commands.parser import parse_command, parse_item_command

def execute_command(command, player, game_state, player_manager, visited):
    """
    Process a player's command and return a string response.
    The 'visited' set is used to avoid re-describing a room when moving,
    but the "look" command should always force a full description.
    """
    command = command.strip()
    
    # Quit command:
    if command.lower() in ("quit", "exit"):
        # Perform any necessary cleanup (e.g., drop items, save state)
        # You can call your logout routines here if needed.
        return "quit"
    
    # Look command: force full description regardless of visited state.
    if command.lower() == "look":
        current_room = game_state.get_room(player.current_room)
        room_desc = f"{current_room.name}\n{current_room.description}\n"
        for item in current_room.items:
            room_desc += f"{item.description}\n"
        # Optionally, you could append a presence message here:
        # (e.g., list other players present in the room)
        return room_desc.strip()
    
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
            return_str = "You aren't carrying anything!"
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
    
    # Handle movement commands.
    direction = parse_command(command)
    if direction:
        current_room = game_state.get_room(player.current_room)
        if direction in current_room.exits:
            new_room_id = current_room.exits[direction]
            player.set_current_room(new_room_id)
            player_manager.save_players()
            new_room = game_state.get_room(new_room_id)
            msg = f"You move {direction} into {new_room.name}.\n"
            # For movement, we might want to not re-display the description if it was visited,
            # but you could always force a description. Here we force it for clarity.
            msg += f"{new_room.name}\n{new_room.description}\n"
            for item in new_room.items:
                msg += f"{item.description}\n"
            # Mark the room as visited.
            visited.add(new_room.room_id)
            return msg.strip()
        else:
            return "You can't go that way."
    
    # If command doesn't match any known command.
    return "Command not recognized."
