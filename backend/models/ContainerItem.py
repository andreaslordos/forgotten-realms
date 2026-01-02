from typing import Any, Callable, Dict, List, Optional, Tuple
from models.StatefulItem import StatefulItem
from models.Item import Item


class ContainerItem(StatefulItem):
    base_description: str
    base_weight: int
    capacity_limit: int
    capacity_weight: int
    items: List[Item]
    no_removal: bool
    no_removal_message: Optional[str]
    no_removal_condition: Optional[Callable[[Any], Tuple[bool, Optional[str]]]]
    on_item_added: Optional[Callable[[Any, "ContainerItem", Item], Optional[str]]]

    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        weight: int = 1,
        value: int = 0,
        takeable: bool = True,
        state: Optional[str] = None,
        capacity_limit: int = 10,
        capacity_weight: int = 100,
        no_removal: bool = False,
        no_removal_message: Optional[str] = None,
    ) -> None:
        """
        :param capacity_limit: Maximum number of items the container can hold.
        :param capacity_weight: Maximum total weight (in kg) for the items in the container.
        """
        # Default to "open" if no state is provided.
        if state is None:
            state = "open"
        # Save the base description so we can build the dynamic full description.
        self.base_description = description  # e.g. "A musty old carpet bag is here"
        # Save the intrinsic weight of the container (without contents)
        self.base_weight = weight
        # Initialize the parent class with the current weight (will be updated later).
        super().__init__(name, id, description, weight, value, takeable, state)
        self.capacity_limit = capacity_limit
        self.capacity_weight = capacity_weight
        self.items = []  # List to hold contained items
        self.no_removal = no_removal
        self.no_removal_message = no_removal_message
        # Dynamic removal check: callable(game_state) -> (blocked, message)
        self.no_removal_condition = None
        # Callback when item added: callable(game_state, container, item) -> Optional[str]
        self.on_item_added = None
        self.update_weight()  # Set the initial total weight (base_weight + contained items)
        self.update_description()  # Set the initial description

        # Add default open/close interactions
        self.setup_default_interactions()

    def setup_default_interactions(self) -> None:
        """Set up the default open and close interactions for containers."""
        # Only add these if we have the add_interaction method (from StatefulItem)
        if hasattr(self, "add_interaction"):
            # Add open interaction for closed state
            self.add_interaction(
                verb="open",
                target_state="open",
                message=f"You open the {self.name}.",
                from_state="closed",
            )

            # Add close interaction for open state
            self.add_interaction(
                verb="close",
                target_state="closed",
                message=f"You close the {self.name}.",
                from_state="open",
            )

    def update_weight(self) -> None:
        """Update the container's total weight to be its own base weight plus the weight of its contents."""
        self.weight = self.base_weight + self.current_weight()

    def get_contained(self) -> str:
        """Used in inventory command."""
        return_str = f"    The {self.name} contains "
        if len(self.items) > 0:
            if self.state == "open":
                items_str = ", ".join(item.name for item in self.items)
            else:
                items_str = "something"
        else:
            items_str = "nothing"
        return return_str + items_str

    def update_description(self) -> None:
        """
        Update the container's full description to follow the required format:

        "<base description>, <state>.
            The bag contains <items list or 'nothing'>"

        When closed/locked, the contents are hidden.
        Uses custom state_descriptions if available.
        """
        # Use custom state description if available
        if (
            hasattr(self, "state_descriptions")
            and self.state
            and self.state in self.state_descriptions
        ):
            full_desc = f"{self.state_descriptions[self.state]}\n"
        elif self.state == "open":
            full_desc = f"{self.base_description}, open.\n"
        else:  # state is "closed" or other non-open state
            full_desc = f"{self.base_description}, closed.\n"
        full_desc += self.get_contained()
        self.description = full_desc

    def set_state(self, new_state: str, game_state: Any = None) -> bool:
        """
        Change the state of the container and update its description.

        :param new_state: The new state (e.g., "open", "closed", "locked").
        :param game_state: Optional game state for updating room exits.
        :return: True if state was changed, False otherwise.
        """
        # Allow standard container states plus any custom states in state_descriptions
        valid_states = {"open", "closed"}
        if hasattr(self, "state_descriptions"):
            valid_states.update(self.state_descriptions.keys())
        if new_state not in valid_states:
            return False

        self.state = new_state
        self.update_description()

        # Handle any exits or other state change effects from parent class
        if game_state and hasattr(self, "room_id") and self.room_id:
            room = game_state.get_room(self.room_id)
            if room:
                # Check if this state change should add/remove exits
                if hasattr(self, "interactions"):
                    for verb, interactions in self.interactions.items():
                        if not isinstance(interactions, list):
                            interactions = [interactions]

                        for interaction in interactions:
                            if interaction.get("target_state") == new_state:
                                if interaction.get("add_exit"):
                                    direction, target_room = interaction["add_exit"]
                                    room.exits[direction] = target_room
                                if (
                                    interaction.get("remove_exit")
                                    and interaction["remove_exit"] in room.exits
                                ):
                                    del room.exits[interaction["remove_exit"]]

        return True

    def add_item(self, item: Item) -> bool:
        """
        Attempt to add an item to the container, respecting capacity and weight limits.
        Updates the description and total weight afterward.

        :param item: An instance of Item (or subclass) to add.
        :return: True if the item was added, False otherwise.
        """
        # Check if the item is a container - prevent nesting containers
        if isinstance(item, ContainerItem):
            return False  # Cannot put containers inside other containers

        if len(self.items) >= self.capacity_limit:
            return False  # Exceeds maximum item count
        if self.current_weight() + item.weight > self.capacity_weight:
            return False  # Exceeds weight limit

        self.items.append(item)
        self.update_weight()
        self.update_description()
        return True

    def remove_item(self, item_id: str) -> Optional[Item]:
        """
        Remove an item from the container by its id and update the description and total weight.

        :param item_id: The id of the item to remove.
        :return: The removed item if found, else None.
        """
        for index, contained_item in enumerate(self.items):
            if contained_item.id == item_id:
                removed = self.items.pop(index)
                self.update_weight()
                self.update_description()
                return removed
        return None

    def current_weight(self) -> int:
        """Calculate the total weight of the contained items."""
        return sum(item.weight for item in self.items)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the container item to a dictionary including its capacity details and contained items.
        Also save the container's intrinsic weight.
        """
        data: Dict[str, Any] = super().to_dict()
        data["capacity_limit"] = self.capacity_limit
        data["capacity_weight"] = self.capacity_weight
        data["items"] = [item.to_dict() for item in self.items]
        data["base_weight"] = self.base_weight
        data["no_removal"] = self.no_removal
        if self.no_removal_message:
            data["no_removal_message"] = self.no_removal_message
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ContainerItem":
        """
        Reconstruct a ContainerItem from a dictionary representation.
        """
        container = ContainerItem(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            weight=data.get("base_weight", 1),
            value=data.get("value", 0),
            takeable=data.get("takeable", True),
            state=data.get("state", "closed"),
            capacity_limit=data.get("capacity_limit", 10),
            capacity_weight=data.get("capacity_weight", 100),
            no_removal=data.get("no_removal", False),
            no_removal_message=data.get("no_removal_message"),
        )
        if "items" in data:
            for item_data in data["items"]:
                if "state" in item_data:
                    from models.StatefulItem import StatefulItem

                    container.items.append(StatefulItem.from_dict(item_data))
                else:
                    container.items.append(Item.from_dict(item_data))
        container.update_weight()
        container.update_description()
        return container

    def __repr__(self) -> str:
        # Simply return the current description.
        return self.description
