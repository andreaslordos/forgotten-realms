from commands.parser import parse_command, parse_item_command

def display_room(room, visited, force_describe=False):
    """
    Display the room details:
      - Always shows the room name.
      - If force_describe is True (e.g., from "look") or the room hasn't been visited
        this session, shows the full room description.
      - Lists each item in the room with its description.
    """
    print("\n" + room.name)
    if force_describe or (room.room_id not in visited):
        print(room.description)
        visited.add(room.room_id)
    for item in room.items:
        print(item.description)

def display_exits(room, game_state):
    """
    Display the exits from the current room.
    """
    exits = room.exits
    exit_list = []
    for direction, dest_room_id in exits.items():
        dest_room = game_state.get_room(dest_room_id)
        dest_name = dest_room.name if dest_room else "Unknown"
        exit_list.append((direction, dest_name))
    max_width = max((len(direction) for direction, _ in exit_list), default=0) + 2
    print("\nExits:")
    for direction, dest_name in sorted(exit_list):
        print(f"{direction:<{max_width}} {dest_name}")

def logout_player(player, game_state, player_manager):
    """
    Logs out the player by dropping all items and saving state.
    """
    current_room = game_state.get_room(player.current_room)
    if current_room:
        for item in list(player.inventory):
            player.remove_item(item)
            current_room.add_item(item)
    game_state.save_rooms()
    player_manager.save_players()
    print("\nAll items have been dropped upon logout.")

def execute_command(command, player, game_state, player_manager, visited):
    """
    Executes a single command from the player.
    Returns "quit" if the command ends the game.
    """
    command = command.strip()
    if command.lower() in ("quit", "exit"):
        logout_player(player, game_state, player_manager)
        print("Goodbye!")
        return "quit"

    elif command.lower() == "look":
        current_room = game_state.get_room(player.current_room)
        display_room(current_room, visited, force_describe=True)
        return

    elif command.lower() in ("x", "exits"):
        current_room = game_state.get_room(player.current_room)
        display_exits(current_room, game_state)
        return

    elif command.lower() in ("inv", "i", "inventory"):
        if not player.inventory:
            print("You aren't carrying anything!")
        else:
            print("You are currently holding the following:")
            for item in player.inventory:
                print(item.name)
        return

    # Try parsing item-related commands.
    action, item_name = parse_item_command(command)
    if action == "take":
        current_room = game_state.get_room(player.current_room)
        if not item_name:
            print("Specify the item to take (e.g., 'get sword' or 'g all').")
            return
        if item_name == "all":
            picked_up = []
            for item in list(current_room.items):
                success, message = player.add_item(item)
                if success:
                    current_room.remove_item(item)
                    picked_up.append(item.name)
            if picked_up:
                print(f"Picked up: {', '.join(picked_up)}.")
            else:
                print("Couldn't pick up anything.")
        elif item_name == "treasure":
            picked_up = []
            for item in list(current_room.items):
                if item.value > 0:
                    success, message = player.add_item(item)
                    if success:
                        current_room.remove_item(item)
                        picked_up.append(item.name)
            if picked_up:
                print(f"Treasure picked up: {', '.join(picked_up)}.")
            else:
                print("No treasure items available.")
        else:
            found_item = next((i for i in current_room.items if item_name in i.name.lower()), None)
            if found_item:
                success, message = player.add_item(found_item)
                if success:
                    current_room.remove_item(found_item)
                print(message)
            else:
                print("No such item found.")
        game_state.save_rooms()
        return

    elif action == "drop":
        if not item_name:
            print("Specify the item to drop (e.g., 'drop shield', 'dr all').")
            return
        current_room = game_state.get_room(player.current_room)
        if item_name == "all":
            dropped_items = list(player.inventory)
            if dropped_items:
                for item in dropped_items:
                    player.remove_item(item)
                    current_room.add_item(item)
                print(f"Dropped all items: {', '.join(i.name for i in dropped_items)}.")
            else:
                print("You aren't carrying anything.")
        elif item_name == "treasure":
            dropped_items = [i for i in player.inventory if i.value > 0]
            if dropped_items:
                for i in dropped_items:
                    player.remove_item(i)
                    current_room.add_item(i)
                print(f"Dropped all treasure: {', '.join(i.name for i in dropped_items)}.")
            else:
                print("You have no treasure items to drop.")
        else:
            found_item = next((i for i in player.inventory if item_name in i.name.lower()), None)
            if found_item:
                success, message = player.remove_item(found_item)
                if success:
                    current_room.add_item(found_item)
                print(message)
            else:
                print("You do not have that item in your inventory.")
        game_state.save_rooms()
        return

    # Handle movement commands.
    direction = parse_command(command)
    if direction:
        current_room = game_state.get_room(player.current_room)
        if direction in current_room.exits:
            new_room_id = current_room.exits[direction]
            player.set_current_room(new_room_id)
            player_manager.save_players()
            new_room = game_state.get_room(new_room_id)
            print(f"\nYou move {direction} into {new_room.name}.")
            display_room(new_room, visited)
        else:
            print("You can't go that way.")
    else:
        print("Command not recognized.")
