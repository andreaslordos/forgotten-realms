# backend/commands/puzzle.py

from commands.registry import command_registry

# ===== USE COMMAND =====
async def handle_use(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """
    Handle using an item, possibly with another item or object.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player using the item
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        
    Returns:
        str: Result message
    """
    subject = cmd.get("subject")  # The item being used
    instrument = cmd.get("instrument")  # What it's being used with/on
    
    if not subject:
        return "What do you want to use?"
    
    # Check if the item being used is in the player's inventory
    item_to_use = None
    for item in player.inventory:
        if subject.lower() in item.name.lower():
            item_to_use = item
            break
    
    # If the item is not in inventory, check the room
    if not item_to_use:
        current_room = game_state.get_room(player.current_room)
        for item in current_room.items:
            if subject.lower() in item.name.lower():
                item_to_use = item
                break
    
    if not item_to_use:
        return f"You don't have or see '{subject}'."
    
    # If no instrument specified, try to use the item by itself
    if not instrument:
        return handle_use_simple(item_to_use, player, game_state, player_manager)
    
    # Check if the instrument is in inventory
    target_item = None
    for item in player.inventory:
        if instrument.lower() in item.name.lower():
            target_item = item
            break
    
    # If not in inventory, check the room
    if not target_item:
        current_room = game_state.get_room(player.current_room)
        for item in current_room.items:
            if instrument.lower() in item.name.lower():
                target_item = item
                break
        
        # If still not found, check for special room features
        if not target_item:
            # This would check for special features in the room description
            # Like "door", "statue", "tree", etc.
            if "door" in instrument.lower() and "door" in current_room.description.lower():
                return handle_use_with_feature(item_to_use, "door", player, game_state, player_manager)
            elif "statue" in instrument.lower() and "statue" in current_room.description.lower():
                return handle_use_with_feature(item_to_use, "statue", player, game_state, player_manager)
            # Add more special features as needed
            
            return f"You don't see '{instrument}' here."
    
    # Handle using one item with another
    return handle_use_with_item(item_to_use, target_item, player, game_state, player_manager)


def handle_use_simple(item, player, game_state, player_manager):
    """Handle using an item by itself."""
    # This would be expanded based on special item functionality
    # For now, we'll just provide a generic response
    return f"You use {item.name}, but nothing special happens."


def handle_use_with_item(item, target, player, game_state, player_manager):
    """Handle using one item with another item."""
    # This would be expanded with specific item interactions
    # For now, we'll just provide a generic response
    return f"You use {item.name} with {target.name}, but nothing special happens."


def handle_use_with_feature(item, feature, player, game_state, player_manager):
    """Handle using an item with a room feature."""
    # This would be expanded with specific feature interactions
    # For now, we'll just provide a generic response
    return f"You use {item.name} with the {feature}, but nothing special happens."


# ===== PUZZLE INTERACTION COMMANDS =====
# These commands handle specific interactions with puzzles

async def handle_knock(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle knocking on something."""
    subject = cmd.get("subject")
    
    if not subject:
        return "What do you want to knock on?"
    
    current_room = game_state.get_room(player.current_room)
    
    # Example interaction: Knocking on a door
    if "door" in subject.lower() and "door" in current_room.description.lower():
        # Check if this is a special door
        if "golden" in subject.lower() and "golden door" in current_room.description.lower():
            # This would trigger AI generation of a new zone
            return "You knock on the golden door. It slowly swings open, revealing a passage..."
            # In the real implementation, this would call a function to generate a new zone
        elif "secret" in subject.lower() and "secret door" in current_room.description.lower():
            # This might reveal a hidden passage
            return "You knock on what appears to be a secret door. It slides open!"
            # In the real implementation, this would update the room exits
        else:
            return "You knock on the door, but nothing happens."
    
    return f"You knock on the {subject}, but nothing happens."


async def handle_push(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle pushing something."""
    subject = cmd.get("subject")
    
    if not subject:
        return "What do you want to push?"
    
    current_room = game_state.get_room(player.current_room)
    
    # Example interaction: Pushing a statue or button
    if "statue" in subject.lower() and "statue" in current_room.description.lower():
        # This might reveal a hidden passage or item
        return "You push the statue and hear a grinding sound as it moves slightly, revealing a small compartment!"
        # In the real implementation, this would add an item to the room or update exits
    elif "button" in subject.lower() and "button" in current_room.description.lower():
        # This might trigger a trap or puzzle mechanism
        return "You push the button and hear a clicking sound from somewhere nearby."
        # In the real implementation, this would update a puzzle state
    
    return f"You push the {subject}, but nothing happens."


async def handle_pull(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle pulling something."""
    subject = cmd.get("subject")
    
    if not subject:
        return "What do you want to pull?"
    
    current_room = game_state.get_room(player.current_room)
    
    # Example interaction: Pulling a lever or rope
    if "lever" in subject.lower() and "lever" in current_room.description.lower():
        # This might open a door or trigger a mechanism
        return "You pull the lever and hear a loud mechanical sound!"
        # In the real implementation, this would update a puzzle state or room exits
    elif "rope" in subject.lower() and "rope" in current_room.description.lower():
        # This might ring a bell or open a trapdoor
        return "You pull the rope and hear a bell ringing in the distance."
        # In the real implementation, this would trigger an event
    
    return f"You pull the {subject}, but nothing happens."


async def handle_chop(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """Handle chopping something with an item."""
    subject = cmd.get("subject")  # What to chop
    instrument = cmd.get("instrument")  # What to chop with
    
    if not subject:
        return "What do you want to chop?"
    
    if not instrument:
        return f"What do you want to chop the {subject} with?"
    
    # Check if the chopping instrument is in inventory
    axe_item = None
    for item in player.inventory:
        if instrument.lower() in item.name.lower():
            axe_item = item
            break
    
    if not axe_item:
        return f"You don't have a {instrument} to chop with."
    
    current_room = game_state.get_room(player.current_room)
    
    # Example interaction: Chopping a tree
    if "tree" in subject.lower() and "tree" in current_room.description.lower():
        # Check if it's a special tree
        if "yew" in subject.lower() and "yew tree" in current_room.description.lower():
            # This might reveal a hidden passage or special item
            return "You chop at the yew tree, revealing a hidden entrance beneath its roots!"
            # In the real implementation, this would update room exits or add items
        else:
            return f"You chop at the tree with your {axe_item.name} and gather some firewood."
    
    return f"You try to chop the {subject} with your {axe_item.name}, but nothing useful happens."


# ===== ARCHMAGE COMMANDS =====
# These commands are only available to players at the Archmage level

async def handle_reset(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """
    Handle the Archmage reset command.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player issuing the reset
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Result message
    """
    # Check if the player is an Archmage
    if player.level != "Archmage":
        return "Only Archmages can reset the world."
    
    # Broadcast the reset event to all players
    if online_sessions and sio and utils:
        reset_message = f"The Archmage {player.name} resets the world!"
        for sid, session_data in online_sessions.items():
            if 'player' in session_data:
                await utils.send_message(sio, sid, reset_message)
                
                # Mark all sessions for disconnection
                if sid != sio.manager.sid:  # Don't disconnect the Archmage yet
                    session_data['should_disconnect'] = True
    
    # In a real implementation, this would call a more complex reset routine
    # For now, we'll just return a message
    return "You have issued a reset command. The world begins to blur around you..."
    # The actual reset logic would be implemented in the main game loop


async def handle_teleport(cmd, player, game_state, player_manager, visited, online_sessions, sio, utils):
    """
    Handle the Archmage teleport command.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player teleporting
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        visited (set): Set of visited room IDs
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Result message
    """
    # Check if the player is an Archmage
    if player.level != "Archmage":
        return "Only Archmages can teleport."
    
    subject = cmd.get("subject")  # Destination
    
    if not subject:
        return "Where do you want to teleport to?"
    
    # Handle special teleport destinations
    if "underswamp" in subject.lower():
        # Find the underswamp room ID
        underswamp_id = None
        for room_id, room in game_state.rooms.items():
            if "underswamp" in room.name.lower() or "under swamp" in room.name.lower():
                underswamp_id = room_id
                break
        
        if not underswamp_id:
            return "The Underswamp does not seem to exist in this world yet."
        
        # Notify departure from the old room
        old_room = game_state.get_room(player.current_room)
        if online_sessions and sio and utils:
            for sid, session_data in online_sessions.items():
                other_player = session_data.get('player')
                if (other_player and 
                    other_player.current_room == player.current_room and 
                    other_player != player):
                    await utils.send_message(sio, sid, 
                                          f"{player.name} vanishes in a cloud of arcane energy!")
        
        # Teleport the player
        player.set_current_room(underswamp_id)
        player_manager.save_players()
        
        # Notify arrival in the new room
        if online_sessions and sio and utils:
            for sid, session_data in online_sessions.items():
                other_player = session_data.get('player')
                if (other_player and 
                    other_player.current_room == underswamp_id and 
                    other_player != player):
                    await utils.send_message(sio, sid, 
                                          f"{player.name} appears in a flash of light!")
        
        if visited is not None:
            visited.add(underswamp_id)
        
        # Return the new room description
        underswamp_room = game_state.get_room(underswamp_id)
        return f"You teleport to the Underswamp!\n\n{underswamp_room.name}\n{underswamp_room.description}"
    
    # If not a special destination, try to find a room with a matching name
    destination_id = None
    for room_id, room in game_state.rooms.items():
        if subject.lower() in room.name.lower():
            destination_id = room_id
            break
    
    if not destination_id:
        return f"No location matching '{subject}' found."
    
    # Notify departure from the old room
    old_room = game_state.get_room(player.current_room)
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == player.current_room and 
                other_player != player):
                await utils.send_message(sio, sid, 
                                      f"{player.name} vanishes in a cloud of arcane energy!")
    
    # Teleport the player
    player.set_current_room(destination_id)
    player_manager.save_players()
    
    # Notify arrival in the new room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == destination_id and 
                other_player != player):
                await utils.send_message(sio, sid, 
                                      f"{player.name} appears in a flash of light!")
    
    if visited is not None:
        visited.add(destination_id)
    
    # Return the new room description
    destination_room = game_state.get_room(destination_id)
    return f"You teleport to {destination_room.name}!\n\n{destination_room.description}"


# Register puzzle interaction commands
command_registry.register("use", handle_use, "Use an item, optionally with another item or object.")
command_registry.register("knock", handle_knock, "Knock on something like a door.")
command_registry.register("push", handle_push, "Push something like a statue or button.")
command_registry.register("pull", handle_pull, "Pull something like a lever or rope.")
command_registry.register("chop", handle_chop, "Chop something with an appropriate tool.")

# Register Archmage commands
command_registry.register("reset", handle_reset, "Reset the world to its default state (Archmage only).")
command_registry.register("teleport", handle_teleport, "Teleport to a specific location (Archmage only).")

# Register aliases
command_registry.register_alias("open", "use")
command_registry.register_alias("unlock", "use")
command_registry.register_alias("tp", "teleport")