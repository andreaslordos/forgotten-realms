# backend/commands/container.py

from commands.registry import command_registry
from models.ContainerItem import ContainerItem
import logging

# Set up logging
logger = logging.getLogger(__name__)

# ===== PUT COMMAND =====
async def handle_put(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle putting an item into a container.
    Format: put <item> in <container>
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player executing the command
        game_state (GameState): The current game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Result message
    """
    subject = cmd.get("subject")  # The item to put
    instrument = cmd.get("instrument")  # The container to put it in
    
    if not subject:
        return "What do you want to put?"
    
    if not instrument:
        return "You can only insert items into objects, not anything else."
    
    # Find the item in player's inventory
    item_to_put = None
    for item in player.inventory:
        if subject.lower() in item.name.lower():
            item_to_put = item
            break
    
    if not item_to_put:
        return f"You don't have '{subject}' in your inventory."
    
    # Find the container in player's inventory
    container = None
    for item in player.inventory:
        if instrument.lower() in item.name.lower() and isinstance(item, ContainerItem):
            container = item
            break
    
    if not container:
        return f"You don't have a container called '{instrument}' in your inventory."
    
    # Check if the container is open
    if container.state != "open":
        return f"The {container.name} is closed. You need to open it first."
    
    # Add the item to the container
    if container.add_item(item_to_put):
        player.remove_item(item_to_put)
        player_manager.save_players()  # Save player state after changing inventory
        return f"{item_to_put.name} now inside the {container.name}."
    else:
        # If add_item returned False, the container is full or item is too heavy
        if len(container.items) >= container.capacity_limit:
            return f"The {container.name} is full and can't hold any more items."
        elif container.current_weight() + item_to_put.weight > container.capacity_weight:
            return f"The {container.name} can't hold something that heavy."
        else:
            return f"You can't put {item_to_put.name} into the {container.name}."

# ===== GET FROM COMMAND =====
async def handle_get_from(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle getting an item from a container.
    Format: get <item> from <container>
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player executing the command
        game_state (GameState): The current game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Result message
    """
    subject = cmd.get("subject")  # The item to get
    instrument = cmd.get("instrument")  # The container to get it from
    
    if not subject:
        return "What do you want to get?"
    
    if not instrument:
        return f"Where do you want to get {subject} from?"
    
    # Find the container in player's inventory
    container = None
    for item in player.inventory:
        if instrument.lower() in item.name.lower() and isinstance(item, ContainerItem):
            container = item
            break
    
    if not container:
        return f"You don't have a container called '{instrument}' in your inventory."
    
    # Check if the container is open
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
        return f"You get {item_to_get.name} from the {container.name}."
    else:
        return message  # Return the error message from player.add_item


# ===== OPEN/CLOSE COMMANDS =====
async def handle_open(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle opening a container."""
    subject = cmd.get("subject")
    
    if not subject:
        return "What do you want to open?"
    
    # Try to find the container in player's inventory
    container = None
    for item in player.inventory:
        if subject.lower() in item.name.lower() and isinstance(item, ContainerItem):
            container = item
            break
    
    # If not in inventory, check the room
    if not container:
        current_room = game_state.get_room(player.current_room)
        for item in current_room.items:
            if subject.lower() in item.name.lower() and isinstance(item, ContainerItem):
                container = item
                break
    
    if not container:
        return f"You don't see '{subject}' here."
    
    if container.state == "open":
        return f"The {container.name} is already open."
    
    container.set_state("open")
    player_manager.save_players()  # Save state
    return f"You open the {container.name}."


async def handle_close(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle closing a container."""
    subject = cmd.get("subject")
    
    if not subject:
        return "What do you want to close?"
    
    # Try to find the container in player's inventory
    container = None
    for item in player.inventory:
        if subject.lower() in item.name.lower() and isinstance(item, ContainerItem):
            container = item
            break
    
    # If not in inventory, check the room
    if not container:
        current_room = game_state.get_room(player.current_room)
        for item in current_room.items:
            if subject.lower() in item.name.lower() and isinstance(item, ContainerItem):
                container = item
                break
    
    if not container:
        return f"You don't see '{subject}' here."
    
    if container.state == "closed":
        return f"The {container.name} is already closed."
    
    container.set_state("closed")
    player_manager.save_players()  # Save state
    return f"You close the {container.name}."


# Register container commands
command_registry.register("put", handle_put, "Put an item into a container. Usage: put <item> in <container>")
command_registry.register("open", handle_open, "Open a container.")
command_registry.register("close", handle_close, "Close a container.")

# For get/take from commands, we'll use the parser's special handling,
# not register them as separate commands with underscores

# Make sure to register insert as an alias for put
command_registry.register_alias("insert", "put")
command_registry.register_alias("remove", "get")