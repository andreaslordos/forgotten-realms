# backend/models/item.py

class Item:
    def __init__(self, name, id, description, weight=1, value=0, takeable=True, state=None):
        """
        :param name: The name of the item.
        :param id: The id of the item.
        :param description: A short description of the item.
        :param weight: How much the item weighs (default: 1kg).
        :param value: The amount of points given if swamped (default: 0).
        :param takeable: Whether the item can be picked up (default: True).
        :param state: Initial state for stateful objects (default: None).
        """
        self.name = name
        self.id = id
        self.description = description
        self.weight = weight
        self.value = value
        self.takeable = takeable
        self.state = state
        self.state_descriptions = {}
        if state:
            self.state_descriptions[state] = description

    def __repr__(self):
        return f"{self.name} - {self.description} ({self.weight}kg, {self.value}pts)"

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
        
        :param new_state: The new state to set
        :return: True if state was changed, False if invalid state
        """
        if new_state in self.state_descriptions:
            self.state = new_state
            self.description = self.state_descriptions[new_state]
            return True
        return False

    def to_dict(self):
        """Convert the item to a dictionary for serialization."""
        data = {
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "value": self.value,
            "takeable": self.takeable
        }
        
        if self.state:
            data["state"] = self.state
            data["state_descriptions"] = self.state_descriptions
            
        return data

    @staticmethod
    def from_dict(data):
        """Create an item from a dictionary representation."""
        item = Item(
            data["name"],
            data["description"],
            data.get("weight", 1),
            data.get("value", 0),
            data.get("takeable", True),
            data.get("state", None)
        )
        
        # Load state descriptions if present
        if "state_descriptions" in data:
            item.state_descriptions = data["state_descriptions"]
            
        return item