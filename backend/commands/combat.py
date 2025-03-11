# backend/commands/combat.py

import random
import logging
import inspect
from commands.registry import command_registry
from models.Weapon import Weapon
from models.CombatDialogue import CombatDialogue
from commands.rest import wake_player

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global dictionary to track active combat sessions
# Format: {player_id: {
#   'target': target_player, 
#   'target_sid': target_sid,
#   'weapon': weapon_item,
#   'next_turn': timestamp,
#   'initiative': True/False  # Whether this player has initiative (hits first in a cycle)
# }}
active_combats = {}

# List of commands that are blocked during combat
RESTRICTED_COMMANDS = [
    "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest",
    "up", "down", "in", "out", "n", "s", "e", "w", "ne", "nw", "se", "sw", "u", "d",
    "quit", "password", "set", "reset"
]

# ===== ATTACK/KILL COMMAND =====
async def handle_attack(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle attacking a target, initiating continuous combat.
    """
    subject = cmd.get("subject")  # target
    instrument = cmd.get("instrument")  # weapon
    
    if not subject:
        return "Who do you want to attack?"
    
    # Check if player is already in combat
    if player.name in active_combats:
        existing_target = active_combats[player.name]['target']
        return f"You're already fighting {existing_target.name}!"
    
    # Find a player target in the room
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
                
                # Check if target is sleeping and wake them up
                if session_data.get('sleeping'):
                    await wake_player(other_player, sid, online_sessions, sio, utils, woken_by=player)
                break
    
    # If a player target was found
    if target_player:
        # Find weapon in inventory if specified
        weapon_item = None
        
        if instrument:
            for item in player.inventory:
                if instrument.lower() in item.name.lower():
                    # Check if it's a weapon
                    if isinstance(item, Weapon) or hasattr(item, 'damage'):
                        weapon_item = item
                        
                        # If it's a Weapon, check requirements
                        if isinstance(item, Weapon):
                            can_use, reason = item.can_use(player)
                            if not can_use:
                                return reason
                    else:
                        return f"{item.name} is not a weapon."
                    break
        
        # Get session IDs
        player_sid = find_player_sid(player, online_sessions)
        
        # Start combat tracking for attacker
        active_combats[player.name] = {
            'target': target_player,
            'target_sid': target_sid,
            'weapon': weapon_item,
            'initiative': True,  # Attacker starts with initiative
            'last_turn': None    # No turn has happened yet
        }
        
        # Start combat tracking for target
        active_combats[target_player.name] = {
            'target': player,
            'target_sid': player_sid,
            'weapon': None,  # Target starts barehanded
            'initiative': False,  # Defender doesn't have initiative
            'last_turn': None     # No turn has happened yet
        }
        
        # Notify the target they are being attacked
        attack_msg = f"{player.name} attacks you"
        if weapon_item:
            attack_msg += f" with {weapon_item.name}"
        attack_msg += "! Combat has begun. Type 'ret with <weapon>' to use a weapon or 'flee <direction>' to escape."
        
        await utils.send_message(sio, target_sid, attack_msg)
        
        # Immediate first attack from the attacker
        await process_combat_attack(
            player, target_player, 
            weapon_item,
            player_sid, target_sid,
            player_manager, game_state, online_sessions, sio, utils
        )
        
        # Return initial attack message
        result = f"You attack {target_player.name}"
        if weapon_item:
            result += f" with {weapon_item.name}"
        result += "! Combat has begun."
        
        return result
    else:
        # TODO: Look for an NPC/mob target in the room
        # This would be implemented when the NPC/mob system is created
        return f"You don't see '{subject}' here."

# ===== RETALIATE COMMAND =====
async def handle_retaliate(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle retaliating with a weapon when already in combat.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player retaliating
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        
    Returns:
        str: Retaliation message
    """
    instrument = cmd.get("instrument")  # weapon
    
    # Check if player is in combat
    if player.name not in active_combats:
        return "You're not in combat with anyone."
    
    # If no weapon specified
    if not instrument:
        return "Retaliate with what? Specify a weapon."
    
    # Find the weapon in inventory
    weapon_item = None
    for item in player.inventory:
        if instrument.lower() in item.name.lower():
            # Check if it's a weapon
            if isinstance(item, Weapon) or hasattr(item, 'damage'):
                weapon_item = item
                
                # If it's a Weapon, check requirements
                if isinstance(item, Weapon):
                    can_use, reason = item.can_use(player)
                    if not can_use:
                        return reason
            else:
                return f"{item.name} is not a weapon."
            break
    
    if not weapon_item:
        return f"You don't have '{instrument}' in your inventory."
    
    # Update player's combat info with the weapon
    combat_info = active_combats[player.name]
    old_weapon = combat_info['weapon']
    combat_info['weapon'] = weapon_item
    
    # Notify opponent
    opponent = combat_info['target']
    opponent_sid = combat_info['target_sid']
    
    if opponent_sid and utils and sio:
        weapon_msg = f"{player.name} is now using {weapon_item.name} against you!"
        await utils.send_message(sio, opponent_sid, weapon_msg)
    
    # Return confirmation message
    if old_weapon:
        return f"You put away your {old_weapon.name} and ready your {weapon_item.name} for combat!"
    else:
        return f"You ready your {weapon_item.name} for combat!"

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
    
    # Check if player is in combat
    if player.name not in active_combats:
        return "You're not in combat with anyone."
    
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
    
    # Get opponent information before ending combat
    combat_info = active_combats[player.name]
    opponent = combat_info['target']
    opponent_sid = combat_info['target_sid']
    
    # Drop all items in the current room
    for item in list(player.inventory):
        player.remove_item(item)
        current_room.add_item(item)
    
    # End combat for both players
    end_combat(player.name, opponent.name)
    
    # Lose 20% of points when fleeing, and give those points to the opponent
    points_lost = player.points // 5  # 20% of points
    
    # Use add_points to properly update levels
    leveled_up, _ = player.add_points(-points_lost, sio, online_sessions, send_notification=False)
    opponent.add_points(points_lost, sio, online_sessions, send_notification=False)
    
    # Notify opponent
    if opponent_sid and utils and sio:
        flee_msg = f"{player.name} has fled {direction}! You gain {points_lost} points from their cowardice."
        await utils.send_message(sio, opponent_sid, flee_msg)
        await utils.send_stats_update(sio, opponent_sid, opponent)
    
    # Notify others in the old room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and 
                other_player.current_room == player.current_room and 
                other_player != player and
                other_player != opponent):
                await utils.send_message(sio, sid, 
                                       f"{player.name} has fled {direction}!")
    
    # Move the player
    player.set_current_room(new_room_id)
    
    # Save changes
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
    return (f"You flee {direction}, dropping all your items and losing {points_lost} points to {opponent.name}!\n\n"
           f"{new_room.name}\n{new_room.description}")

# ===== COMBAT TICK PROCESSING =====
async def process_combat_tick(sio, online_sessions, player_manager, game_state, utils):
    """
    Process one tick of combat for all active combats.
    This should be called regularly by the game's tick service.
    
    Args:
        sio (SocketIO): Socket.IO instance
        online_sessions (dict): Online sessions dictionary
        player_manager (PlayerManager): The player manager
        game_state (GameState): The game state
        utils (module): Utilities module
    """
    # Get a copy of active combat keys since we might modify during iteration
    combat_players = list(active_combats.keys())
    processed_pairs = set()  # Keep track of combat pairs we've processed
    
    for player_name in combat_players:
        # Skip if combat was ended during this tick
        if player_name not in active_combats:
            continue
            
        combat_info = active_combats[player_name]
        target_player_name = combat_info['target'].name
        
        # Skip if we've already processed this combat pair
        combat_pair = tuple(sorted([player_name, target_player_name]))
        if combat_pair in processed_pairs:
            continue
        
        # Mark this combat pair as processed
        processed_pairs.add(combat_pair)
        
        # Determine who attacks this tick based on initiative
        attacker_name = None
        defender_name = None
        
        # If someone has initiative, they go first
        if player_name in active_combats and active_combats[player_name]['initiative']:
            attacker_name = player_name
            defender_name = target_player_name
        elif target_player_name in active_combats and active_combats[target_player_name]['initiative']:
            attacker_name = target_player_name
            defender_name = player_name
        else:
            # If no one has initiative yet, attacker goes first
            attacker_name = player_name
            defender_name = target_player_name
            if player_name in active_combats:
                active_combats[player_name]['initiative'] = True
        
        # Get session IDs and player objects
        attacker = find_player_by_name(attacker_name, online_sessions)
        defender = find_player_by_name(defender_name, online_sessions)
        
        # Skip if we can't find both players
        if not attacker or not defender:
            continue
        
        attacker_sid = find_player_sid(attacker_name, online_sessions)
        defender_sid = find_player_sid(defender_name, online_sessions)
        
        # Skip if we can't find the session IDs
        if not attacker_sid or not defender_sid:
            continue
        
        # Get attacker's weapon
        attacker_weapon = None
        if attacker_name in active_combats:
            attacker_weapon = active_combats[attacker_name]['weapon']
        
        # Process attack
        await process_combat_attack(
            attacker, defender, 
            attacker_weapon,
            attacker_sid, defender_sid,
            player_manager, game_state, online_sessions, sio, utils
        )
        
        # Toggle initiative (if both players still exist in combat)
        if (attacker_name in active_combats and 
            defender_name in active_combats):
            
            # Attacker loses initiative, defender gains it
            if attacker_name in active_combats:
                active_combats[attacker_name]['initiative'] = False
            if defender_name in active_combats:
                active_combats[defender_name]['initiative'] = True

async def process_combat_attack(attacker, defender, weapon, attacker_sid, defender_sid, 
                               player_manager, game_state, online_sessions, sio, utils):
    """
    Process a single attack in combat.
    
    Args:
        attacker (Player): The attacking player
        defender (Player): The defending player
        weapon (Item): Optional weapon item
        attacker_sid (str): The attacker's session ID
        defender_sid (str): The defender's session ID
        player_manager (PlayerManager): The player manager
        game_state (GameState): The game state
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
    """
    # Verify that the weapon is still in the attacker's inventory
    weapon_in_inventory = False
    if weapon:
        for item in attacker.inventory:
            if item == weapon:  # Check if the same object is still in inventory
                weapon_in_inventory = True
                break
        
        # If weapon is no longer in inventory, update combat info to unarmed
        if not weapon_in_inventory:
            weapon = None
            # Update the attacker's combat info
            if attacker.name in active_combats:
                active_combats[attacker.name]['weapon'] = None
    
    # Calculate base damage based on attacker's strength and weapon
    weapon_bonus = getattr(weapon, 'damage', 5) if weapon else 0
    base_damage = (attacker.strength // 15) + weapon_bonus
    
    # Add random variation (±30%)
    variation = random.uniform(0.7, 1.3)
    damage = max(1, int(base_damage * variation))
    
    # Calculate hit chance based on attacker's dexterity versus defender's
    hit_chance = min(90, 50 + (attacker.dexterity - defender.dexterity) // 2)
    
    # Determine if the attack hits
    roll = random.randint(1, 100)
    
    if roll <= hit_chance:
        # Attack hits - apply damage to defender
        defender.stamina = max(0, defender.stamina - damage)
        
        # Send messages about the hit
        if damage > base_damage:  # Critical hit (high roll)
            attack_msg_attacker = CombatDialogue.get_player_hit_message(defender.name, weapon)
            attack_msg_defender = CombatDialogue.get_opponent_hit_message(attacker.name, weapon)
        else:  # Normal hit
            attack_msg_attacker = CombatDialogue.get_player_hit_message(defender.name, weapon)
            attack_msg_defender = CombatDialogue.get_opponent_hit_message(attacker.name, weapon)
        
        # For heavier hits, add a recovery message for the defender
        if damage > base_damage * 0.8:
            attack_msg_defender += "\n" + CombatDialogue.get_heavy_damage_recovery()
        
        # Send messages
        await utils.send_message(sio, attacker_sid, attack_msg_attacker)
        await utils.send_message(sio, defender_sid, attack_msg_defender)
        
        # Update defender's stats display
        await utils.send_stats_update(sio, defender_sid, defender)
        
        # Check if defender is defeated
        if defender.stamina <= 0:
            await handle_player_defeat(attacker, defender, defender_sid, game_state, player_manager, online_sessions, sio, utils)
    else:
        # Attack misses
        miss_msg_attacker = CombatDialogue.get_player_miss_message(defender.name)
        miss_msg_defender = CombatDialogue.get_opponent_miss_message(attacker.name)
        
        await utils.send_message(sio, attacker_sid, miss_msg_attacker)
        await utils.send_message(sio, defender_sid, miss_msg_defender)

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
    """
    # End combat tracking for both players
    end_combat(attacker.name, defender.name)
    
    # Drop all defender's items in the current room
    current_room = game_state.get_room(defender.current_room)
    
    for item in list(defender.inventory):
        defender.remove_item(item)
        current_room.add_item(item)
    
    # Zero out defender's points completely when they die
    points_lost = defender.points
    points_gained = max(100, points_lost // 2)  # Victor gets half or at least 100 points
    
    # Transfer the points - use add_points to properly update levels
    defender.add_points(-points_lost, sio, online_sessions, send_notification=False)  # Zero out points
    attacker.add_points(points_gained, sio, online_sessions, send_notification=False)  # Award points to winner
    
    # Respawn at spawn room
    old_room = defender.current_room
    defender.set_current_room(player_manager.spawn_room)
    
    # Reset stamina to a percentage of max (e.g., 50%)
    defender.stamina = defender.max_stamina // 2
    
    # Save changes
    player_manager.save_players()
    
    # Find attacker's session ID
    attacker_sid = find_player_sid(attacker.name, online_sessions)
    
    # Get attacker's weapon
    attacker_weapon = None
    if attacker.name in active_combats:
        attacker_weapon = active_combats[attacker.name]['weapon']
    
    # Get killing blow message
    killing_blow_msg = CombatDialogue.get_killing_blow_message(defender.name, attacker_weapon)
    
    # Notify the defender of their defeat
    if defender_sid and sio and utils:
        defeat_msg = f"{attacker.name} has defeated you! You've lost ALL your points.\n"
        defeat_msg += "All your items have been dropped.\n"
        defeat_msg += "You've been returned to the village center."
        
        await utils.send_message(sio, defender_sid, defeat_msg)
        await utils.send_stats_update(sio, defender_sid, defender)
        
        # Send the new room description to the defender
        spawn_room = game_state.get_room(player_manager.spawn_room)
        if spawn_room:
            await utils.send_message(sio, defender_sid, 
                                   f"{spawn_room.name}\n{spawn_room.description}")
    
    # Notify the attacker of their victory with the killing blow message
    if attacker_sid and sio and utils:
        points_msg = f"[{attacker.points}]"
        await utils.send_message(sio, attacker_sid, points_msg)
        await utils.send_message(sio, attacker_sid, killing_blow_msg)
        await utils.send_stats_update(sio, attacker_sid, attacker)
    
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

# ===== HELPER FUNCTIONS =====
def find_player_sid(player_name_or_obj, online_sessions):
    """Find a player's session ID from their name or object."""
    for sid, session in online_sessions.items():
        player = session.get('player')
        if player:
            if isinstance(player_name_or_obj, str):
                if player.name.lower() == player_name_or_obj.lower():
                    return sid
            else:
                if player == player_name_or_obj:
                    return sid
    return None

def find_player_by_name(player_name, online_sessions):
    """Find a player object from their name."""
    for session in online_sessions.values():
        player = session.get('player')
        if player and player.name.lower() == player_name.lower():
            return player
    return None

def end_combat(player1_name, player2_name):
    """End combat between two players."""
    if player1_name in active_combats:
        del active_combats[player1_name]
    if player2_name in active_combats:
        del active_combats[player2_name]

def is_in_combat(player_name):
    """Check if a player is in combat."""
    return player_name in active_combats

# Add restriction checking function to command executor
def check_command_restrictions(cmd, player, sio=None, sid=None, utils=None):
    """
    Check if a command is allowed to be executed based on player state.
    
    Args:
        cmd (dict): The parsed command
        player (Player): The player executing the command
        sio (SocketIO, optional): Socket.IO instance for sending messages
        sid (str, optional): Session ID for sending messages
        utils (module, optional): Utilities module for sending messages
        
    Returns:
        tuple: (allowed, message) - Whether the command is allowed and an error message if not
    """
    verb = cmd.get("verb", "").lower()
    
    # Check if player is in combat and trying to use a restricted command
    if player.name in active_combats and verb in RESTRICTED_COMMANDS:
        if verb in ["north", "south", "east", "west", "northeast", "northwest", 
                   "southeast", "southwest", "up", "down", "in", "out", 
                   "n", "s", "e", "w", "ne", "nw", "se", "sw", "u", "d"]:
            return False, "You can't move while in combat! Use 'flee <direction>' instead."
        elif verb == "quit":
            return False, "You can't quit while in combat! That would be cowardice."
        else:
            return False, f"You can't use '{verb}' while in combat!"
    
    return True, ""

# Function to handle player disconnection during combat
async def handle_combat_disconnect(player_name, online_sessions, player_manager, game_state, sio, utils):
    """
    Handle when a player disconnects during combat.
    
    Args:
        player_name (str): The name of the disconnected player
        online_sessions (dict): Online sessions dictionary
        player_manager (PlayerManager): The player manager
        game_state (GameState): The game state
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
    """
    if player_name in active_combats:
        # Get opponent info
        combat_info = active_combats[player_name]
        opponent = combat_info['target']
        opponent_sid = combat_info['target_sid']
        
        # Get player object if available
        player = None
        for session in online_sessions.values():
            if session.get('player') and session['player'].name == player_name:
                player = session['player']
                break
        
        if not player:
            # Player is fully disconnected
            # Just notify opponent and end combat
            end_combat(player_name, opponent.name)
            
            if opponent_sid and sio and utils:
                disconnect_msg = f"{player_name} has disconnected during combat. You win by default!"
                await utils.send_message(sio, opponent_sid, disconnect_msg)
            return
        
        # If player object exists, treat it similar to a defeat
        current_room = game_state.get_room(player.current_room)
        
        # Drop all player's items
        for item in list(player.inventory):
            player.remove_item(item)
            current_room.add_item(item)
        
        # Zero out points and give half to opponent
        points_lost = player.points
        points_gained = max(100, points_lost // 2)
        
        # Use add_points to properly update levels
        player.add_points(-points_lost, sio, online_sessions, send_notification=False)  # Zero out points
        opponent.add_points(points_gained, sio, online_sessions, send_notification=False)  # Award points to opponent
        
        # End combat
        end_combat(player_name, opponent.name)
        
        # Notify opponent with points in brackets first, then a victory message
        if opponent_sid and sio and utils:
            # Display points in brackets MUD1-style
            points_msg = f"[{opponent.points}]"
            await utils.send_message(sio, opponent_sid, points_msg)
            
            # Then show the disconnect victory message
            disconnect_msg = f"{player_name} has disconnected during combat!"
            await utils.send_message(sio, opponent_sid, disconnect_msg)
            await utils.send_stats_update(sio, opponent_sid, opponent)
        
        # Save changes
        player_manager.save_players()

# Register combat commands
command_registry.register("attack", handle_attack, "Attack a target (player or NPC).")
command_registry.register("retaliate", handle_retaliate, "Use a weapon in combat. Usage: retaliate with <weapon>")
command_registry.register("flee", handle_flee, "Escape from combat, dropping all items and losing some points.")

# Register aliases
command_registry.register_alias("kill", "attack")
command_registry.register_alias("fight", "attack")
command_registry.register_alias("k", "attack")
command_registry.register_alias("ret", "retaliate")
command_registry.register_alias("run", "flee")