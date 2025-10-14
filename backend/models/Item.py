# backend/models/item.py

from typing import Any, Dict


class Item:
    name: str
    id: str
    description: str
    weight: int
    value: int
    takeable: bool
    emits_light: bool

    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        weight: int = 1,
        value: int = 0,
        takeable: bool = True,
        emits_light: bool = False,
    ) -> None:
        """
        :param name: The name of the item.
        :param id: The id of the item.
        :param description: A short description of the item.
        :param weight: How much the item weighs (default: 1kg).
        :param value: The amount of points given if swamped (default: 0).
        :param takeable: Whether the item can be picked up (default: True).
        :param emits_light: Whether the item emits light (default: False).
        """
        self.name = name
        self.id = id
        self.description = description
        self.weight = weight
        self.value = value
        self.takeable = takeable
        self.emits_light = emits_light

    def __repr__(self) -> str:
        return f"{self.name} - {self.description} ({self.weight}kg, {self.value}pts)"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the item to a dictionary for serialization."""
        return {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "weight": self.weight,
            "value": self.value,
            "takeable": self.takeable,
            "emits_light": self.emits_light,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Item":
        """Create an item from a dictionary representation."""
        return Item(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            weight=data.get("weight", 1),
            value=data.get("value", 0),
            takeable=data.get("takeable", True),
            emits_light=data.get("emits_light", False),
        )
