# Update to interaction handler for notifications

from commands.registry import command_registry
from commands.executor import build_look_description
import logging
import traceback
from services.notifications import broadcast_room  # Use existing notification service

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def handle_interaction(cmd, player, game_state, player_manager, online_sessions, sio, utils):
    """
    Handle specific verb-object interactions with better support for:
    - 'open door with key' (traditional)
    - 'tie rope to well' (reversed format)
    - 'unlock chest using key' (with preposition variants)
    """
    try:
        verb = cmd.get("verb")
        subject = cmd.get("subject")
        instrument = cmd.get("instrument")
        preposition = cmd.get("preposition", "with")  # Default preposition
        reversed_syntax = cmd.get("reversed_syntax", False)  # Flag for reversed syntax
        
        if not subject:
            return f"What do you want to {verb}?"
        
        # In REVERSED syntax (tie rope to well), we need:
        # - primary_item = well (the item with the interaction)
        # - secondary_item = rope (the instrument used)
        
        # In STANDARD syntax (unlock door with key), we need:
        # - primary_item = door (the item with the interaction)
        # - secondary_item = key (the instrument used)
            
        # Initialize our search variables
        primary_item = None
        secondary_item = None
        current_room = game_state.get_room(player.current_room)
        
        if reversed_syntax:
            # In reversed syntax, first find the intended target in either:
            # 1. instrument field (which was originally the subject but is now in instrument field)
            # 2. subject field (if the reversal was incorrect)
            
            # Try to find the item with interactions in the room based on instrument field
            for item in current_room.get_items(game_state):
                if instrument and instrument.lower() in item.name.lower() and hasattr(item, 'interactions'):
                    primary_item = item
                    secondary_item_name = subject  # The subject is actually the instrument in reversed syntax
                    if hasattr(primary_item, 'set_room_id'):
                        primary_item.set_room_id(current_room.room_id)
                    break
            
            # If not found, check if subject is actually the item with interactions
            if not primary_item:
                for item in current_room.get_items(game_state):
                    if subject.lower() in item.name.lower() and hasattr(item, 'interactions'):
                        primary_item = item
                        secondary_item_name = instrument  # Keep the original instrument
                        if hasattr(primary_item, 'set_room_id'):
                            primary_item.set_room_id(current_room.room_id)
                        break
                        
            # If still not found, check player's inventory
            if not primary_item:
                for item in player.inventory:
                    if instrument and instrument.lower() in item.name.lower() and hasattr(item, 'interactions'):
                        primary_item = item
                        secondary_item_name = subject
                        break
                    
            # One last attempt with subject field
            if not primary_item:
                for item in player.inventory:
                    if subject.lower() in item.name.lower() and hasattr(item, 'interactions'):
                        primary_item = item
                        secondary_item_name = instrument
                        break
        else:
            # Standard syntax, subject contains the target item, instrument contains the tool
            
            # First check player inventory for subject
            for item in player.inventory:
                if subject.lower() in item.name.lower() and hasattr(item, 'interactions'):
                    primary_item = item
                    secondary_item_name = instrument
                    break
            
            # If not in inventory, check the room items
            if not primary_item:
                for item in current_room.get_items(game_state):
                    if subject.lower() in item.name.lower() and hasattr(item, 'interactions'):
                        primary_item = item
                        secondary_item_name = instrument
                        if hasattr(primary_item, 'set_room_id'):
                            primary_item.set_room_id(current_room.room_id)
                        break
        
        # If we couldn't find primary item with interactions                    
        if not primary_item:
            return f"You can't {verb} that."
        
        # If we found a primary item, but it doesn't support this verb
        if verb not in primary_item.interactions:
            return f"You can't {verb} the {primary_item.name}."
            
        # Now get the secondary item (the instrument) if needed
        if secondary_item_name:
            for item in player.inventory:
                if secondary_item_name.lower() in item.name.lower():
                    secondary_item = item
                    break
        
        # Get all possible interactions for this verb
        possible_interactions = primary_item.interactions[verb]
        
        # Make sure we're dealing with a list
        if not isinstance(possible_interactions, list):
            possible_interactions = [possible_interactions]  # Backward compatibility
        
        # Find the appropriate interaction based on current state and conditions
        valid_interaction = None
        for interaction in possible_interactions:
            # Skip non-dictionary interactions
            if not isinstance(interaction, dict):
                continue
                
            # Check if this interaction is valid for the current state
            if 'from_state' in interaction:
                from_state = interaction['from_state']
                if from_state is not None and from_state != primary_item.state:
                    continue
            
            # We found a match for the current state (or one with no state requirement)
            valid_interaction = interaction
            break
        
        # If no valid interaction was found
        if not valid_interaction:
            return f"You can't {verb} the {primary_item.name} in its current state."
        
        # If an instrument is required, check if we have it
        if 'required_instrument' in valid_interaction and valid_interaction['required_instrument']:
            required_instrument = valid_interaction['required_instrument']
            
            if not secondary_item:
                return f"You need {required_instrument} to {verb} the {primary_item.name}."
            
            # Check if it's the right type of instrument
            if required_instrument.lower() not in secondary_item.name.lower():
                return f"You can't {verb} the {primary_item.name} with that."
        
        # Check any additional conditions
        if 'conditional_fn' in valid_interaction and valid_interaction['conditional_fn']:
            if not valid_interaction['conditional_fn'](player, game_state):
                return f"You can't {verb} the {primary_item.name} right now."
        
        # All conditions met, perform the interaction
        if 'target_state' in valid_interaction and valid_interaction['target_state']:
            target_state = valid_interaction['target_state']
            primary_item.set_state(target_state, game_state)
            
            # Broadcast state change to other players in the room
            if hasattr(primary_item, 'room_id') and primary_item.room_id:
                # Create a message that describes what happened
                change_message = f"{player.name} {verb}s the {primary_item.name}."
                
                # Use the notifications service to broadcast
                await broadcast_room(primary_item.room_id, change_message, exclude_player=[player.name])
        
        # Get the success message
        message = valid_interaction.get('message', f"You {verb} the {primary_item.name}.")
        
        # Handle exit modifications
        add_exit = valid_interaction.get('add_exit')
        remove_exit = valid_interaction.get('remove_exit')
        show_room_desc = valid_interaction.get('show_room_desc', False)
        
        if add_exit or remove_exit:
            if show_room_desc:
                return f"{message}\n\n{build_look_description(player, game_state, online_sessions)}"
            
            # Otherwise just mention the exit change
            exit_msg = ""
            if add_exit:
                direction, _ = add_exit
                exit_msg = f" You can now go {direction}."
            return f"{message}{exit_msg}"
        
        return message
        
    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"Exception in interaction handler: {e}")
        logger.error(error_trace)
        return f"Error processing command: {str(e)}"

# Register all the interaction verbs
common_interaction_verbs = [
    "open", "close", "push", "pull", "turn", "twist", "light", "extinguish", "touch",
    "cut", "break", "chop", "hit", "move", "unlock", "lock", "knock", "read", "tie", "use"
]

def register_interaction_verbs():
    for verb in common_interaction_verbs:
        command_registry.register(verb, handle_interaction, 
                                 f"{verb.capitalize()} something, optionally with an instrument.")

# Call this function to register all verbs
register_interaction_verbs()