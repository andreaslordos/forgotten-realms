# backend/models/StatefulItem.py

from models.Item import Item

class StatefulItem(Item):
    def __init__(self, name, id, description, weight=1, value=0, takeable=True, state=None):
        super().__init__(name, id, description, weight, value, takeable)
        self.state = state
        self.state_descriptions = {}
        if state:
            # When a state is provided, use the given description for that state.
            self.state_descriptions[state] = description

    def add_state_description(self, state, description):
        """Add a description for a specific state."""
        self.state_descriptions[state] = description

    def get_state(self):
        """Get the current state of the item."""
        return self.state

    def set_state(self, new_state):
        """
        Change the state of the item and update its description
        if a description exists for the new state.
        
        :param new_state: The new state to set.
        :return: True if state was changed, False if the state is invalid.
        """
        if new_state in self.state_descriptions:
            self.state = new_state
            self.description = self.state_descriptions[new_state]
            return True
        return False

    def to_dict(self):
        """Convert the stateful item to a dictionary including its state data."""
        data = super().to_dict()
        if self.state is not None:
            data["state"] = self.state
            data["state_descriptions"] = self.state_descriptions
        return data

    @staticmethod
    def from_dict(data):
        """Create a stateful item from a dictionary representation."""
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
        return item
