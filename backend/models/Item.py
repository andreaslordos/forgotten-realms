# backend/models/item.py

class Item:
    def __init__(self, name, id, description, weight=1, value=0, takeable=True):
        """
        :param name: The name of the item.
        :param id: The id of the item.
        :param description: A short description of the item.
        :param weight: How much the item weighs (default: 1kg).
        :param value: The amount of points given if swamped (default: 0).
        :param takeable: Whether the item can be picked up (default: True).
        """
        self.name = name
        self.id = id
        self.description = description
        self.weight = weight
        self.value = value
        self.takeable = takeable

    def __repr__(self):
        return f"{self.name} - {self.description} ({self.weight}kg, {self.value}pts)"

    def to_dict(self):
        """Convert the item to a dictionary for serialization."""
        return {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "weight": self.weight,
            "value": self.value,
            "takeable": self.takeable
        }

    @staticmethod
    def from_dict(data):
        """Create an item from a dictionary representation."""
        return Item(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            weight=data.get("weight", 1),
            value=data.get("value", 0),
            takeable=data.get("takeable", True)
        )