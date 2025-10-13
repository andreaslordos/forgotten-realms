# backend/commands/combat.py

import random
import logging
import inspect
from commands.registry import command_registry
from models.Weapon import Weapon
from models.CombatDialogue import CombatDialogue
from commands.rest import wake_player
from models.Item import Item

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global dictionary to track active combat sessions
active_combats = {}

# List of commands that are blocked during combat
RESTRICTED_COMMANDS = [
    "north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest",
    "up", "down", "in", "out", "n", "s", "e", "w", "ne", "nw", "se", "sw", "u", "d",
    "quit", "password", "set", "reset"
]

async def handle_attack(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle attacking a target, initiating continuous combat.
    """
    from models.Mobile import Mobile

    # Get the subject (target) from the parsed command
    subject = cmd.get("subject")
    subject_obj = cmd.get("subject_object")

    # Get the optional instrument (weapon) from the parsed command
    instrument = cmd.get("instrument")
    instrument_obj = cmd.get("instrument_object")

    if not subject and not subject_obj:
        return "Who do you want to attack?"

    # Check if player is already in combat
    if player.name in active_combats:
        existing_target = active_combats[player.name]['target']
        return f"You're already fighting {existing_target.name}!"

    # Find a player target in the room
    target_player = None
    target_sid = None

    # If we have a bound subject object that's a player (NOT a mob)
    if (subject_obj and
        not isinstance(subject_obj, Mobile) and
        hasattr(subject_obj, 'name') and
        hasattr(subject_obj, 'current_room')):
        if subject_obj.current_room == player.current_room and subject_obj != player:
            target_player = subject_obj
            
            # Find their session ID
            for sid, session_data in online_sessions.items():
                if session_data.get('player') == target_player:
                    target_sid = sid
                    
                    # Check if target is sleeping and wake them up
                    if session_data.get('sleeping'):
                        await wake_player(target_player, sid, online_sessions, sio, utils, woken_by=player)
                    break
    else:
        # Find a player by name
        if online_sessions:
            for sid, session_data in online_sessions.items():
                other_player = session_data.get('player')
                if (other_player and 
                    other_player.current_room == player.current_room and 
                    other_player != player and
                    subject and subject.lower() in other_player.name.lower()):
                    target_player = other_player
                    target_sid = sid
                    
                    # Check if target is sleeping and wake them up
                    if session_data.get('sleeping'):
                        await wake_player(other_player, sid, online_sessions, sio, utils, woken_by=player)
                    break
    
    # If a player target was found
    if target_player:
        # Use the bound weapon if available, otherwise try to find it by name
        weapon_item = None
        
        if instrument_obj and isinstance(instrument_obj, (Weapon, Item)) and instrument_obj in player.inventory:
            weapon_item = instrument_obj
            
            # Check if it's a Weapon class with requirements
            if isinstance(weapon_item, Weapon):
                can_use, reason = weapon_item.can_use(player)
                if not can_use:
                    return reason
        elif instrument:
            # Find weapon in inventory by name
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
            'last_turn': None,   # No turn has happened yet
            'is_mob': False,
            'entity': player,
        }
        
        # Start combat tracking for target
        active_combats[target_player.name] = {
            'target': player,
            'target_sid': player_sid,
            'weapon': None,  # Target starts barehanded
            'initiative': False,  # Defender doesn't have initiative
            'last_turn': None,    # No turn has happened yet
            'is_mob': False,
            'entity': target_player,
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
        # Look for a mob target in the room
        # Import mob_manager from the command context (passed via utils or global)
        # For now, we'll check if mob_manager is available
        mob_manager = getattr(utils, 'mob_manager', None) if hasattr(utils, '__dict__') else None

        if mob_manager:
            mobs_in_room = mob_manager.get_mobs_in_room(player.current_room)
            target_mob = None

            # Try to find mob by bound object first
            if subject_obj and hasattr(subject_obj, 'is_mob'):
                target_mob = subject_obj
            else:
                # Find mob by name
                for mob in mobs_in_room:
                    if subject and subject.lower() in mob.name.lower():
                        target_mob = mob
                        break

            if target_mob:
                # Check if player is already in combat
                if player.name in active_combats:
                    existing_target = active_combats[player.name]['target']
                    return f"You're already fighting {existing_target.name}!"

                # Parse weapon (same logic as for player targets)
                weapon_item = None

                if instrument_obj and isinstance(instrument_obj, (Weapon, Item)) and instrument_obj in player.inventory:
                    weapon_item = instrument_obj

                    # Check if it's a Weapon class with requirements
                    if isinstance(weapon_item, Weapon):
                        can_use, reason = weapon_item.can_use(player)
                        if not can_use:
                            return reason
                elif instrument:
                    # Find weapon in inventory by name
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

                # Get player session ID
                player_sid = find_player_sid(player, online_sessions)

                # Attack the mob
                return await handle_mob_attack(player, target_mob, weapon_item, player_sid,
                                              player_manager, game_state, online_sessions, mob_manager, sio, utils)

        return f"You don't see '{subject}' here."

async def handle_retaliate(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle retaliating with a weapon when already in combat.
    """
    # Get the instrument (weapon) from the parsed command
    instrument = cmd.get("instrument")
    instrument_obj = cmd.get("instrument_object")
    
    # Check if player is in combat
    if player.name not in active_combats:
        return "You're not in combat with anyone."
    
    # If no weapon specified
    if not instrument and not instrument_obj:
        return "Retaliate with what? Specify a weapon."
    
    # Use the bound weapon object if available
    weapon_item = None
    if instrument_obj and instrument_obj in player.inventory:
        weapon_item = instrument_obj
        
        # If it's a Weapon, check requirements
        if isinstance(weapon_item, Weapon):
            can_use, reason = weapon_item.can_use(player)
            if not can_use:
                return reason
        elif not hasattr(weapon_item, 'damage'):
            return f"{weapon_item.name} is not a weapon."
    else:
        # Find the weapon in inventory by name
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

async def handle_flee(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle fleeing from combat.
    """
    # Get the subject (direction) from the parsed command
    subject = cmd.get("subject")
    
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
    is_mob = combat_info.get('is_mob', False)

    # Check if opponent is a mob
    from models.Mobile import Mobile
    opponent_is_mob = isinstance(opponent, Mobile)

    # Drop all items in the current room
    for item in list(player.inventory):
        player.remove_item(item)
        current_room.add_item(item)

    # End combat using proper identifier (mob.id or player.name)
    opponent_identifier = opponent.id if opponent_is_mob else opponent.name
    end_combat(player.name, opponent_identifier)

    # Lose 20% of points when fleeing, and give those points to the opponent (if player)
    points_lost = player.points // 5  # 20% of points

    # Use add_points to properly update levels
    leveled_up, _ = player.add_points(-points_lost, sio, online_sessions, send_notification=False)

    # Only give points to opponent if they're a player (mobs don't have add_points)
    if not opponent_is_mob:
        opponent.add_points(points_lost, sio, online_sessions, send_notification=False)

    # Notify opponent (only if it's a player)
    if not opponent_is_mob and opponent_sid and utils and sio:
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
async def process_combat_tick(sio, online_sessions, player_manager, game_state, utils, mob_manager=None):
    """
    Process one tick of combat for all active combats (including mobs).
    This should be called regularly by the game's tick service.

    Args:
        sio (SocketIO): Socket.IO instance
        online_sessions (dict): Online sessions dictionary
        player_manager (PlayerManager): The player manager
        game_state (GameState): The game state
        utils (module): Utilities module
        mob_manager (MobManager, optional): The mob manager for mob combat
    """
    from models.Mobile import Mobile

    def _cleanup_entry(identifier):
        entry = active_combats.pop(identifier, None)
        if entry:
            entity = entry.get('entity')
            if isinstance(entity, Mobile):
                entity.target_player = None

    combat_players = list(active_combats.keys())
    processed_pairs = set()

    if combat_players:
        logger.info(f"Processing combat tick. Active combats: {combat_players}")

    for combat_key in combat_players:
        combat_entry = active_combats.get(combat_key)
        if not combat_entry:
            continue

        attacker_entity = combat_entry.get('entity')
        defender_entity = combat_entry.get('target')

        if not attacker_entity or not defender_entity:
            logger.debug("Skipping %s due to missing entity or target", combat_key)
            continue

        attacker_is_mob = isinstance(attacker_entity, Mobile)
        defender_is_mob = isinstance(defender_entity, Mobile)

        if attacker_is_mob and attacker_entity.state != "alive":
            logger.info("Cleaning up combat for dead mob %s", attacker_entity.id)
            _cleanup_entry(attacker_entity.id)
            continue

        if defender_is_mob and defender_entity.state != "alive":
            logger.info("Cleaning up combat for dead mob %s", defender_entity.id)
            _cleanup_entry(attacker_entity.id if attacker_is_mob else attacker_entity.name)
            _cleanup_entry(defender_entity.id)
            continue

        attacker_identifier = attacker_entity.id if attacker_is_mob else attacker_entity.name
        defender_identifier = defender_entity.id if defender_is_mob else defender_entity.name

        combat_pair = tuple(sorted([attacker_identifier, defender_identifier]))
        if combat_pair in processed_pairs:
            logger.info(f"Skipping pair {combat_pair} - already processed")
            continue
        processed_pairs.add(combat_pair)
        logger.info(f"Processing pair: {combat_pair}")

        defender_entry = active_combats.get(defender_identifier)

        attacker_entry_ref = combat_entry
        defender_entry_ref = defender_entry
        initiative_holder = None

        if not defender_entry:
            logger.info(
                "Defender entry missing for %s; removing attacker combat state",
                defender_identifier,
            )
            _cleanup_entry(attacker_identifier)
            continue

        if combat_entry.get('initiative'):
            initiative_holder = 'attacker'
        elif defender_entry and defender_entry.get('initiative'):
            initiative_holder = 'defender'
        else:
            combat_entry['initiative'] = True
            initiative_holder = 'attacker'

        if initiative_holder == 'attacker':
            attacker = attacker_entity
            defender = defender_entity
            attacker_key = attacker_identifier
            defender_key = defender_identifier
        else:
            if not defender_entry:
                logger.debug("Defender entry missing for %s; defaulting to attacker initiative", combat_pair)
                attacker = attacker_entity
                defender = defender_entity
                attacker_key = attacker_identifier
                defender_key = defender_identifier
                attacker_entry_ref = combat_entry
                defender_entry_ref = defender_entry
            else:
                attacker = defender_entry.get('entity')
                defender = defender_entry.get('target')
                attacker_key = defender_identifier
                defender_key = attacker_identifier
                attacker_entry_ref = defender_entry
                defender_entry_ref = combat_entry

        if not attacker or not defender:
            logger.error(
                "SKIPPING - attacker=%s, defender=%s, attacker_key=%s, defender_key=%s",
                attacker, defender, attacker_key, defender_key,
            )
            _cleanup_entry(attacker_key)
            _cleanup_entry(defender_key)
            continue

        attacker_is_mob = isinstance(attacker, Mobile)
        defender_is_mob = isinstance(defender, Mobile)

        attacker_sid = None if attacker_is_mob else find_player_sid(attacker, online_sessions)
        defender_sid = None if defender_is_mob else find_player_sid(defender, online_sessions)

        logger.info(
            "SID check - attacker_is_mob: %s, attacker_sid: %s, defender_is_mob: %s, defender_sid: %s",
            attacker_is_mob,
            attacker_sid,
            defender_is_mob,
            defender_sid,
        )

        if not attacker_is_mob and not attacker_sid:
            logger.warning(
                "Skipping - attacker %s is player but no SID found",
                attacker_identifier,
            )
            _cleanup_entry(attacker_identifier)
            continue
        if not defender_is_mob and not defender_sid:
            logger.warning(
                "Skipping - defender %s is player but no SID found",
                defender_identifier,
            )
            _cleanup_entry(attacker_identifier)
            _cleanup_entry(defender_identifier)
            continue

        attacker_weapon = attacker_entry_ref.get('weapon') if attacker_entry_ref else None

        if attacker_is_mob or defender_is_mob:
            if mob_manager:
                logger.info(
                    "Processing mob combat: %s vs %s",
                    attacker_identifier,
                    defender_identifier,
                )
                sid_for_attack = attacker_sid if not attacker_is_mob else defender_sid
                await process_mob_combat_attack(
                    attacker,
                    defender,
                    attacker_weapon,
                    sid_for_attack,
                    player_manager,
                    game_state,
                    online_sessions,
                    mob_manager,
                    sio,
                    utils,
                )
            else:
                logger.warning(
                    "Mob combat skipped - no mob_manager! Attacker: %s, Defender: %s",
                    attacker_identifier,
                    defender_identifier,
                )
        else:
            await process_combat_attack(
                attacker,
                defender,
                attacker_weapon,
                attacker_sid,
                defender_sid,
                player_manager,
                game_state,
                online_sessions,
                sio,
                utils,
            )

        if attacker_key in active_combats:
            active_combats[attacker_key]['initiative'] = False
            logger.info(f"Toggled {attacker_key} initiative to False")
        if defender_key in active_combats:
            active_combats[defender_key]['initiative'] = True
            logger.info(f"Toggled {defender_key} initiative to True")

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

def reset_player_persona(player):
    """
    Reset a player's persona to neophyte (level 0) state.

    Args:
        player (Player): The player to reset
    """
    from models.Levels import levels

    # Reset to level 0 (neophyte)
    level_data = levels[0]
    player.points = 0
    player.level = level_data['name']
    player.stamina = level_data['stamina']
    player.max_stamina = level_data['stamina']
    player.strength = level_data['strength']
    player.dexterity = level_data['dexterity']
    player.magic = level_data['magic']
    player.carrying_capacity_num = level_data['carrying_capacity_num']
    player.current_level_at = 0
    player.next_level_at = 400


async def handle_respawn_choice(player, choice, player_sid, game_state, player_manager, online_sessions, sio, utils, combat_death=True):
    """
    Handle a player's choice to respawn or disconnect after death.

    Args:
        player (Player): The player who died
        choice (str): The player's choice ("yes", "y", "no", or anything else)
        player_sid (str): The player's session ID
        game_state (GameState): The game state
        player_manager (PlayerManager): The player manager
        online_sessions (dict): Online sessions dictionary
        sio (SocketIO): Socket.IO instance
        utils (module): Utilities module
        combat_death (bool): Whether this was a combat death (True) or non-combat death (False)

    Returns:
        str or None: Response message if continuing, None if disconnecting
    """
    choice_lower = choice.lower().strip()

    if choice_lower in ['yes', 'y']:
        # Player wants to respawn
        if combat_death:
            # Combat death: reset persona
            reset_player_persona(player)

        # Respawn at spawn room
        player.set_current_room(player_manager.spawn_room)
        player.stamina = player.max_stamina

        # Clear the awaiting_respawn flag
        if player_sid in online_sessions:
            online_sessions[player_sid]['awaiting_respawn'] = False

        # Save changes
        player_manager.save_players()

        # Send welcome back message and room description (with other players)
        from commands.executor import build_look_description
        from services.notifications import broadcast_arrival
        mob_manager = getattr(utils, 'mob_manager', None) if hasattr(utils, '__dict__') else None

        welcome_msg = "You awaken in the village center.\n\n"
        room_desc = build_look_description(player, game_state, online_sessions, look=True, mob_manager=mob_manager)
        welcome_msg += room_desc

        await utils.send_message(sio, player_sid, welcome_msg)
        await utils.send_stats_update(sio, player_sid, player)

        # Notify other players at spawn of arrival
        await broadcast_arrival(player)

        return ""
    else:
        # Player chooses not to continue - disconnect them
        if player_sid in online_sessions:
            online_sessions[player_sid]['awaiting_respawn'] = False

        # Disconnect the player
        await utils.send_message(sio, player_sid, "Farewell! Thank you for playing.")
        # The actual disconnection should be handled by the caller
        return None


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
    old_room = defender.current_room

    for item in list(defender.inventory):
        defender.remove_item(item)
        current_room.add_item(item)

    # Transfer points to attacker
    points_lost = defender.points
    points_gained = max(100, points_lost // 2)  # Victor gets half or at least 100 points
    attacker.add_points(points_gained, sio, online_sessions, send_notification=False)

    # Save attacker's changes
    player_manager.save_players()

    # Find attacker's session ID
    attacker_sid = find_player_sid(attacker.name, online_sessions)

    # Get attacker's weapon
    attacker_weapon = None
    if attacker.name in active_combats:
        attacker_weapon = active_combats[attacker.name]['weapon']

    # Get killing blow message
    killing_blow_msg = CombatDialogue.get_killing_blow_message(defender.name, attacker_weapon)

    # Notify the attacker of their victory
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

    # Notify the defender and prompt for respawn choice
    if defender_sid and sio and utils:
        defeat_msg = f"{attacker.name} has defeated you!\n"
        defeat_msg += "All your items have been dropped.\n\n"
        defeat_msg += "Persona reset.\nWould you like to play again?"

        await utils.send_message(sio, defender_sid, defeat_msg)

        # Set flag indicating player is awaiting respawn choice
        # Also remove player from game world (limbo state)
        if defender_sid in online_sessions:
            online_sessions[defender_sid]['awaiting_respawn'] = True
            online_sessions[defender_sid]['combat_death'] = True

        # Put player in limbo (remove from game world)
        defender.current_room = None

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

# ===== MOB COMBAT FUNCTIONS =====
async def handle_mob_attack(player, mob, weapon, player_sid, player_manager, game_state, online_sessions, mob_manager, sio, utils):
    """
    Handle a player attacking a mob.

    Args:
        player (Player): The attacking player
        mob (Mobile): The target mob
        weapon (Weapon): Optional weapon
        player_sid (str): Player's session ID
        player_manager (PlayerManager): Player manager instance
        game_state (GameState): Game state instance
        online_sessions (dict): Online sessions
        mob_manager (MobManager): Mob manager instance
        sio: Socket.IO instance
        utils: Utils module

    Returns:
        str: Result message
    """
    # Start combat tracking for player
    active_combats[player.name] = {
        'target': mob,
        'target_sid': None,  # Mobs don't have session IDs
        'weapon': weapon,
        'initiative': True,  # Attacker starts with initiative
        'last_turn': None,
        'is_mob': False,  # Player is not a mob
        'entity': player,
    }

    # Start combat tracking for mob
    active_combats[mob.id] = {
        'target': player,
        'target_sid': player_sid,
        'weapon': None,  # Mobs use their base damage
        'initiative': False,  # Defender doesn't have initiative
        'last_turn': None,
        'is_mob': True,  # This is a mob
        'entity': mob,
    }

    # Set mob's target
    mob.target_player = player

    # Notify others in the room
    current_room = game_state.get_room(player.current_room)
    if current_room and online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and
                other_player.current_room == player.current_room and
                other_player != player):
                await utils.send_message(sio, sid, f"{player.name} attacks {mob.name}!")

    # Immediate first attack
    await process_mob_combat_attack(player, mob, weapon, player_sid,
                                    player_manager, game_state, online_sessions, mob_manager, sio, utils)

    # Toggle initiative after immediate attack so combat alternates properly
    if player.name in active_combats and mob.id in active_combats:
        active_combats[player.name]['initiative'] = False
        active_combats[mob.id]['initiative'] = True

    result = f"You attack {mob.name}"
    if weapon:
        result += f" with {weapon.name}"
    result += "!"

    return result


async def mob_initiate_attack(mob, player, player_sid, player_manager, game_state, online_sessions, sio, utils):
    """
    Handle a mob initiating an attack on a player.

    Args:
        mob (Mobile): The attacking mob
        player (Player): The target player
        player_sid (str): Player's session ID
        player_manager (PlayerManager): Player manager instance
        game_state (GameState): Game state instance
        online_sessions (dict): Online sessions
        sio: Socket.IO instance
        utils: Utils module
    """
    # Check if mob or player is already in combat
    if mob.id in active_combats or player.name in active_combats:
        return

    # Start combat tracking for mob
    active_combats[mob.id] = {
        'target': player,
        'target_sid': player_sid,
        'weapon': None,
        'initiative': True,  # Mob gets initiative
        'last_turn': None,
        'is_mob': True,
        'entity': mob,
    }

    # Start combat tracking for player
    active_combats[player.name] = {
        'target': mob,
        'target_sid': None,
        'weapon': None,  # Player starts barehanded
        'initiative': False,
        'last_turn': None,
        'is_mob': False,
        'entity': player,
    }

    # Set mob's target
    mob.target_player = player

    # Notify the player
    attack_msg = f"{mob.name.capitalize()} attacks you! Combat has begun. Type 'ret with <weapon>' to use a weapon or 'flee <direction>' to escape."
    await utils.send_message(sio, player_sid, attack_msg)

    # Immediate first attack from the mob
    await process_mob_combat_attack(mob, player, None, None,
                                    player_manager, game_state, online_sessions, None, sio, utils)


async def process_mob_combat_attack(attacker, defender, weapon, attacker_sid,
                                   player_manager, game_state, online_sessions, mob_manager, sio, utils):
    """
    Process a combat attack involving a mob (either attacking or being attacked).

    Args:
        attacker: The attacker (Player or Mobile)
        defender: The defender (Player or Mobile)
        weapon: Optional weapon (for player attacks)
        attacker_sid: Attacker's session ID (None if mob)
        player_manager: Player manager instance
        game_state: Game state instance
        online_sessions: Online sessions
        mob_manager: Mob manager instance (can be None)
        sio: Socket.IO instance
        utils: Utils module
    """
    from models.Mobile import Mobile

    # Determine if attacker/defender are mobs
    attacker_is_mob = isinstance(attacker, Mobile)
    defender_is_mob = isinstance(defender, Mobile)

    # Verify weapon is in inventory (for player attackers)
    if not attacker_is_mob and weapon:
        weapon_in_inventory = weapon in attacker.inventory
        if not weapon_in_inventory:
            weapon = None
            if attacker.name in active_combats:
                active_combats[attacker.name]['weapon'] = None

    # Calculate damage
    if attacker_is_mob:
        base_damage = attacker.damage
    else:
        weapon_bonus = getattr(weapon, 'damage', 5) if weapon else 0
        base_damage = (attacker.strength // 15) + weapon_bonus

    # Add random variation (±30%)
    variation = random.uniform(0.7, 1.3)
    damage = max(1, int(base_damage * variation))

    # Calculate hit chance
    hit_chance = min(90, 50 + (attacker.dexterity - defender.dexterity) // 2)

    # Determine if attack hits
    roll = random.randint(1, 100)

    if roll <= hit_chance:
        # Attack hits
        if defender_is_mob:
            is_dead, remaining_stamina = defender.take_damage(damage)
        else:
            defender.stamina = max(0, defender.stamina - damage)
            is_dead = defender.stamina <= 0

        # Send hit messages
        if attacker_is_mob:
            # Mob hit player
            hit_msg = f"{attacker.name.capitalize()} strikes you for {damage} damage!"
            if attacker_sid:  # attacker_sid is actually defender_sid when mob attacks
                await utils.send_message(sio, attacker_sid, hit_msg)
                # Find the correct defender SID
                defender_sid = find_player_sid(defender, online_sessions)
                if defender_sid:
                    await utils.send_stats_update(sio, defender_sid, defender)
        else:
            # Player hit mob
            hit_msg = f"You strike {defender.name} for {damage} damage!"
            if attacker_sid:
                await utils.send_message(sio, attacker_sid, hit_msg)

        # Check for death
        if is_dead:
            if defender_is_mob:
                await handle_mob_defeat(attacker, defender, attacker_sid, game_state, player_manager, online_sessions, mob_manager, sio, utils)
            else:
                # Player was defeated by mob
                await handle_player_defeat_by_mob(attacker, defender, game_state, player_manager, online_sessions, sio, utils)
    else:
        # Attack misses
        if attacker_is_mob:
            miss_msg = f"{attacker.name.capitalize()} attacks but misses!"
            defender_sid = find_player_sid(defender, online_sessions)
            if defender_sid:
                await utils.send_message(sio, defender_sid, miss_msg)
        else:
            miss_msg = f"You swing at {defender.name} but miss!"
            if attacker_sid:
                await utils.send_message(sio, attacker_sid, miss_msg)


async def handle_mob_defeat(player, mob, player_sid, game_state, player_manager, online_sessions, mob_manager, sio, utils):
    """
    Handle when a player defeats a mob.

    Args:
        player (Player): The victorious player
        mob (Mobile): The defeated mob
        player_sid (str): Player's session ID
        game_state (GameState): Game state instance
        player_manager (PlayerManager): Player manager instance
        online_sessions (dict): Online sessions
        mob_manager (MobManager): Mob manager instance
        sio: Socket.IO instance
        utils: Utils module
    """
    # End combat
    if player.name in active_combats:
        del active_combats[player.name]
    if mob.id in active_combats:
        del active_combats[mob.id]

    mob.target_player = None

    # Award points
    if mob.point_value > 0:
        player.add_points(mob.point_value, sio, online_sessions, send_notification=True)

    # Drop loot
    current_room = game_state.get_room(mob.current_room)
    loot_dropped = mob.drop_loot()

    if loot_dropped and current_room:
        for item in loot_dropped:
            current_room.add_item(item)

    # Victory message
    victory_msg = f"You have slain {mob.name}!"
    if mob.point_value > 0:
        victory_msg += f" You gain {mob.point_value} points!"

    if loot_dropped:
        loot_names = ", ".join(item.name for item in loot_dropped)
        victory_msg += f"\n{mob.name.capitalize()} dropped: {loot_names}"

    if player_sid:
        await utils.send_message(sio, player_sid, victory_msg)
        await utils.send_stats_update(sio, player_sid, player)

    # Notify others in room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and
                other_player.current_room == mob.current_room and
                other_player != player):
                await utils.send_message(sio, sid, f"{player.name} has slain {mob.name}!")

    # Remove mob from game
    if mob_manager:
        mob_manager.remove_mob(mob.id, game_state)

    # Save
    player_manager.save_players()


async def handle_player_defeat_by_mob(mob, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle when a mob defeats a player.

    Args:
        mob (Mobile): The victorious mob
        player (Player): The defeated player
        game_state (GameState): Game state instance
        player_manager (PlayerManager): Player manager instance
        online_sessions (dict): Online sessions
        sio: Socket.IO instance
        utils: Utils module
    """
    # End combat
    if mob.id in active_combats:
        del active_combats[mob.id]
    if player.name in active_combats:
        del active_combats[player.name]

    mob.target_player = None

    # Drop all items
    current_room = game_state.get_room(player.current_room)
    old_room = player.current_room

    for item in list(player.inventory):
        player.remove_item(item)
        current_room.add_item(item)

    # Notify others in old room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and
                other_player.current_room == old_room and
                other_player != player):
                await utils.send_message(sio, sid, f"{mob.name.capitalize()} has defeated {player.name}!")

    # Notify player and prompt for respawn choice
    player_sid = find_player_sid(player, online_sessions)
    if player_sid:
        defeat_msg = f"{mob.name.capitalize()} has defeated you!\n"
        defeat_msg += "All your items have been dropped.\n\n"
        defeat_msg += "Persona reset.\nWould you like to play again?"

        await utils.send_message(sio, player_sid, defeat_msg)

        # Set flag indicating player is awaiting respawn choice
        # Also remove player from game world (limbo state)
        if player_sid in online_sessions:
            online_sessions[player_sid]['awaiting_respawn'] = True
            online_sessions[player_sid]['combat_death'] = True

        # Put player in limbo (remove from game world)
        player.current_room = None


async def handle_non_combat_death(player, player_sid, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle when a player dies from non-combat sources (traps, etc.).

    Args:
        player (Player): The defeated player
        player_sid (str): The player's session ID
        game_state (GameState): Game state instance
        player_manager (PlayerManager): Player manager instance
        online_sessions (dict): Online sessions
        sio: Socket.IO instance
        utils: Utils module
    """
    # Drop all items in current room
    current_room = game_state.get_room(player.current_room)
    old_room = player.current_room

    for item in list(player.inventory):
        player.remove_item(item)
        current_room.add_item(item)

    # Notify others in the room
    if online_sessions and sio and utils:
        for sid, session_data in online_sessions.items():
            other_player = session_data.get('player')
            if (other_player and
                other_player.current_room == old_room and
                other_player != player):
                await utils.send_message(sio, sid, f"{player.name} has died!")

    # Notify player and prompt for respawn choice
    if player_sid and sio and utils:
        death_msg = "You have died!\n"
        death_msg += "All your items have been dropped.\n\n"
        death_msg += "Persona updated.\nWould you like to play again?"

        await utils.send_message(sio, player_sid, death_msg)

        # Set flag indicating player is awaiting respawn choice
        # Also remove player from game world (limbo state)
        if player_sid in online_sessions:
            online_sessions[player_sid]['awaiting_respawn'] = True
            online_sessions[player_sid]['combat_death'] = False  # Non-combat death

        # Put player in limbo (remove from game world)
        player.current_room = None

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

# Log the registrations for verification
logger.info("Registered command aliases: 'kill', 'fight', 'k' → 'attack'")
