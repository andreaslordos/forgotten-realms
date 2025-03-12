# backend/commands/standard.py

from commands.registry import command_registry
from commands.executor import build_look_description
from models.Levels import levels
from models.ContainerItem import ContainerItem
from commands.utils import get_player_inventory
from models.SpecializedRooms import SwampRoom

# ===== LOOK COMMAND =====
async def handle_look(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'look' command."""
    # Get the subject (what to look at)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    
    # If no subject, look at the room
    if not subject and not subject_obj:
        return build_look_description(player, game_state, online_sessions, look=True)
    
    # If we have a bound object, use it directly
    if subject_obj:
        # Check if it's in inventory
        if subject_obj in player.inventory:
            return f"{subject_obj.description}"
        
        # Check if it's in the room
        current_room = game_state.get_room(player.current_room)
        if subject_obj in current_room.get_items(game_state):
            return f"{subject_obj.name}: {subject_obj.description}"
        
        # For players in the room
        if hasattr(subject_obj, 'name') and hasattr(subject_obj, 'current_room'):
            if subject_obj.current_room == player.current_room:
                return f"{subject_obj.name} the {subject_obj.level}"
    
    # Look at a specific item in inventory
    for item in player.inventory:
        if subject.lower() in item.name.lower():
            return f"{item.description}"
    
    # Look at a specific item in the room
    current_room = game_state.get_room(player.current_room)
    all_visible_items = current_room.get_items(game_state)  # Get visible items including hidden ones
    for item in all_visible_items:
        if subject.lower() in item.name.lower():
            return f"{item.name}: {item.description}"
    
    # Look at another player in the room
    for sid, session_data in online_sessions.items():
        other_player = session_data.get('player')
        if (other_player and 
            other_player.current_room == player.current_room and 
            other_player != player and
            subject.lower() in other_player.name.lower()):
            return f"{other_player.name} the {other_player.level}"
    
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
async def handle_get(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'get' command."""
    # Get the subject (item to get)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    
    # Get the instrument (possible container for get-from)
    instrument = cmd.get("instrument")
    instrument_obj = cmd.get("instrument_object")
    
    # Check for container-specific commands (get from container)
    from_container = cmd.get("from_container", False)
    if from_container or (instrument and "from" in cmd.get("preposition", "")):
        from commands.container import handle_get_from
        return await handle_get_from(cmd, player, game_state, player_manager, online_sessions, sio, utils)
    
    current_room = game_state.get_room(player.current_room)
    
    # Handle missing subject
    if not subject and not subject_obj:
        return "Specify the item to take (e.g., 'get sword' or 'get all')."
    
    # Handle "get all" command
    if subject and subject.lower() == "all":
        picked_up = []
        all_visible_items = current_room.get_items(game_state)
        for item in list(all_visible_items):
            # Skip non-takeable items
            if not item.takeable:
                continue
                
            success, message = player.add_item(item)
            if success:
                current_room.remove_item(item)
                # Also remove from hidden_items if it's there
                if hasattr(item, 'id') and item.id in current_room.hidden_items:
                    current_room.remove_hidden_item(item.id)
                picked_up.append(item.name)
        
        # Save player state
        player_manager.save_players()
        
        return '\n'.join(f'{item} taken.' for item in picked_up) if picked_up else "Nothing taken."
    
    # Handle "get treasure" command
    if subject and subject.lower() in ["treasure", "t"]:
        picked_up = []
        all_visible_items = current_room.get_items(game_state)
        for item in list(all_visible_items):
            # Skip non-takeable items
            if not item.takeable:
                continue
                
            if hasattr(item, 'value') and item.value > 0:
                success, message = player.add_item(item)
                if success:
                    current_room.remove_item(item)
                    # Also remove from hidden_items if it's there
                    if hasattr(item, 'id') and item.id in current_room.hidden_items:
                        current_room.remove_hidden_item(item.id)
                    picked_up.append(item.name)
        
        # Save player state
        player_manager.save_players()
        
        return '\n'.join(f'{item} taken.' for item in picked_up) if picked_up else "Nothing taken."
    
    # Handle getting a specific item - prefer the bound object if available
    found_item = subject_obj
    
    # If no bound object, search for the item by name
    if not found_item:
        # Look for a matching item in the room
        all_visible_items = current_room.get_items(game_state)
        for item in all_visible_items:
            if subject.lower() in item.name.lower():
                found_item = item
                break
    
    if found_item:
        # Skip non-takeable items
        if not found_item.takeable:
            return f"You can't take the {found_item.name}."
            
        success, message = player.add_item(found_item)
        if success:
            current_room.remove_item(found_item)
            # Also remove from hidden_items if it's there
            if hasattr(found_item, 'id') and found_item.id in current_room.hidden_items:
                current_room.remove_hidden_item(found_item.id)
            
            # Save player state
            player_manager.save_players()
            
        return message
    
    return f"You don't see '{subject}' here."


# ===== DROP COMMAND =====
async def handle_drop(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'drop' command."""
    # Get the subject (item to drop)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    
    # Handle missing subject
    if not subject and not subject_obj:
        return "Specify the item to drop (e.g., 'drop shield' or 'drop all')."
    
    current_room = game_state.get_room(player.current_room)
    
    # Check if room is a SwampRoom for special handling
    is_swamp_room = isinstance(current_room, SwampRoom)
    
    # Helper function to handle dropping a single item
    async def drop_single_item(item):
        player.remove_item(item)
        
        # Special handling for treasure in swamp rooms
        if is_swamp_room and hasattr(item, 'value') and item.value > 0:
            success, message = current_room.handle_treasure_drop(
                item, player, game_state, player_manager, sio, online_sessions
            )
            return message
        else:
            # Standard drop behavior
            current_room.add_item(item)
            return f"{item.name.capitalize()} dropped."
    
    # Handle "drop all" command
    if subject and subject.lower() in ["all", "everything"]:
        dropped_items = list(player.inventory)
        if not dropped_items:
            return "You aren't carrying anything."
        
        messages = []
        for item in dropped_items:
            message = await drop_single_item(item)
            messages.append(message)
        
        # Save player state
        player_manager.save_players()
        
        return "\n".join(messages)
    
    # Handle "drop treasure" command
    if subject and subject.lower() in ["treasure", "t"]:
        treasure_items = [item for item in player.inventory 
                         if hasattr(item, 'value') and item.value > 0]
        
        if not treasure_items:
            return "You have no treasure to drop."
        
        messages = []
        for item in treasure_items:
            message = await drop_single_item(item)
            messages.append(message)
        
        # Save player state
        player_manager.save_players()
        
        return "\n".join(messages)
    
    # Handle dropping a specific item - prefer the bound object if available
    item_to_drop = subject_obj if subject_obj in player.inventory else None
    
    # If no bound object, search for the item by name
    if not item_to_drop:
        for item in player.inventory:
            if subject.lower() in item.name.lower():
                item_to_drop = item
                break
    
    if item_to_drop:
        result = await drop_single_item(item_to_drop)
        
        # Save player state
        player_manager.save_players()
        
        return result
    
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
    # Get the subject (specific command to get help for)
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
        "  quit                  - Exit the game (also: qq, bye).\n"
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
        "Command format: <verb> <subject> WITH <instrument>\n"
        "For example: 'use key with door', 'attack troll with sword'\n\n"
        "The game understands abbreviations like 'n' for 'north', 'g' for 'get', etc.\n"
        "It also tracks pronouns like IT, HIM, HER, THEM for easier command entry.\n\n"
        "Type 'help' for a list of available commands."
    )
    return info_text

# ===== LEVELS COMMAND =====
async def handle_levels(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle the 'levels' command."""
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


# ===== DIAGNOSTIC COMMAND =====
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
command_registry.register("debug", handle_diagnostic, "Show diagnostic info for debugging.")

# Register aliases
command_registry.register_alias("l", "look")
command_registry.register_alias("i", "inventory")
command_registry.register_alias("inv", "inventory")
command_registry.register_alias("g", "get")
command_registry.register_alias("take", "get")
command_registry.register_alias("pickup", "get")
command_registry.register_alias("dr", "drop")
command_registry.register_alias("sc", "score")
command_registry.register_alias("qs", "score")
command_registry.register_alias("x", "exits")
command_registry.register_alias("qq", "quit")
command_registry.register_alias("bye", "quit")
command_registry.register_alias("who", "users")
command_registry.register_alias("examine", "look")