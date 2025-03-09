# backend/commands/combat.py

import random
from commands.registry import command_registry

# ===== ATTACK/KILL COMMAND =====
async def handle_attack(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle attacking a target.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player attacking
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Combat result message
    """
    subject = cmd.get("subject")  # target
    instrument = cmd.get("instrument")  # weapon
    
    if not subject:
        return "Who do you want to attack?"
    
    # First, look for a player target in the room
    target_player = None
    target_sid = None
    
    if online_sessions:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == player.current_room and 
                other_player != player and
                subject.lower() in other_player.name.lower()):
                target_player = other_player
                target_sid = sid
                break
    
    # If a player target was found
    if target_player:
        return await handle_player_combat(player, target_player, target_sid, instrument, online_sessions, sio, utils)
    
    # TODO: Look for an NPC/mob target in the room
    # This would be implemented when the NPC/mob system is created
    
    return f"You don't see '{subject}' here."


async def handle_player_combat(attacker, defender, defender_sid, weapon, online_sessions, sio, utils):
    """
    Handle player-vs-player combat.
    
    Args:
        attacker (Player): The attacking player
        defender (Player): The defending player
        defender_sid (str): The defender's session ID
        weapon (str): Optional weapon name
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Combat result message
    """
    # Find weapon in inventory if specified
    weapon_item = None
    weapon_bonus = 0
    
    if weapon:
        for item in attacker.inventory:
            if weapon.lower() in item.name.lower():
                weapon_item = item
                # Assuming weapons might have a damage attribute
                weapon_bonus = getattr(item, 'damage', 5)
                break
    
    # Calculate base damage based on attacker's strength and weapon
    base_damage = (attacker.strength // 10) + weapon_bonus
    
    # Add random variation (±20%)
    variation = random.uniform(0.8, 1.2)
    damage = int(base_damage * variation)
    
    # Apply damage to defender
    defender.stamina = max(0, defender.stamina - damage)
    
    # Notify the defender
    if sio and utils:
        attack_msg = f"{attacker.name} attacks you"
        if weapon_item:
            attack_msg += f" with {weapon_item.name}"
        attack_msg += f" for {damage} damage! Stamina: {defender.stamina}/{defender.max_stamina}"
        
        await utils.send_message(sio, defender_sid, attack_msg)
        await utils.send_stats_update(sio, defender_sid, defender)
    
    # Check if defender is defeated
    if defender.stamina <= 0:
        # Handle defeat - drop all items, lose points, respawn
        return await handle_player_defeat(attacker, defender, defender_sid, game_state, player_manager, online_sessions, sio, utils)
    
    # Return result to attacker
    result = f"You attack {defender.name}"
    if weapon_item:
        result += f" with {weapon_item.name}"
    result += f" for {damage} damage!"
    
    return result


async def handle_player_defeat(attacker, defender, defender_sid, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle when a player defeats another player.
    
    Args:
        attacker (Player): The attacking player
        defender (Player): The defeated player
        defender_sid (str): The defender's session ID
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Victory message
    """
    # Drop all defender's items in the current room
    current_room = game_state.get_room(defender.current_room)
    
    for item in list(defender.inventory):
        defender.remove_item(item)
        current_room.add_item(item)
    
    # Lose some points (e.g., 10% of current points)
    points_lost = defender.points // 10
    defender.points = max(0, defender.points - points_lost)
    
    # Respawn at spawn room
    old_room = defender.current_room
    defender.set_current_room(player_manager.spawn_room)
    
    # Reset stamina to a percentage of max (e.g., 50%)
    defender.stamina = defender.max_stamina // 2
    
    # Save changes
    game_state.save_rooms()
    player_manager.save_players()
    
    # Notify the defender of their defeat
    if sio and utils:
        defeat_msg = (f"{attacker.name} has defeated you! You've lost {points_lost} points.\n"
                     f"All your items have been dropped.\n"
                     f"You've been returned to the village center.")
        
        await utils.send_message(sio, defender_sid, defeat_msg)
        await utils.send_stats_update(sio, defender_sid, defender)
        
        # Send the new room description to the defender
        spawn_room = game_state.get_room(player_manager.spawn_room)
        await utils.send_message(sio, defender_sid, 
                               f"{spawn_room.name}\n{spawn_room.description}")
    
    # Notify others in the old room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == old_room and 
                other_player != defender and
                other_player != attacker):
                await utils.send_message(sio, sid, 
                                       f"{attacker.name} has defeated {defender.name}!")
    
    # Return victory message to attacker
    return (f"You have defeated {defender.name}!\n"
           f"They've lost {points_lost} points and dropped all their items.")


# ===== RETALIATE COMMAND =====
async def handle_retaliate(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle retaliating against someone who attacked you.
    This is similar to attack but targets the last person who attacked you.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player retaliating
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Combat result message
    """
    # In a real implementation, we would track the last attacker
    # For now, we'll just pass through to the attack handler with the subject
    subject = cmd.get("subject")
    instrument = cmd.get("instrument")
    
    if not subject:
        return "Who do you want to retaliate against?"
    
    # Create a new command dict for the attack handler
    attack_cmd = {
        "verb": "attack",
        "subject": subject,
        "instrument": instrument,
        "original": f"retaliate {subject} with {instrument}" if instrument else f"retaliate {subject}"
    }
    
    return await handle_attack(attack_cmd, player, game_state, player_manager, online_sessions, sio, utils)


# ===== FLEE COMMAND =====
async def handle_flee(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle fleeing from combat.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player fleeing
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Flee result message
    """
    subject = cmd.get("subject")  # Optional direction
    current_room = game_state.get_room(player.current_room)
    
    # If a direction is specified, try to flee in that direction
    if subject and subject in current_room.exits:
        direction = subject
    else:
        # Choose a random exit
        exits = list(current_room.exits.keys())
        if not exits:
            return "There's nowhere to flee to!"
        direction = random.choice(exits)
    
    # Get the destination room
    new_room_id = current_room.exits[direction]
    new_room = game_state.get_room(new_room_id)
    
    if not new_room:
        return f"You tried to flee {direction}, but something went wrong!"
    
    # Drop all items in the current room
    for item in list(player.inventory):
        player.remove_item(item)
        current_room.add_item(item)
    
    # Notify others in the old room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == player.current_room and 
                other_player != player):
                await utils.send_message(sio, sid, 
                                       f"{player.name} has fled {direction}!")
    
    # Move the player
    player.set_current_room(new_room_id)
    
    # Lose some points (e.g., 5% of current points)
    points_lost = player.points // 20
    player.points = max(0, player.points - points_lost)
    
    # Save changes
    game_state.save_rooms()
    player_manager.save_players()
    
    # Notify others in the new room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == new_room_id and 
                other_player != player):
                await utils.send_message(sio, sid, 
                                       f"{player.name} runs in, panting heavily!")
    
    # Return result message including the room description
    return (f"You flee {direction}, dropping all your items and losing {points_lost} points!\n\n"
           f"{new_room.name}\n{new_room.description}")


# Register combat commands
command_registry.register("attack", handle_attack, "Attack a target (player or NPC).")
command_registry.register("retaliate", handle_retaliate, "Attack back at someone who attacked you.")
command_registry.register("flee", handle_flee, "Escape from combat, dropping all items and losing some points.")

# Register aliases
command_registry.register_alias("kill", "attack")
command_registry.register_alias("k", "attack")
command_registry.register_alias("ret", "retaliate")
command_registry.register_alias("run", "flee")