# backend/commands/standard.py

from commands.registry import command_registry
from commands.executor import build_look_description
from models.Levels import levels
from models.ContainerItem import ContainerItem
from commands.utils import get_player_inventory

# ===== LOOK COMMAND =====
async def handle_look(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'look' command."""
    subject = cmd.get("subject")
    
    # If no subject, look at the room
    if not subject:
        return build_look_description(player, game_state, online_sessions, look=True)
    
    # Look at a specific item in inventory
    for item in player.inventory:
        if subject.lower() in item.name.lower():
            return f"{item.description}"
    
    # Look at a specific item in the room - UPDATE THIS PART
    current_room = game_state.get_room(player.current_room)
    all_visible_items = current_room.get_items(game_state)  # Get visible items including hidden ones
    for item in all_visible_items:
        if subject.lower() in item.name.lower():
            return f"{item.name}: {item.description}"
    
    return f"You don't see '{subject}' here."


# ===== INVENTORY COMMAND =====
async def handle_inventory(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'inventory' command."""
    if not player.inventory:
        return "You aren't carrying anything!"
    
    return_str = "You are currently holding the following:\n"
    return_str += get_player_inventory(player)
    return return_str


# ===== EXITS COMMAND =====
async def handle_exits(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'exits' command."""
    current_room = game_state.get_room(player.current_room)
    if not current_room.exits:
        return "No exits from here."
    
    # Determine the maximum length of the direction strings
    max_length = max(len(direction) for direction in current_room.exits)
    
    exit_list = []
    for direction, dest_room_id in current_room.exits.items():
        dest_room = game_state.get_room(dest_room_id)
        dest_name = dest_room.name if dest_room else "Unknown"
        # Format with left-aligned direction so all room names start in the same column
        exit_list.append(f"{direction:<{max_length}}       {dest_name}")
    
    return "\n".join(sorted(exit_list))


# ===== GET/TAKE COMMAND =====
# Update to commands/standard.py - handle_get function

async def handle_get(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'get' command."""
    subject = cmd.get("subject")
    current_room = game_state.get_room(player.current_room)
    
    # Handle get from container
    if cmd.get("from_container") or (cmd.get("instrument") and "from" in cmd.get("original").lower()):
        container_name = cmd.get("instrument")
        
        # Check if we have this container in inventory
        container = None
        for item in player.inventory:
            if container_name.lower() in item.name.lower() and isinstance(item, ContainerItem):
                container = item
                break
                
        if not container:
            return f"You don't have a container called '{container_name}' in your inventory."
            
        # Check if container is open
        if container.state != "open":
            return f"The {container.name} is closed. You need to open it first."
            
        # Find the item in the container
        item_to_get = None
        for item in container.items:
            if subject.lower() in item.name.lower():
                item_to_get = item
                break
                
        if not item_to_get:
            return f"There is no '{subject}' in the {container.name}."
            
        # Add the item to player's inventory
        success, message = player.add_item(item_to_get)
        if success:
            container.remove_item(item_to_get.id)
            player_manager.save_players()  # Save player state after changing inventory
            return f"{item_to_get.name} removed from {container.name}."
        else:
            return message
    
    # Regular get command continues here
    if not subject:
        return "Specify the item to take (e.g., 'get sword' or 'get all')."
    
    if subject.lower() == "all":
        picked_up = []
        all_visible_items = current_room.get_items(game_state)  # Get visible items including hidden ones
        for item in list(all_visible_items):
            success, message = player.add_item(item)
            if success:
                current_room.remove_item(item)  # This removes from visible items
                # Also remove from hidden_items if it's there
                if hasattr(item, 'id') and item.id in current_room.hidden_items:
                    current_room.remove_hidden_item(item.id)
                picked_up.append(item.name)
        return f"Picked up: {', '.join(picked_up)}." if picked_up else "Nothing to pick up."
    
    if subject.lower() == "treasure" or subject.lower() == "t":
        picked_up = []
        all_visible_items = current_room.get_items(game_state)  # Get visible items including hidden ones
        for item in list(all_visible_items):
            if hasattr(item, 'value') and item.value > 0:
                success, message = player.add_item(item)
                if success:
                    current_room.remove_item(item)
                    # Also remove from hidden_items if it's there
                    if hasattr(item, 'id') and item.id in current_room.hidden_items:
                        current_room.remove_hidden_item(item.id)
                    picked_up.append(item.name)
        return f"Treasure picked up: {', '.join(picked_up)}." if picked_up else "No treasure available."
    
    # Look for a matching item in the room
    found_item = None
    all_visible_items = current_room.get_items(game_state)  # Get visible items including hidden ones
    for item in all_visible_items:
        if subject.lower() in item.name.lower():
            found_item = item
            break
    
    if found_item:
        success, message = player.add_item(found_item)
        if success:
            current_room.remove_item(found_item)
            # Also remove from hidden_items if it's there
            if hasattr(found_item, 'id') and found_item.id in current_room.hidden_items:
                current_room.remove_hidden_item(found_item.id)
        return message
    
    return f"You don't see '{subject}' here."


# ===== DROP COMMAND =====
async def handle_drop(cmd, player, game_state, player_manager, online_sessions, sio, utils):
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
            # game_state.save_rooms()  # Save room state after changing items
            return f"Dropped all items: {', '.join(i.name for i in dropped_items)}."
        else:
            return "You aren't carrying anything."
    
    if subject.lower() == "treasure" or subject.lower() == "t":
        dropped_items = [i for i in player.inventory if hasattr(i, 'value') and i.value > 0]
        if dropped_items:
            for i in dropped_items:
                player.remove_item(i)
                current_room.add_item(i)
            # game_state.save_rooms()  # Save room state after changing items
            
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
            # game_state.save_rooms()  # Save room state after changing items
            
            # Check if this is the swamp for point gain
            if hasattr(found_item, 'value') and found_item.value > 0:
                if "swamp" in current_room.name.lower() or "swamp" in current_room.description.lower():
                    player.add_points(found_item.value)
                    player_manager.save_players()  # Save player state after gaining points
                    return f"You swamp {found_item.name} for {found_item.value} points! New score: {player.points}"
        
        return message
    
    return f"You don't have '{subject}' in your inventory."


# ===== SCORE COMMAND =====
async def handle_score(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'score' command."""
    return (f"Score: {player.points} points\n"
            f"Level: {player.level}\n"
            f"Stamina: {player.stamina}/{player.max_stamina}\n"
            f"Strength: {player.strength}\n"
            f"Dexterity: {player.dexterity}\n"
            f"Carrying capacity: {len(player.inventory)}/{player.carrying_capacity_num} items")


# ===== HELP COMMAND =====
async def handle_help(cmd, player, game_state, player_manager, online_sessions, sio, utils):
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
        "  look [<item>]         - Describes your current location or examines something.\n"
        "  get <item>            - Pick up an item (also: g).\n"
        "  open <container>      - Open a container.\n"
        "  close <container>     - Close a container.\n"
        "  drop <item>           - Drop an item from your inventory (also: dr).\n"
        "  inventory             - Lists items in your inventory (also: i, inv).\n"
        "  exits                 - Lists available exits (also: x).\n"
        "  score                 - Shows your current score and stats (also: sc).\n"
        "  levels                - Shows the levels of experience\n"
        "  qq                    - Exit the game (two letters to avoid accidental quits).\n"
    )
    return help_text


# ===== INFO COMMAND =====
async def handle_info(cmd, player, game_state, player_manager, online_sessions, sio, utils):
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
async def handle_levels(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    return_str = "Levels of experience in Forgotten Realms:\n"
    # Header row with fixed width for each column
    return_str += f"{'Level':<10}{'Points':<15}\n"
    
    # Iterate over the points in sorted order and assign a numerical level
    for idx, points in enumerate(sorted(levels.keys()), start=1):
        details = levels[points]
        return_str += f"{idx:<10}{points:<15}{details['name']:<25}\n"
        
    return return_str



# ===== USERS COMMAND =====
async def handle_users(cmd, player, game_state, player_manager, online_sessions, sio, utils):
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
async def handle_quit(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'quit' command."""
    return "quit"


# Register standard commands
command_registry.register("look", handle_look, "Describes your current location or an object.")
command_registry.register("inventory", handle_inventory, "Lists items in your inventory.")
command_registry.register("exits", handle_exits, "Lists available exits from your current location.")
command_registry.register("get", handle_get, "Pick up an item from your surroundings or from a container.")
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


# Add this to commands/standard.py

async def handle_diagnostic(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Debug command to print information about items in the room."""
    import json
    
    subject = cmd.get("subject")
    current_room = game_state.get_room(player.current_room)
    
    result = f"=== DIAGNOSTIC INFO ===\n"
    result += f"Current room: {current_room.room_id} ({current_room.name})\n"
    result += f"Visible items: {len(current_room.items)}\n"
    
    # List all items in the room
    result += "\nROOM ITEMS:\n"
    for item in current_room.items:
        result += f"- {item.name} (ID: {getattr(item, 'id', 'unknown')})\n"
        
        # Check if it's a StatefulItem
        if hasattr(item, 'state'):
            result += f"  State: {item.state}\n"
            
        # Check for interactions
        if hasattr(item, 'interactions'):
            result += f"  Has interactions: YES\n"
            result += f"  Verbs: {list(item.interactions.keys())}\n"
            
            # Check structure of interaction lists
            for verb, interactions in item.interactions.items():
                result += f"  Verb: {verb}\n"
                if isinstance(interactions, list):
                    result += f"    Is a list: YES\n"
                    result += f"    Number of interactions: {len(interactions)}\n"
                    for i, inter in enumerate(interactions):
                        result += f"    Interaction {i}:\n"
                        if isinstance(inter, dict):
                            result += f"      Is a dictionary: YES\n"
                            result += f"      Keys: {list(inter.keys())}\n"
                        else:
                            result += f"      Is a dictionary: NO - TYPE: {type(inter)}\n"
                else:
                    result += f"    Is a list: NO - TYPE: {type(interactions)}\n"
        else:
            result += f"  Has interactions: NO\n"
    
    # Check inventory items
    result += "\nINVENTORY ITEMS:\n"
    for item in player.inventory:
        result += f"- {item.name} (ID: {getattr(item, 'id', 'unknown')})\n"
        
        # Check if it's a container
        if hasattr(item, 'items'):
            result += f"  Is container: YES\n"
            result += f"  Container state: {getattr(item, 'state', 'unknown')}\n"
            result += f"  Contains: {len(item.items)} items\n"
            
            # Check for interactions
            if hasattr(item, 'interactions'):
                result += f"  Has interactions: YES\n"
                result += f"  Verbs: {list(item.interactions.keys())}\n"
                
                # Check open/close
                for verb in ['open', 'close']:
                    if verb in item.interactions:
                        result += f"  Has {verb} verb: YES\n"
                        interactions = item.interactions[verb]
                        if isinstance(interactions, list):
                            result += f"    {verb} is a list: YES\n"
                            result += f"    Number of interactions: {len(interactions)}\n"
                        else:
                            result += f"    {verb} is a list: NO - TYPE: {type(interactions)}\n"
            else:
                result += f"  Has interactions: NO\n"
    
    return result

# Add this entry:
command_registry.register("debug", handle_diagnostic, "Show diagnostic info for debugging.")