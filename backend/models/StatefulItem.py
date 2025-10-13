# Enhancement to models/StatefulItem.py to support linked items

from typing import Any, Callable, Dict, List, Optional, Tuple
from models.Item import Item
import logging

if False:  # TYPE_CHECKING
    pass

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class StatefulItem(Item):
    state: Optional[str]
    state_descriptions: Dict[str, str]
    interactions: Dict[str, List[Dict[str, Any]]]
    room_id: Optional[str]
    linked_items: List[str]

    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        weight: int = 1,
        value: int = 0,
        takeable: bool = True,
        state: Optional[str] = None,
    ) -> None:
        super().__init__(name, id, description, weight, value, takeable)
        self.state = state
        self.state_descriptions = {}
        self.interactions = {}  # Maps verbs to required instruments and effects
        self.room_id = None  # Track which room this item is in
        self.linked_items = []  # IDs of linked items (like other side of a door)

        if state:
            # When a state is provided, use the given description for that state.
            self.state_descriptions[state] = description

    def add_state_description(self, state: str, description: str) -> None:
        """Add a description for a specific state."""
        self.state_descriptions[state] = description

    def get_state(self) -> Optional[str]:
        """Get the current state of the item."""
        return self.state

    def set_room_id(self, room_id: str) -> None:
        """Set the room ID where this item is located."""
        self.room_id = room_id

    def link_item(self, item_id: str) -> None:
        """
        Link this item to another item (e.g., door with another door).
        Linked items change state together.

        Args:
            item_id (str): ID of the item to link with
        """
        if item_id not in self.linked_items:
            self.linked_items.append(item_id)
            logger.debug(f"Linked {self.id} with {item_id}")

    def add_interaction(
        self,
        verb: str,
        required_instrument: Optional[str] = None,
        target_state: Optional[str] = None,
        message: Optional[str] = None,
        add_exit: Optional[Tuple[str, str]] = None,
        remove_exit: Optional[str] = None,
        conditional_fn: Optional[Callable[..., bool]] = None,
        from_state: Optional[str] = None,
        consume_instrument: bool = False,
        drop_instrument: bool = False,
        reciprocal_exit: Optional[Tuple[str, str, str]] = None,
        remove_item: bool = False,
    ) -> None:
        """
        Register an interaction for this item.

        Args:
            verb (str): The verb that triggers this interaction (e.g., 'open', 'light')
            required_instrument (str, optional): Item required to perform the action
            target_state (str, optional): State to change to if action succeeds
            message (str, optional): Message to display on success
            add_exit (tuple, optional): (direction, room_id) to add to room exits
            remove_exit (str, optional): Direction to remove from room exits
            conditional_fn (callable, optional): Additional condition function
            from_state (str, optional): Only allow this interaction when item is in this state
            consume_instrument (bool, optional): Whether to consume (delete) the instrument after use
            drop_instrument (bool, optional): Whether to force dropping the instrument after use
            reciprocal_exit (tuple, optional): (room_id, direction, target_room_id) for return path
        """
        verb = verb.lower()

        # Create a list for this verb if it doesn't exist
        if verb not in self.interactions:
            self.interactions[verb] = []

        # Create the new interaction dictionary explicitly
        interaction: Dict[str, Any] = {}
        if required_instrument is not None:
            interaction["required_instrument"] = required_instrument
        if target_state is not None:
            interaction["target_state"] = target_state
        if message is not None:
            interaction["message"] = message
        if add_exit is not None:
            interaction["add_exit"] = add_exit
        if remove_exit is not None:
            interaction["remove_exit"] = remove_exit
        if conditional_fn is not None:
            interaction["conditional_fn"] = conditional_fn
        if from_state is not None:
            interaction["from_state"] = from_state
        if consume_instrument:
            interaction["consume_instrument"] = True
        if drop_instrument:
            interaction["drop_instrument"] = True
        if reciprocal_exit is not None:
            interaction["reciprocal_exit"] = reciprocal_exit
        if remove_item:
            interaction["remove_item"] = True

        # Add the interaction to the list
        self.interactions[verb].append(interaction)

    def set_state(self, new_state: str, game_state: Optional[Any] = None) -> bool:
        """
        Change the state of the item and update room exits if needed.
        Also update any linked items to maintain consistency.

        Args:
            new_state (str): The new state to set
            game_state (GameState, optional): Game state for updating room exits

        Returns:
            bool: True if state was changed, False if invalid
        """
        if new_state not in self.state_descriptions:
            return False

        # Change this item's state
        old_state = self.state if self.state is not None else ""
        self.state = new_state
        self.description = self.state_descriptions[new_state]

        # If we have game_state, update room exits and linked items
        if game_state:
            # Process exit changes for this item
            self._process_exit_changes(game_state, old_state, new_state)

            # Update any linked items (e.g., the other side of a door)
            self._update_linked_items(game_state, new_state)

        return True

    def _process_exit_changes(
        self, game_state: Any, old_state: str, new_state: str
    ) -> None:
        """Process exit changes based on state change."""
        if self.room_id:
            room = game_state.get_room(self.room_id)
            if room:
                # Check if this state change should add/remove exits
                if hasattr(self, "interactions"):
                    for verb in self.interactions:
                        interactions_list = self.interactions[verb]

                        if not isinstance(interactions_list, list):
                            interactions_list = [interactions_list]

                        for interaction in interactions_list:
                            if not isinstance(interaction, dict):
                                continue

                            if (
                                "target_state" in interaction
                                and interaction["target_state"] == new_state
                            ):
                                if "add_exit" in interaction:
                                    direction, target_room = interaction["add_exit"]
                                    room.exits[direction] = target_room

                                if (
                                    "remove_exit" in interaction
                                    and interaction["remove_exit"] in room.exits
                                ):
                                    del room.exits[interaction["remove_exit"]]

                                if interaction.get("remove_item", False):
                                    room.remove_item(self)

    def _update_linked_items(self, game_state: Any, new_state: str) -> None:
        """Update all linked items to maintain consistency."""
        for item_id in self.linked_items:
            # Find the linked item in all rooms
            for room_id, room in game_state.rooms.items():
                for item in room.items:
                    if hasattr(item, "id") and item.id == item_id:
                        # Found the linked item - update its state without triggering another link update
                        if hasattr(item, "state") and item.state != new_state:
                            # Set state directly without calling set_state to avoid infinite recursion
                            item.state = new_state
                            if new_state in item.state_descriptions:
                                item.description = item.state_descriptions[new_state]
                            # Process exit changes for the linked item
                            if hasattr(item, "_process_exit_changes"):
                                item._process_exit_changes(
                                    game_state, item.state, new_state
                                )
                        break

    def to_dict(self) -> Dict[str, Any]:
        """Convert the stateful item to a dictionary including its state data."""
        data = super().to_dict()
        if self.state is not None:
            data["state"] = self.state
            data["state_descriptions"] = self.state_descriptions
            data["interactions"] = self.interactions
            data["room_id"] = self.room_id
            data["linked_items"] = self.linked_items
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StatefulItem":
        """Create a stateful item from a dictionary representation."""
        item = StatefulItem(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            weight=data.get("weight", 1),
            value=data.get("value", 0),
            takeable=data.get("takeable", True),
            state=data.get("state", None),
        )
        if "state_descriptions" in data:
            item.state_descriptions = data["state_descriptions"]
        if "interactions" in data:
            item.interactions = data["interactions"]
        if "room_id" in data:
            item.room_id = data["room_id"]
        if "linked_items" in data:
            item.linked_items = data["linked_items"]
        return item
