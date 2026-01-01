# backend/commands/standard.py

from typing import Dict, Any, cast
from commands.registry import command_registry
from commands.executor import build_look_description
from models.Levels import levels
from commands.utils import get_player_inventory
from models.SpecializedRooms import SwampRoom
from services.notifications import broadcast_item_drop
from services.invisibility_service import is_invisible


# ===== LOOK COMMAND =====
async def handle_look(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Handle the 'look' command."""
    # Check if player is BLIND
    from services.affliction_service import find_player_sid, has_affliction

    player_sid = find_player_sid(player, online_sessions)
    if player_sid:
        session = online_sessions.get(player_sid, {})
        if has_affliction(session, "blind"):
            return "You are blinded and cannot see anything!"

    # Get the subject (what to look at)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")

    # If no subject, look at the room
    if not subject and not subject_obj:
        mob_manager = (
            getattr(utils, "mob_manager", None)
            if utils and hasattr(utils, "__dict__")
            else None
        )
        return build_look_description(
            player, game_state, online_sessions, look=True, mob_manager=mob_manager
        )

    # If we have a bound object, use it directly
    if subject_obj:
        # Check for custom "examine" or "look" interaction first
        if hasattr(subject_obj, "interactions") and isinstance(
            subject_obj.interactions, dict
        ):
            verb = cmd.get("verb", "look")
            # Check for examine interaction, then look interaction
            for interaction_verb in [verb, "examine", "look"]:
                if interaction_verb in subject_obj.interactions:
                    interactions = subject_obj.interactions[interaction_verb]
                    if not isinstance(interactions, list):
                        interactions = [interactions]
                    for interaction in interactions:
                        if isinstance(interaction, dict) and "message" in interaction:
                            # Check state requirement if present
                            if "from_state" in interaction:
                                from_state = interaction["from_state"]
                                if (
                                    from_state is not None
                                    and from_state != subject_obj.state
                                ):
                                    continue
                            return str(interaction["message"])
                    break

        # Check if it's in inventory
        if subject_obj in player.inventory:
            return f"{subject_obj.description}"

        # Check if it's in the room
        current_room = game_state.get_room(player.current_room)
        if subject_obj in current_room.get_items(game_state):
            return f"{subject_obj.name}: {subject_obj.description}"

        # For players in the room
        if hasattr(subject_obj, "name") and hasattr(subject_obj, "current_room"):
            if subject_obj.current_room == player.current_room:
                return f"{subject_obj.name} the {subject_obj.level}"

    # Look at a specific item in inventory
    for item in player.inventory:
        if subject and hasattr(item, "matches_name") and item.matches_name(subject):
            # Check for custom interaction first
            if hasattr(item, "interactions") and isinstance(item.interactions, dict):
                verb = cmd.get("verb", "look")
                for interaction_verb in [verb, "examine", "look"]:
                    if interaction_verb in item.interactions:
                        interactions = item.interactions[interaction_verb]
                        if not isinstance(interactions, list):
                            interactions = [interactions]
                        for interaction in interactions:
                            if (
                                isinstance(interaction, dict)
                                and "message" in interaction
                            ):
                                if "from_state" in interaction:
                                    from_state = interaction["from_state"]
                                    if (
                                        from_state is not None
                                        and from_state != item.state
                                    ):
                                        continue
                                return str(interaction["message"])
                        break
            return f"{item.description}"

    # Look at a specific item in the room
    current_room = game_state.get_room(player.current_room)
    all_visible_items = current_room.get_items(
        game_state
    )  # Get visible items including hidden ones
    for item in all_visible_items:
        if subject and hasattr(item, "matches_name") and item.matches_name(subject):
            # Check for custom interaction first
            if hasattr(item, "interactions") and isinstance(item.interactions, dict):
                verb = cmd.get("verb", "look")
                for interaction_verb in [verb, "examine", "look"]:
                    if interaction_verb in item.interactions:
                        interactions = item.interactions[interaction_verb]
                        if not isinstance(interactions, list):
                            interactions = [interactions]
                        for interaction in interactions:
                            if (
                                isinstance(interaction, dict)
                                and "message" in interaction
                            ):
                                if "from_state" in interaction:
                                    from_state = interaction["from_state"]
                                    if (
                                        from_state is not None
                                        and from_state != item.state
                                    ):
                                        continue
                                return str(interaction["message"])
                        break
            return f"{item.name}: {item.description}"

    # Look at another player in the room
    for sid, session_data in online_sessions.items():
        other_player = session_data.get("player")
        if (
            other_player
            and other_player.current_room == player.current_room
            and other_player != player
            and subject
            and subject.lower() in other_player.name.lower()
        ):
            return f"{other_player.name} the {other_player.level}"

    return f"You don't see '{subject}' here."


# ===== INVENTORY COMMAND =====
async def handle_inventory(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Handle the 'inventory' command."""
    if not player.inventory:
        return "You aren't carrying anything!"

    return_str = "You are currently holding the following:\n"
    return_str += get_player_inventory(player)
    return return_str


# ===== EXITS COMMAND =====
async def handle_exits(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Handle the 'exits' command."""
    from commands.darkness_utils import room_is_visible

    current_room = game_state.get_room(player.current_room)
    if not current_room.exits:
        return "No exits from here."
    if not room_is_visible(current_room, online_sessions, game_state):
        return "It's too dark to see any exits."

    # Check for swamp direction (virtual exit for outdoor rooms)
    swamp_dir = getattr(current_room, "swamp_direction", None)
    has_swamp = (
        getattr(current_room, "is_outdoor", False)
        and current_room.room_id != "lake"
        and swamp_dir is not None
    )

    # Determine the maximum length of the direction strings
    all_directions = list(current_room.exits.keys())
    if has_swamp:
        all_directions.append("swamp")
    max_length = max(len(direction) for direction in all_directions)

    exit_list = []
    for direction, dest_room_id in current_room.exits.items():
        dest_room = game_state.get_room(dest_room_id)
        dest_name = dest_room.name if dest_room else "Unknown"
        # Format with left-aligned direction so all room names start in the same column
        exit_list.append(f"{direction:<{max_length}}       {dest_name}")

    # Add swamp as a virtual exit for outdoor rooms
    if has_swamp and swamp_dir:
        next_room = game_state.get_room(current_room.exits.get(swamp_dir, ""))
        next_name = next_room.name if next_room else "Unknown"
        exit_list.append(f"{'swamp':<{max_length}}       {next_name}")

    return "\n".join(sorted(exit_list))


# ===== GET/TAKE COMMAND =====
async def handle_get(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Handle the 'get' command."""
    # Get the subject (item to get)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")

    # Get the instrument (possible container for get-from)
    instrument = cmd.get("instrument")

    # Check for container-specific commands (get from container)
    from_container = cmd.get("from_container", False)
    if from_container or (instrument and "from" in cmd.get("preposition", "")):
        from commands.container import handle_get_from

        return await handle_get_from(
            cmd, player, game_state, player_manager, online_sessions, sio, utils
        )

    current_room = game_state.get_room(player.current_room)

    # Handle missing subject
    if not subject and not subject_obj:
        return "Specify the item to take (e.g., 'get sword' or 'get all')."

    # Handle "get all" command
    if subject and subject.lower() == "all":
        picked_up = []
        failure_reason = None
        all_visible_items = current_room.get_items(game_state)
        for item in list(all_visible_items):
            # Skip non-takeable items
            if not item.takeable:
                continue

            success, message = player.add_item(item)
            if success:
                current_room.remove_item(item)
                # Also remove from hidden_items if it's there
                if hasattr(item, "id") and item.id in current_room.hidden_items:
                    current_room.remove_hidden_item(item.id)
                picked_up.append(item.name)
            else:
                # Track the first failure reason to report to user
                if failure_reason is None:
                    failure_reason = str(message)

        # Save player state
        player_manager.save_players()

        if picked_up:
            return "\n".join(f"{item} taken." for item in picked_up)
        elif failure_reason:
            return failure_reason
        else:
            return "Nothing to take."

    # Handle "get treasure" command
    if subject and subject.lower() in ["treasure", "t"]:
        picked_up = []
        failure_reason = None
        all_visible_items = current_room.get_items(game_state)
        for item in list(all_visible_items):
            # Skip non-takeable items
            if not item.takeable:
                continue

            if hasattr(item, "value") and item.value > 0:
                success, message = player.add_item(item)
                if success:
                    current_room.remove_item(item)
                    # Also remove from hidden_items if it's there
                    if hasattr(item, "id") and item.id in current_room.hidden_items:
                        current_room.remove_hidden_item(item.id)
                    picked_up.append(item.name)
                else:
                    # Track the first failure reason to report to user
                    if failure_reason is None:
                        failure_reason = str(message)

        # Save player state
        player_manager.save_players()

        if picked_up:
            return "\n".join(f"{item} taken." for item in picked_up)
        elif failure_reason:
            return failure_reason
        else:
            return "No treasure to take."

    # Handle getting a specific item - prefer the bound object if available
    found_item = subject_obj

    # Check if the found item is from inventory rather than the room
    if found_item in player.inventory:
        # The parser bound to an item in inventory, but we need an item from the room
        found_item = None  # Reset to look in the room instead

    # If no bound object, search for the item by name
    if not found_item:
        # Look for a matching item in the room ONLY
        all_visible_items = current_room.get_items(game_state)
        for item in all_visible_items:
            if subject and hasattr(item, "matches_name") and item.matches_name(subject):
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
            if hasattr(found_item, "id") and found_item.id in current_room.hidden_items:
                current_room.remove_hidden_item(found_item.id)

            # Save player state
            player_manager.save_players()

        return cast(str, message)

    return f"You don't see '{subject}' here."


# ===== DROP COMMAND =====
async def handle_drop(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
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
    async def drop_single_item(item: Any) -> str:
        player.remove_item(item)

        # Special handling for treasure in swamp rooms
        if is_swamp_room and hasattr(item, "value") and item.value > 0:
            success, message = current_room.handle_treasure_drop(
                item, player, game_state, player_manager, sio, online_sessions
            )
            return cast(str, message)
        else:
            # Standard drop behavior
            current_room.add_item(item)
            # Broadcast to other players in the room
            await broadcast_item_drop(player.current_room, player.name, item.name)
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
        treasure_items = [
            item
            for item in player.inventory
            if hasattr(item, "value") and item.value > 0
        ]

        if not treasure_items:
            return "You have no treasure to drop."

        messages = []
        for item in treasure_items:
            message = await drop_single_item(item)
            messages.append(message)

        # Save player state
        player_manager.save_players()

        return "\n".join(messages)

    # Handle dropping a specific item - require object binding
    if not subject_obj:
        # No object binding - item not found
        if player.inventory:
            return f"You don't have '{subject}'."
        else:
            return "You aren't carrying anything."

    # Verify the item is in inventory
    if subject_obj not in player.inventory:
        return f"You don't have the {subject_obj.name} in your inventory."

    # Item is valid and in inventory
    result = await drop_single_item(subject_obj)

    # Save player state
    player_manager.save_players()

    return result


# ===== SCORE COMMAND =====
async def handle_score(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Handle the 'score' command."""
    return (
        f"Score: {player.points} points\n"
        f"Level: {player.level}\n"
        f"Stamina: {player.stamina}/{player.max_stamina}\n"
        f"Strength: {player.strength}\n"
        f"Dexterity: {player.dexterity}\n"
        f"Carrying capacity: {len(player.inventory)}/{player.carrying_capacity_num} items"
    )


# ===== HELP COMMAND =====
async def handle_help(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Handle the 'help' command."""
    # Get the subject (specific command to get help for)
    subject = cmd.get("subject")

    # If a specific command was requested
    if subject:
        return command_registry.get_help(subject)

    # General help
    help_text = (
        "Commands:\n\n"
        "MOVEMENT:\n"
        "  n, s, e, w                   - Move north, south, east, west (also: north, south, etc).\n"
        "  ne, nw, se, sw               - Move diagonally (also: northeast, etc).\n"
        "  up, down, in, out            - Move vertically or through entrances/exits.\n"
        "  flee <direction>             - Escape from combat (drops items, loses points).\n\n"
        "COMMUNICATION:\n"
        '  "<message>                  - Say something to everyone in your room (also: say).\n'
        "  <player> <message>           - Send a private message to a specific player (also: tell).\n"
        "  shout <message>              - Broadcast to all players in the game.\n"
        "  act <action>                 - Perform an emote or action.\n"
        "  converse                     - Toggle conversation mode (auto-say).\n\n"
        "ITEMS:\n"
        "  look [<item>]                - Examine your surroundings or a specific item (also: l).\n"
        "  get <item>                   - Pick up an item (also: g, take).\n"
        "  drop <item>                  - Drop an item (also: dr).\n"
        "  inventory                    - List items you're carrying (also: i, inv).\n"
        "  get all                      - Get all available items in the room.\n"
        "  get t                        - Get all treasure items in the room.\n"
        "  drop all                     - Drop everything you're carrying.\n\n"
        "CONTAINERS:\n"
        "  open <container>             - Open a container.\n"
        "  close <container>            - Close a container.\n"
        "  put <item> in <container>    - Put an item into a container.\n"
        "  get <item> from <container>  - Take an item from a container.\n"
        "  empty <container>            - Empty all contents of a container into the room.\n\n"
        "INTERACTIONS:\n"
        "  <verb> <object>              - Interact with objects (push, pull, move, etc).\n"
        "  <verb> <object> with <item>  - Use an item with an object.\n"
        "  read <object>                - Read inscriptions or examine objects closely.\n"
        "  use <item> with <object>     - Try to use items with objects in the world.\n\n"
        "PLAYER INTERACTIONS:\n"
        "  attack <player>              - Attack another player (also: k, kill).\n"
        "  retaliate with <weapon>      - Use a weapon in combat (also: ret).\n"
        "  give <item> to <player>      - Give an item to another player.\n"
        "  steal <item> from <player>   - Attempt to steal from another player.\n\n"
        "REST:\n"
        "  sleep                        - Go to sleep to recover stamina (also: rest).\n"
        "  wake                         - Wake up from sleep (also: awake).\n"
        "  wake <player>                - Wake up another sleeping player.\n\n"
        "INFORMATION:\n"
        "  score                        - Show your current stats (also: sc).\n"
        "  levels                       - Show the levels of experience.\n"
        "  exits                        - Show available exits from your location (also: x).\n"
        "  users                        - List online players (also: who).\n"
        "  info                         - Get game information and objectives.\n"
        "  help [<command>]             - Show this help or help for a specific command.\n\n"
        "ACCOUNT:\n"
        "  password                     - Change your account password.\n"
        "  quit                         - Exit the game (also: qq, bye).\n"
    )
    return help_text


# ===== INFO COMMAND =====
async def handle_info(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
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
async def handle_levels(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
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
async def handle_users(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Handle the 'users' command."""
    if not online_sessions:
        return "How is this possible?"

    user_list = []
    for sid, session_data in online_sessions.items():
        other_player = session_data.get("player")
        # Filter out players awaiting respawn, in limbo, or invisible
        if (
            other_player
            and not session_data.get("awaiting_respawn", False)
            and other_player.current_room is not None
            and not is_invisible(other_player, online_sessions)
        ):
            user_list.append(f"{other_player.name} the {other_player.level}")

    return "\n".join(f"{user} is playing" for user in user_list)


# ===== QUIT COMMAND =====
async def handle_quit(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Handle the 'quit' command."""
    return "quit"


# ===== DIAGNOSTIC COMMAND =====
async def handle_diagnostic(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Any],
    sio: Any,
    utils: Any,
) -> str:
    """Debug command to print information about items in the room."""

    current_room = game_state.get_room(player.current_room)

    result = "=== DIAGNOSTIC INFO ===\n"
    result += f"Current room: {current_room.room_id} ({current_room.name})\n"
    result += f"Visible items: {len(current_room.items)}\n"

    # List all items in the room
    result += "\nROOM ITEMS:\n"
    for item in current_room.items:
        result += f"- {item.name} (ID: {getattr(item, 'id', 'unknown')})\n"

        # Check if it's a StatefulItem
        if hasattr(item, "state"):
            result += f"  State: {item.state}\n"

        # Check for interactions
        if hasattr(item, "interactions"):
            result += "  Has interactions: YES\n"
            result += f"  Verbs: {list(item.interactions.keys())}\n"

            # Check structure of interaction lists
            for verb, interactions in item.interactions.items():
                result += f"  Verb: {verb}\n"
                if isinstance(interactions, list):
                    result += "    Is a list: YES\n"
                    result += f"    Number of interactions: {len(interactions)}\n"
                    for i, inter in enumerate(interactions):
                        result += f"    Interaction {i}:\n"
                        if isinstance(inter, dict):
                            result += "      Is a dictionary: YES\n"
                            result += f"      Keys: {list(inter.keys())}\n"
                        else:
                            result += (
                                f"      Is a dictionary: NO - TYPE: {type(inter)}\n"
                            )
                else:
                    result += f"    Is a list: NO - TYPE: {type(interactions)}\n"
        else:
            result += "  Has interactions: NO\n"

    # Check inventory items
    result += "\nINVENTORY ITEMS:\n"
    for item in player.inventory:
        result += f"- {item.name} (ID: {getattr(item, 'id', 'unknown')})\n"

        # Check if it's a container
        if hasattr(item, "items"):
            result += "  Is container: YES\n"
            result += f"  Container state: {getattr(item, 'state', 'unknown')}\n"
            result += f"  Contains: {len(item.items)} items\n"

            # Check for interactions
            if hasattr(item, "interactions"):
                result += "  Has interactions: YES\n"
                result += f"  Verbs: {list(item.interactions.keys())}\n"

                # Check open/close
                for verb in ["open", "close"]:
                    if verb in item.interactions:
                        result += f"  Has {verb} verb: YES\n"
                        interactions = item.interactions[verb]
                        if isinstance(interactions, list):
                            result += f"    {verb} is a list: YES\n"
                            result += (
                                f"    Number of interactions: {len(interactions)}\n"
                            )
                        else:
                            result += f"    {verb} is a list: NO - TYPE: {type(interactions)}\n"
            else:
                result += "  Has interactions: NO\n"

    return result


# Register standard commands
command_registry.register(
    "look", handle_look, "Describes your current location or an object."
)
command_registry.register(
    "inventory", handle_inventory, "Lists items in your inventory."
)
command_registry.register(
    "exits", handle_exits, "Lists available exits from your current location."
)
command_registry.register(
    "get", handle_get, "Pick up an item from your surroundings or from a container."
)
command_registry.register("drop", handle_drop, "Drop an item from your inventory.")
command_registry.register("score", handle_score, "Shows your current score and stats.")
command_registry.register("help", handle_help, "Provides help on commands.")
command_registry.register(
    "info", handle_info, "Provides information about the game and its objectives."
)
command_registry.register("users", handle_users, "Lists online users.")
command_registry.register("quit", handle_quit, "Exit the game.")
command_registry.register("levels", handle_levels, "Lists levels of experience.")
command_registry.register(
    "debug", handle_diagnostic, "Show diagnostic info for debugging."
)

# Register aliases
command_registry.register_alias("l", "look")
command_registry.register_alias("commands", "help")
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
