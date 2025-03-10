# backend/commands/interaction.py with extensive debugging

from commands.registry import command_registry
from commands.executor import build_look_description
import logging
import json
import traceback

# Set up logging with more verbosity
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def handle_interaction(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle specific verb-object interactions with extended debugging.
    """
    try:
        verb = cmd["verb"]
        subject = cmd.get("subject")
        instrument = cmd.get("instrument")
        
        # Debug log command parsing
        logger.debug(f"==== INTERACTION DEBUG ====")
        logger.debug(f"CMD: {json.dumps(cmd)}")
        logger.debug(f"Processing: verb={verb}, subject={subject}, instrument={instrument}")
        
        if not subject:
            return f"What do you want to {verb}?"
        
        # Look for the target item in the room or inventory
        target_item = None
        instrument_item = None
        
        # Check player's inventory for subject
        for item in player.inventory:
            if subject.lower() in item.name.lower():
                target_item = item
                logger.debug(f"Found target item in inventory: {item.name}")
                break
        
        # If not in inventory, check the room (including hidden but visible items)
        current_room = None
        if not target_item:
            current_room = game_state.get_room(player.current_room)
            logger.debug(f"Looking for item in room: {current_room.room_id}")
            
            # Check all visible items in the room
            visible_items = current_room.get_items(game_state)
            logger.debug(f"Visible items in room: {[item.name for item in visible_items]}")
            for item in visible_items:
                if subject.lower() in item.name.lower():
                    target_item = item
                    logger.debug(f"Found target item in room: {item.name}")
                    # Set the room_id for the item if it has the attribute
                    if hasattr(item, 'set_room_id'):
                        item.set_room_id(current_room.room_id)
                        logger.debug(f"Set room_id to {current_room.room_id}")
                    break
        
        if not target_item:
            return f"You don't see '{subject}' here."
        
        # Debug item properties
        logger.debug(f"Target item properties:")
        logger.debug(f"  Name: {target_item.name}")
        logger.debug(f"  ID: {getattr(target_item, 'id', 'No ID')}")
        logger.debug(f"  Has interactions: {hasattr(target_item, 'interactions')}")
        
        # If it's not a StatefulItem or doesn't have interactions attribute
        if not hasattr(target_item, 'interactions'):
            return f"You can't {verb} the {target_item.name}."
        
        # Debug the interactions dictionary
        logger.debug(f"Interactions dict: {target_item.interactions}")
        logger.debug(f"Looking for verb: {verb}")
        logger.debug(f"Verb is present: {verb in target_item.interactions}")
        
        # Check if the verb is supported for this item
        if verb not in target_item.interactions:
            return f"You can't {verb} the {target_item.name}."
        
        # Get all possible interactions for this verb
        possible_interactions = target_item.interactions[verb]
        logger.debug(f"Possible interactions: {possible_interactions}")
        logger.debug(f"Type of possible_interactions: {type(possible_interactions)}")
        
        # Make sure we're dealing with a list
        if not isinstance(possible_interactions, list):
            logger.debug(f"Converting interaction to list for backward compatibility")
            possible_interactions = [possible_interactions]  # Backward compatibility
        
        # Debug each possible interaction
        for i, inter in enumerate(possible_interactions):
            logger.debug(f"Interaction {i}: {inter}")
            logger.debug(f"Type of interaction: {type(inter)}")
            if isinstance(inter, dict):
                logger.debug(f"Keys: {inter.keys()}")
            else:
                logger.debug(f"NOT A DICTIONARY - THIS IS THE PROBLEM")
        
        # Find the appropriate interaction based on current state and conditions
        valid_interaction = None
        for interaction in possible_interactions:
            logger.debug(f"Checking interaction compatibility")
            
            if not isinstance(interaction, dict):
                logger.debug(f"SKIPPING: Not a dictionary")
                continue
                
            # Check if this interaction is valid for the current state
            if 'from_state' in interaction:
                from_state = interaction['from_state']
                logger.debug(f"Interaction requires state: {from_state}")
                logger.debug(f"Item current state: {target_item.state}")
                
                if from_state is not None and from_state != target_item.state:
                    logger.debug(f"SKIPPING: State mismatch")
                    continue
            
            # We found a match for the current state (or one with no state requirement)
            logger.debug(f"Found valid interaction")
            valid_interaction = interaction
            break
        
        # If no valid interaction was found
        if not valid_interaction:
            logger.debug(f"No valid interaction found")
            return f"You can't {verb} the {target_item.name} in its current state."
        
        logger.debug(f"Valid interaction: {valid_interaction}")
        
        # If an instrument is required, find it
        if 'required_instrument' in valid_interaction:
            required_instrument = valid_interaction['required_instrument']
            logger.debug(f"Required instrument: {required_instrument}")
            
            if required_instrument:
                if not instrument:
                    return f"You need something to {verb} the {target_item.name} with."
                
                # Look for the instrument in inventory
                for item in player.inventory:
                    if instrument.lower() in item.name.lower():
                        instrument_item = item
                        logger.debug(f"Found instrument: {item.name}")
                        break
                
                if not instrument_item:
                    return f"You don't have '{instrument}'."
                
                # Check if it's the right type of instrument
                if required_instrument.lower() not in instrument_item.name.lower():
                    return f"You can't {verb} the {target_item.name} with that."
        
        # Check any additional conditions
        if 'conditional_fn' in valid_interaction and valid_interaction['conditional_fn']:
            logger.debug(f"Checking conditional function")
            conditional_fn = valid_interaction['conditional_fn']
            if not conditional_fn(player, game_state):
                return f"You can't {verb} the {target_item.name} right now."
        
        # All conditions met, perform the interaction
        if 'target_state' in valid_interaction and valid_interaction['target_state']:
            target_state = valid_interaction['target_state']
            logger.debug(f"Setting item state to: {target_state}")
            target_item.set_state(target_state, game_state)
        
        # Get the success message
        logger.debug(f"Getting success message")
        message = f"You {verb} the {target_item.name}."
        if 'message' in valid_interaction:
            message = valid_interaction['message']
            logger.debug(f"Using custom message: {message}")
        
        # Handle exit modifications
        logger.debug(f"Checking for exit modifications")
        add_exit = None
        remove_exit = None
        
        if 'add_exit' in valid_interaction:
            add_exit = valid_interaction['add_exit']
            logger.debug(f"Adding exit: {add_exit}")
            
        if 'remove_exit' in valid_interaction:
            remove_exit = valid_interaction['remove_exit']
            logger.debug(f"Removing exit: {remove_exit}")
        
        if 'show_room_desc' in valid_interaction:
            show_room_desc = valid_interaction['show_room_desc']
            logger.debug(f"Show room desc: {show_room_desc}")
        else:
            show_room_desc = False
        
        if add_exit or remove_exit:
            logger.debug(f"Handling exit changes")
            # player_manager.save_players()  # Save state - uncomment if needed
            if show_room_desc:
                return f"{message}\n\n{build_look_description(player, game_state, online_sessions)}"
            
            # Otherwise just mention the exit change
            exit_msg = ""
            if add_exit:
                direction, _ = add_exit
                exit_msg = f" You can now go {direction}."
            return f"{message}{exit_msg}"
        
        logger.debug(f"Interaction completed successfully")
        return message
        
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Exception in interaction handler: {e}")
        logger.error(error_trace)
        return f"Error processing command: {str(e)}\n(Debug trace has been logged)"

# List of common interaction verbs to register
common_interaction_verbs = [
    "open", "close", "push", "pull", "turn", "twist", "light", "extinguish", 
    "cut", "break", "chop", "hit", "move", "unlock", "lock", "knock", "read"
]

# Register all the interaction verbs
def register_interaction_verbs():
    for verb in common_interaction_verbs:
        command_registry.register(verb, handle_interaction, 
                                 f"{verb.capitalize()} something, optionally with an instrument.")

# Call this function to register all verbs
register_interaction_verbs()