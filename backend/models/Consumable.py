# backend/models/Consumable.py

from typing import Any, Dict, List, Optional

from models.Item import Item

EFFECT_HEAL = "heal"
EFFECT_CURE_ALL = "cure_all"


class Consumable(Item):
    """
    A drinkable/usable item with a one-shot effect.

    Effects:
        heal      — restore `magnitude` stamina (capped at max_stamina)
        cure_all  — remove all afflictions
    """

    effect: str
    magnitude: int

    def __init__(
        self,
        name: str,
        id: str,
        description: str,
        effect: str = EFFECT_HEAL,
        magnitude: int = 0,
        weight: int = 1,
        value: int = 0,
        takeable: bool = True,
        synonyms: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            name=name,
            id=id,
            description=description,
            weight=weight,
            value=value,
            takeable=takeable,
            synonyms=synonyms,
        )
        self.effect = effect
        self.magnitude = magnitude

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["item_type"] = "consumable"
        data["effect"] = self.effect
        data["magnitude"] = self.magnitude
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Consumable":
        return Consumable(
            name=data["name"],
            id=data["id"],
            description=data["description"],
            effect=data.get("effect", EFFECT_HEAL),
            magnitude=data.get("magnitude", 0),
            weight=data.get("weight", 1),
            value=data.get("value", 0),
            takeable=data.get("takeable", True),
            synonyms=data.get("synonyms"),
        )
