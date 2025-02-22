class Item:
    def __init__(self, name, description, weight=1, value=0):
        """
        :param name: The name of the item.
        :param description: A short description of the item.
        :param weight: How much the item weighs (default: 1kg).
        :param value: The amount of points given if swamped (default: 0).
        """
        self.name = name
        self.description = description
        self.weight = weight
        self.value = value

    def __repr__(self):
        return f"{self.name} - {self.description} ({self.weight}kg, {self.value}pts)"

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "weight": self.weight,
            "value": self.value
        }

    @staticmethod
    def from_dict(data):
        return Item(
            data["name"],
            data["description"],
            data.get("weight", 1),
            data.get("value", 0)
        )
