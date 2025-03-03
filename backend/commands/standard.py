# backend/commands/standard.py

from commands.registry import command_registry
from commands.executor import build_look_description
from models.levels import levels

# ===== LOOK COMMAND =====
async def handle_look(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'look' command."""
    subject = cmd.get("subject")
    
    # If no subject, look at the room
    if not subject:
        return build_look_description(player, game_state, online_sessions)
    
    # Look at a specific item in inventory
    for item in player.inventory:
        if subject.lower() in item.name.lower():
            return f"{item.name}: {item.description}"
    
    # Look at a specific item in the room
    current_room = game_state.get_room(player.current_room)
    for item in current_room.items:
        if subject.lower() in item.name.lower():
            return f"{item.name}: {item.description}"
    
    # Look in a specific direction
    if subject in current_room.exits:
        next_room_id = current_room.exits[subject]
        next_room = game_state.get_room(next_room_id)
        return f"Looking {subject}: {next_room.name}"
    
    return f"You don't see '{subject}' here."


# ===== INVENTORY COMMAND =====
async def handle_inventory(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'inventory' command."""
    if not player.inventory:
        return "You aren't carrying anything!"
    
    return_str = "You are currently holding the following:\n"
    return_str += " ".join([item.name for item in player.inventory])
    return return_str


# ===== EXITS COMMAND =====
async def handle_exits(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'exits' command."""
    current_room = game_state.get_room(player.current_room)
    exit_list = []
    for direction, dest_room_id in current_room.exits.items():
        dest_room = game_state.get_room(dest_room_id)
        dest_name = dest_room.name if dest_room else "Unknown"
        exit_list.append(f"{direction}: {dest_name}")
    if exit_list == []:
        return "No exits from here."
    return "\n".join(sorted(exit_list))


# ===== GET/TAKE COMMAND =====
async def handle_get(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'get' command."""
    subject = cmd.get("subject")
    current_room = game_state.get_room(player.current_room)
    
    if not subject:
        return "Specify the item to take (e.g., 'get sword' or 'get all')."
    
    if subject.lower() == "all":
        picked_up = []
        for item in list(current_room.items):
            success, message = player.add_item(item)
            if success:
                current_room.remove_item(item)
                picked_up.append(item.name)
        return f"Picked up: {', '.join(picked_up)}." if picked_up else "Couldn't pick up anything."
    
    if subject.lower() == "treasure" or subject.lower() == "t":
        picked_up = []
        for item in list(current_room.items):
            if hasattr(item, 'value') and item.value > 0:
                success, message = player.add_item(item)
                if success:
                    current_room.remove_item(item)
                    picked_up.append(item.name)
        return f"Treasure picked up: {', '.join(picked_up)}." if picked_up else "No treasure items available."
    
    # Look for a matching item in the room
    found_item = None
    for item in current_room.items:
        if subject.lower() in item.name.lower():
            found_item = item
            break
    
    if found_item:
        success, message = player.add_item(found_item)
        if success:
            current_room.remove_item(found_item)
        return message
    
    return f"You don't see '{subject}' here."


# ===== DROP COMMAND =====
async def handle_drop(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'drop' command."""
    subject = cmd.get("subject")
    current_room = game_state.get_room(player.current_room)
    
    if not subject:
        return "Specify the item to drop (e.g., 'drop shield' or 'drop all')."
    
    if subject.lower() == "all" or subject.lower() == "everything":
        dropped_items = list(player.inventory)
        if dropped_items:
            for item in dropped_items:
                player.remove_item(item)
                current_room.add_item(item)
            game_state.save_rooms()  # Save room state after changing items
            return f"Dropped all items: {', '.join(i.name for i in dropped_items)}."
        else:
            return "You aren't carrying anything."
    
    if subject.lower() == "treasure" or subject.lower() == "t":
        dropped_items = [i for i in player.inventory if hasattr(i, 'value') and i.value > 0]
        if dropped_items:
            for i in dropped_items:
                player.remove_item(i)
                current_room.add_item(i)
            game_state.save_rooms()  # Save room state after changing items
            
            # Check if this is the swamp for point gain
            if "swamp" in current_room.name.lower() or "swamp" in current_room.description.lower():
                total_value = sum(i.value for i in dropped_items)
                player.add_points(total_value)
                player_manager.save_players()  # Save player state after gaining points
                return f"You swamp treasure worth {total_value} points! New score: {player.points}"
            
            return f"Dropped all treasure: {', '.join(i.name for i in dropped_items)}."
        else:
            return "You have no treasure items to drop."
    
    # Look for a matching item in inventory
    found_item = None
    for item in player.inventory:
        if subject.lower() in item.name.lower():
            found_item = item
            break
    
    if found_item:
        success, message = player.remove_item(found_item)
        if success:
            current_room.add_item(found_item)
            game_state.save_rooms()  # Save room state after changing items
            
            # Check if this is the swamp for point gain
            if hasattr(found_item, 'value') and found_item.value > 0:
                if "swamp" in current_room.name.lower() or "swamp" in current_room.description.lower():
                    player.add_points(found_item.value)
                    player_manager.save_players()  # Save player state after gaining points
                    return f"You swamp {found_item.name} for {found_item.value} points! New score: {player.points}"
        
        return message
    
    return f"You don't have '{subject}' in your inventory."


# ===== SCORE COMMAND =====
async def handle_score(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'score' command."""
    return (f"Score: {player.points} points\n"
            f"Level: {player.level}\n"
            f"Stamina: {player.stamina}/{player.max_stamina}\n"
            f"Strength: {player.strength}\n"
            f"Dexterity: {player.dexterity}\n"
            f"Carrying capacity: {len(player.inventory)}/{player.carrying_capacity_num} items")


# ===== HELP COMMAND =====
async def handle_help(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'help' command."""
    subject = cmd.get("subject")
    
    # If a specific command was requested
    if subject:
        return command_registry.get_help(subject)
    
    # General help
    help_text = (
        "Commands:\n"
        "  shout <message>       - Broadcasts a global shout.\n"
        "  \"<message>           - Sends a message to everyone in your current room.\n"
        "  <recipient> <msg>     - Sends a private message to a specific player.\n"
        "  users                 - Lists online users.\n"
        "  help [<topic>]        - Displays this help information.\n"
        "  info                  - Provides information about the game and its objectives.\n"
        "  <direction>           - Move in a specific direction (n, s, e, w, north, south, etc).\n"
        "  look [<item/direction>] - Describes your current location or examines something.\n"
        "  get <item>            - Pick up an item (also: g).\n"
        "  drop <item>           - Drop an item from your inventory (also: dr).\n"
        "  inventory             - Lists items in your inventory (also: i, inv).\n"
        "  exits                 - Lists available exits (also: x).\n"
        "  score                 - Shows your current score and stats (also: sc).\n"
        "  levels                - Shows the levels of experience\n"
        "  qq                    - Exit the game (two letters to avoid accidental quits).\n"
    )
    return help_text


# ===== INFO COMMAND =====
async def handle_info(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'info' command."""
    info_text = (
        "AI MUD: A text-based multiplayer adventure where you explore, solve puzzles, "
        "and earn treasure.\n\n"
        "Objective: Gain points by swamping treasure, solving puzzles, and leveling up your character.\n\n"
        "Explore the village, discover mysterious doors to AI-generated zones, and face various challenges.\n\n"
        "Player progress (levels and points) persists across weekly resets, while the world resets.\n\n"
        "Command format: <verb> <subject> WITH <object>\n"
        "For example: 'use key with door', 'attack troll with sword'\n\n"
        "The game understands abbreviations like 'n' for 'north', 'g' for 'get', etc.\n"
        "It also tracks pronouns like IT, HIM, HER, THEM for easier command entry.\n\n"
        "Type 'help' for a list of available commands."
    )
    return info_text

# ===== LEVELS COMMAND =====
async def handle_levels(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    return_str = "Levels of experience in Forgotten Realms:\n"
    # Header row with fixed width for each column
    return_str += f"{'Level':<10}{'Points':<15}\n"
    
    # Iterate over the points in sorted order and assign a numerical level
    for idx, points in enumerate(sorted(levels.keys()), start=1):
        details = levels[points]
        return_str += f"{idx:<10}{points:<15}{details['name']:<25}\n"
        
    return return_str



# ===== USERS COMMAND =====
async def handle_users(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'users' command."""
    if not online_sessions:
        return "How is this possible?"
    
    user_list = []
    for sid, session_data in online_sessions.items():
        other_player = session_data.get('player')
        if other_player:
            user_list.append(f"{other_player.name} the {other_player.level}")
    
    return "\n".join(f"{user} is playing" for user in user_list)


# ===== QUIT COMMAND =====
async def handle_quit(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle the 'quit' command."""
    return "quit"


# Register standard commands
command_registry.register("look", handle_look, "Describes your current location or an object.")
command_registry.register("inventory", handle_inventory, "Lists items in your inventory.")
command_registry.register("exits", handle_exits, "Lists available exits from your current location.")
command_registry.register("get", handle_get, "Pick up an item from your surroundings.")
command_registry.register("drop", handle_drop, "Drop an item from your inventory.")
command_registry.register("score", handle_score, "Shows your current score and stats.")
command_registry.register("help", handle_help, "Provides help on commands.")
command_registry.register("info", handle_info, "Provides information about the game and its objectives.")
command_registry.register("users", handle_users, "Lists online users.")
command_registry.register("quit", handle_quit, "Exit the game.")
command_registry.register("levels", handle_levels, "Lists levels of experience.")

# Register aliases
command_registry.register_alias("l", "look")
command_registry.register_alias("i", "inventory")
command_registry.register_alias("inv", "inventory")
command_registry.register_alias("g", "get")
command_registry.register_alias("take", "get")
command_registry.register_alias("pickup", "get")
command_registry.register_alias("dr", "drop")
command_registry.register_alias("sc", "score")
command_registry.register_alias("x", "exits")
command_registry.register_alias("qq", "quit")  # Changed from "exit" to "qq"
command_registry.register_alias("who", "users")