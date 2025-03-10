# models/StatefulItem.py with debugging enhancements

from models.Item import Item
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class StatefulItem(Item):
    def __init__(self, name, id, description, weight=1, value=0, takeable=True, state=None):
        super().__init__(name, id, description, weight, value, takeable)
        self.state = state
        self.state_descriptions = {}
        self.interactions = {}  # Maps verbs to required instruments and effects
        self.room_id = None  # Track which room this item is in
        
        logger.debug(f"StatefulItem created: {name} (ID: {id})")
        logger.debug(f"Initial state: {state}")
        
        if state:
            # When a state is provided, use the given description for that state.
            self.state_descriptions[state] = description
            logger.debug(f"Added initial state description for {state}")

    def add_state_description(self, state, description):
        """Add a description for a specific state."""
        self.state_descriptions[state] = description
        logger.debug(f"Added state description for {state}: {description[:30]}...")

    def get_state(self):
        """Get the current state of the item."""
        return self.state

    def set_room_id(self, room_id):
        """Set the room ID where this item is located."""
        logger.debug(f"Setting room_id for {self.name} to {room_id}")
        self.room_id = room_id

    def add_interaction(self, verb, required_instrument=None, target_state=None, 
                       message=None, add_exit=None, remove_exit=None, 
                       conditional_fn=None, from_state=None):
        """
        Register an interaction for this item with debug information.
        """
        verb = verb.lower()
        logger.debug(f"Adding interaction for {self.name}, verb: {verb}")
        logger.debug(f"  From state: {from_state}")
        logger.debug(f"  Target state: {target_state}")
        logger.debug(f"  Required instrument: {required_instrument}")
        
        # Create a list for this verb if it doesn't exist
        if verb not in self.interactions:
            logger.debug(f"  Creating new interaction list for verb: {verb}")
            self.interactions[verb] = []
            
        # Create the new interaction dictionary explicitly
        interaction = {}
        if required_instrument is not None:
            interaction['required_instrument'] = required_instrument
        if target_state is not None:
            interaction['target_state'] = target_state
        if message is not None:
            interaction['message'] = message
        if add_exit is not None:
            interaction['add_exit'] = add_exit
        if remove_exit is not None:
            interaction['remove_exit'] = remove_exit
        if conditional_fn is not None:
            interaction['conditional_fn'] = conditional_fn
        if from_state is not None:
            interaction['from_state'] = from_state
            
        logger.debug(f"  Interaction created: {interaction}")
        
        # Verify it's a proper dictionary
        logger.debug(f"  Type of interaction: {type(interaction)}")
        logger.debug(f"  Keys: {list(interaction.keys())}")
            
        # Add the interaction to the list
        self.interactions[verb].append(interaction)
        logger.debug(f"  Interaction added to list. Current interactions for {verb}: {self.interactions[verb]}")
        
        # Print out the entire interactions dictionary for this verb
        try:
            logger.debug(f"  Full interactions structure: {json.dumps(self.interactions[verb])}")
        except:
            logger.debug(f"  Could not serialize interactions (possibly due to conditional_fn)")

    def set_state(self, new_state, game_state=None):
        """
        Change the state of the item and update room exits if needed.
        
        Args:
            new_state (str): The new state to set
            game_state (GameState, optional): Game state for updating room exits
            
        Returns:
            bool: True if state was changed, False if invalid
        """
        logger.debug(f"Attempting to set state of {self.name} from {self.state} to {new_state}")
        
        if new_state not in self.state_descriptions:
            logger.debug(f"  Failed: {new_state} is not a valid state")
            return False
            
        old_state = self.state
        self.state = new_state
        self.description = self.state_descriptions[new_state]
        logger.debug(f"  State changed from {old_state} to {new_state}")
        logger.debug(f"  New description: {self.description[:30]}...")
        
        # If we have game_state and a room_id, update any room exits
        if game_state and self.room_id:
            logger.debug(f"  Updating room exits for room {self.room_id}")
            room = game_state.get_room(self.room_id)
            if room:
                logger.debug(f"  Room found: {room.name}")
                # Check if this state change should add/remove exits
                if hasattr(self, 'interactions'):
                    logger.debug(f"  Checking for exit changes in interactions")
                    for verb in self.interactions:
                        interactions_list = self.interactions[verb]
                        logger.debug(f"  Checking verb {verb}, interactions: {interactions_list}")
                        
                        if not isinstance(interactions_list, list):
                            logger.debug(f"  Converting to list for backwards compatibility")
                            interactions_list = [interactions_list]
                        
                        for interaction in interactions_list:
                            logger.debug(f"  Checking interaction: {interaction}")
                            
                            if not isinstance(interaction, dict):
                                logger.debug(f"  Skipping: not a dictionary")
                                continue
                                
                            if 'target_state' in interaction and interaction['target_state'] == new_state:
                                logger.debug(f"  Found interaction with matching target state: {new_state}")
                                
                                if 'add_exit' in interaction:
                                    logger.debug(f"  Adding exit: {interaction['add_exit']}")
                                    direction, target_room = interaction['add_exit']
                                    room.exits[direction] = target_room
                                    
                                if 'remove_exit' in interaction and interaction['remove_exit'] in room.exits:
                                    logger.debug(f"  Removing exit: {interaction['remove_exit']}")
                                    del room.exits[interaction['remove_exit']]
        else:
            logger.debug(f"  No game_state or room_id provided, skipping exit updates")
        
        return True

    def to_dict(self):
        """Convert the stateful item to a dictionary including its state data."""
        data = super().to_dict()
        if self.state is not None:
            data["state"] = self.state
            data["state_descriptions"] = self.state_descriptions
            data["interactions"] = self.interactions
            data["room_id"] = self.room_id
        return data

    @staticmethod
    def from_dict(data):
        """Create a stateful item from a dictionary representation."""
        logger.debug(f"Creating StatefulItem from dict: {data['name']}")
        
        item = StatefulItem(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            weight=data.get("weight", 1),
            value=data.get("value", 0),
            takeable=data.get("takeable", True),
            state=data.get("state", None)
        )
        if "state_descriptions" in data:
            item.state_descriptions = data["state_descriptions"]
            logger.debug(f"  Added state descriptions: {list(item.state_descriptions.keys())}")
            
        if "interactions" in data:
            # Convert interaction data back to proper format if needed
            interactions_data = data["interactions"]
            logger.debug(f"  Loading interactions from data: {interactions_data}")
            
            for verb, interactions in interactions_data.items():
                if not isinstance(interactions, list):
                    interactions = [interactions]
                
                for interaction in interactions:
                    # Make sure each interaction is a proper dictionary
                    if isinstance(interaction, dict):
                        if verb not in item.interactions:
                            item.interactions[verb] = []
                        item.interactions[verb].append(interaction)
                    else:
                        logger.error(f"  Invalid interaction format for {verb}: {interaction}")
            
            logger.debug(f"  Loaded interactions: {list(item.interactions.keys())}")
            
        if "room_id" in data:
            item.room_id = data["room_id"]
            logger.debug(f"  Set room_id: {item.room_id}")
            
        return item