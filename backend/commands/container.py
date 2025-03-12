# backend/commands/container.py

from commands.registry import command_registry
from models.ContainerItem import ContainerItem
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== PUT COMMAND =====
async def handle_put(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle putting an item into a container.
    Format: put <item> in <container>
    """
    # Get the subject (item) and instrument (container)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    instrument = cmd.get("instrument")
    instrument_obj = cmd.get("instrument_object")
    
    if not subject and not subject_obj:
        return "What do you want to put?"
    
    if not instrument and not instrument_obj:
        return "You can only insert items into objects, not anything else."
    
    # Find the item in player's inventory - prefer the bound object if available
    item_to_put = subject_obj if subject_obj in player.inventory else None
    
    if not item_to_put:
        for item in player.inventory:
            if subject.lower() in item.name.lower():
                item_to_put = item
                break
    
    if not item_to_put:
        return f"You don't have '{subject}' in your inventory."
    
    # Find the container in player's inventory - prefer the bound object if available
    container = instrument_obj if (instrument_obj in player.inventory and 
                                  isinstance(instrument_obj, ContainerItem)) else None
    
    if not container:
        for item in player.inventory:
            if instrument.lower() in item.name.lower() and isinstance(item, ContainerItem):
                container = item
                break
    
    if not container:
        return f"You don't have a container called '{instrument}' in your inventory."
    
    # Check if the container is open
    if container.state != "open":
        return f"The {container.name} is closed. You need to open it first."
    
    # Check if the item is a container (nested containers not allowed)
    if isinstance(item_to_put, ContainerItem):
        return f"Infinite recursion doesn't exist in this realm."
    
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
    
    Note: This is called directly when a get/from command is identified by the parser.
    """
    # Get the subject (item) and instrument (container)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    instrument = cmd.get("instrument")
    instrument_obj = cmd.get("instrument_object")
    
    if not subject and not subject_obj:
        return "What do you want to get?"
    
    if not instrument and not instrument_obj:
        return f"Where do you want to get {subject} from?"
    
    # Find the container in player's inventory - prefer the bound object if available
    container = instrument_obj if (instrument_obj in player.inventory and 
                                  isinstance(instrument_obj, ContainerItem)) else None
    
    if not container:
        for item in player.inventory:
            if instrument.lower() in item.name.lower() and isinstance(item, ContainerItem):
                container = item
                break
    
    if not container:
        return f"You don't have a container called '{instrument}' in your inventory."
    
    # Check if the container is open
    if container.state != "open":
        return f"The {container.name} is closed. You need to open it first."
    
    # Find the item in the container - prefer the bound object if available
    item_to_get = None
    if subject_obj:
        for item in container.items:
            if item == subject_obj:
                item_to_get = item
                break
    
    if not item_to_get:
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
        return message


# ===== OPEN/CLOSE COMMANDS =====
async def handle_open(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """Handle opening a container."""
    # Get the subject (container)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    
    if not subject and not subject_obj:
        return "What do you want to open?"
    
    # Try to find the container - prefer the bound object if available
    container = None
    
    # Check if the subject object is a container
    if subject_obj and isinstance(subject_obj, ContainerItem):
        if subject_obj in player.inventory:
            container = subject_obj
        else:
            current_room = game_state.get_room(player.current_room)
            if subject_obj in current_room.get_items(game_state):
                container = subject_obj
    
    # If no bound container found, search by name
    if not container:
        # Try player's inventory
        for item in player.inventory:
            if subject.lower() in item.name.lower() and isinstance(item, ContainerItem):
                container = item
                break
        
        # If not in inventory, check the room
        if not container:
            current_room = game_state.get_room(player.current_room)
            for item in current_room.get_items(game_state):
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
    # Get the subject (container)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    
    if not subject and not subject_obj:
        return "What do you want to close?"
    
    # Try to find the container - prefer the bound object if available
    container = None
    
    # Check if the subject object is a container
    if subject_obj and isinstance(subject_obj, ContainerItem):
        if subject_obj in player.inventory:
            container = subject_obj
        else:
            current_room = game_state.get_room(player.current_room)
            if subject_obj in current_room.get_items(game_state):
                container = subject_obj
    
    # If no bound container found, search by name
    if not container:
        # Try player's inventory
        for item in player.inventory:
            if subject.lower() in item.name.lower() and isinstance(item, ContainerItem):
                container = item
                break
        
        # If not in inventory, check the room
        if not container:
            current_room = game_state.get_room(player.current_room)
            for item in current_room.get_items(game_state):
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


async def handle_empty(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle emptying a container, dropping all contained items into the current room.
    Format: empty <container>
    """
    # Get the subject (container to empty)
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")
    
    if not subject and not subject_obj:
        return "What container do you want to empty?"
    
    # Try to find the container - prefer the bound object if available
    container = None
    
    # Check if the subject object is a container
    if subject_obj and isinstance(subject_obj, ContainerItem):
        if subject_obj in player.inventory:
            container = subject_obj
    
    # If no bound container found, search by name
    if not container:
        # Try player's inventory
        for item in player.inventory:
            if subject.lower() in item.name.lower() and isinstance(item, ContainerItem):
                container = item
                break
    
    if not container:
        return f"You don't see '{subject}'!"
    
    # Container found - empty it
    if len(container.items) == 0:
        return f"The {container.name} is already empty."
    
    current_room = game_state.get_room(player.current_room)
    messages = []
    
    # Check if the container is closed
    if container.state == "closed":
        # Open it first
        container.set_state("open")
        
    # Drop all items from the container to the room
    for item in list(container.items):
        # Remove from container and add to room
        container.remove_item(item.id)
        current_room.add_item(item)
        messages.append(f"{item.name.capitalize()} dropped.")
    
    # Add a summary message
    messages.append(f"The {container.name} now contains nothing.")
    
    # Save player state
    player_manager.save_players()
    
    return "\n".join(messages)


# Register container commands
command_registry.register("put", handle_put, "Put an item into a container. Usage: put <item> in <container>")
command_registry.register("open", handle_open, "Open a container.")
command_registry.register("close", handle_close, "Close a container.")
command_registry.register("empty", handle_empty, "Empty a container, dropping all its contents. Usage: empty <container>")

# Make sure to register insert as an alias for put
command_registry.register_alias("insert", "put")
command_registry.register_alias("remove", "get")