# backend/models/item.py

from typing import Any, Dict, Optional


class Item:
    name: str
    id: str
    description: str
    weight: int
    value: int
    takeable: bool
    emits_light: bool
    grants_invisibility: bool
    invisibility_duration_seconds: float
    invisibility_activated_at: Optional[float]
    invisibility_expired: bool

    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        weight: int = 1,
        value: int = 0,
        takeable: bool = True,
        emits_light: bool = False,
        grants_invisibility: bool = False,
        invisibility_duration_seconds: float = 0.0,
    ) -> None:
        """
        :param name: The name of the item.
        :param id: The id of the item.
        :param description: A short description of the item.
        :param weight: How much the item weighs (default: 1kg).
        :param value: The amount of points given if swamped (default: 0).
        :param takeable: Whether the item can be picked up (default: True).
        :param emits_light: Whether the item emits light (default: False).
        :param grants_invisibility: Whether item grants invisibility (default: False).
        :param invisibility_duration_seconds: How long invisibility lasts (default: 0).
        """
        self.name = name
        self.id = id
        self.description = description
        self.weight = weight
        self.value = value
        self.takeable = takeable
        self.emits_light = emits_light
        self.grants_invisibility = grants_invisibility
        self.invisibility_duration_seconds = invisibility_duration_seconds
        self.invisibility_activated_at: Optional[float] = None
        self.invisibility_expired: bool = False

    def __repr__(self) -> str:
        return f"{self.name} - {self.description} ({self.weight}kg, {self.value}pts)"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the item to a dictionary for serialization."""
        data: Dict[str, Any] = {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "weight": self.weight,
            "value": self.value,
            "takeable": self.takeable,
            "emits_light": self.emits_light,
        }
        # Only include invisibility fields if item grants invisibility
        if self.grants_invisibility:
            data["grants_invisibility"] = self.grants_invisibility
            data["invisibility_duration_seconds"] = self.invisibility_duration_seconds
            data["invisibility_activated_at"] = self.invisibility_activated_at
            data["invisibility_expired"] = self.invisibility_expired
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Item":
        """Create an item from a dictionary representation."""
        item = Item(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            weight=data.get("weight", 1),
            value=data.get("value", 0),
            takeable=data.get("takeable", True),
            emits_light=data.get("emits_light", False),
            grants_invisibility=data.get("grants_invisibility", False),
            invisibility_duration_seconds=data.get(
                "invisibility_duration_seconds", 0.0
            ),
        )
        # Restore invisibility state if present
        item.invisibility_activated_at = data.get("invisibility_activated_at")
        item.invisibility_expired = data.get("invisibility_expired", False)
        return item
