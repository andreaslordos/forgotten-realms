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
    Handle specific verb-object interactions like 'open door with key', 'light torch with match'.
    """
    try:
        verb = cmd["verb"]
        subject = cmd.get("subject")
        instrument = cmd.get("instrument")
        
        if not subject:
            return f"What do you want to {verb}?"
        
        # Look for the target item in the room or inventory
        target_item = None
        instrument_item = None
        
        # Check player's inventory for subject
        for item in player.inventory:
            if subject.lower() in item.name.lower():
                target_item = item
                break
        
        # If not in inventory, check the room
        current_room = None
        if not target_item:
            current_room = game_state.get_room(player.current_room)
            
            # Check all visible items in the room
            visible_items = current_room.get_items(game_state)
            for item in visible_items:
                if subject.lower() in item.name.lower():
                    target_item = item
                    # Set the room_id for the item if it has the attribute
                    if hasattr(item, 'set_room_id'):
                        item.set_room_id(current_room.room_id)
                    break
        
        if not target_item:
            return f"You don't see '{subject}' here."
        
        # If it's not a StatefulItem or doesn't have interactions attribute
        if not hasattr(target_item, 'interactions'):
            return f"You can't {verb} that."
        
        # Check if the verb is supported for this item
        if verb not in target_item.interactions:
            return f"You can't {verb} the {target_item.name}."
        
        # Get all possible interactions for this verb
        possible_interactions = target_item.interactions[verb]
        
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
                if from_state is not None and from_state != target_item.state:
                    continue
            
            # We found a match for the current state (or one with no state requirement)
            valid_interaction = interaction
            break
        
        # If no valid interaction was found
        if not valid_interaction:
            return f"You can't {verb} the {target_item.name} in its current state."
        
        # If an instrument is required, find it
        if 'required_instrument' in valid_interaction and valid_interaction['required_instrument']:
            required_instrument = valid_interaction['required_instrument']
            
            if not instrument:
                return f"You need something to {verb} the {target_item.name} with."
            
            # Look for the instrument in inventory
            for item in player.inventory:
                if instrument.lower() in item.name.lower():
                    instrument_item = item
                    break
            
            if not instrument_item:
                return f"You don't have '{instrument}'."
            
            # Check if it's the right type of instrument
            if required_instrument.lower() not in instrument_item.name.lower():
                return f"You can't {verb} the {target_item.name} with that."
        
        # Check any additional conditions
        if 'conditional_fn' in valid_interaction and valid_interaction['conditional_fn']:
            if not valid_interaction['conditional_fn'](player, game_state):
                return f"You can't {verb} the {target_item.name} right now."
        
        # All conditions met, perform the interaction
        if 'target_state' in valid_interaction and valid_interaction['target_state']:
            target_state = valid_interaction['target_state']
            target_item.set_state(target_state, game_state)
            
            # Broadcast state change to other players in the room
            if hasattr(target_item, 'room_id') and target_item.room_id:
                # Create a message that describes what happened
                change_message = f"{player.name} {verb}s the {target_item.name}."
                
                # Use the notifications service to broadcast
                await broadcast_room(target_item.room_id, change_message, exclude_player=[player.name])
        
        # Get the success message
        message = valid_interaction.get('message', f"You {verb} the {target_item.name}.")
        
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