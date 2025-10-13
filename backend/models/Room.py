# Update models/Room.py to add hidden items support

from typing import Any, Callable, Dict, List, Optional, Tuple

if False:  # TYPE_CHECKING
    pass


class Room:
    room_id: str
    name: str
    description: str
    items: List[Any]  # List["Item"]
    hidden_items: Dict[
        str, Tuple[Any, Callable[[Any], bool]]
    ]  # Dict[str, Tuple["Item", Callable[["GameState"], bool]]]
    exits: Dict[str, str]

    def __init__(
        self,
        room_id: str,
        name: str,
        description: str,
        exits: Optional[Dict[str, str]] = None,
    ) -> None:
        self.room_id = room_id
        self.name = name
        self.description = description
        self.items = []  # Holds all visible items in the room
        self.hidden_items = {}  # Maps item_id to (item, condition_func) pairs
        self.exits = exits if exits is not None else {}

    def add_item(self, item: Any) -> None:  # item: "Item"
        """Add a visible item to the room."""
        self.items.append(item)

    def add_hidden_item(
        self, item: Any, condition_func: Callable[[Any], bool]
    ) -> None:  # item: "Item", condition_func: Callable[["GameState"], bool]
        """
        Add a hidden item that only appears when a condition is met.

        Args:
            item: The item to add
            condition_func: A function that takes (game_state) and returns True when item should be visible
        """
        self.hidden_items[item.id] = (item, condition_func)

    def remove_item(self, item: Any) -> bool:  # item: "Item"
        """Remove an item from the room."""
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def remove_hidden_item(self, item_id: str) -> bool:
        """Remove a hidden item from the room."""
        if item_id in self.hidden_items:
            del self.hidden_items[item_id]
            return True
        return False

    def get_items(
        self, game_state: Optional[Any] = None
    ) -> List[Any]:  # game_state: Optional["GameState"], returns List["Item"]
        """
        Get all visible items in the room, including hidden items
        whose conditions are satisfied.
        """
        visible_items: List[Any] = list(self.items)

        if game_state:
            for item_id, (item, condition) in self.hidden_items.items():
                if condition(game_state):
                    visible_items.append(item)

        return visible_items

    def to_dict(self) -> Dict[str, Any]:
        """Convert the room to a dictionary for serialization."""
        return {
            "room_id": self.room_id,
            "name": self.name,
            "description": self.description,
            "items": [item.to_dict() for item in self.items],
            "hidden_items": {
                id: item.to_dict() for id, (item, _) in self.hidden_items.items()
            },
            "exits": self.exits,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Room":
        """Create a room from a dictionary representation."""
        room = Room(
            data["room_id"],
            data["name"],
            data["description"],
            exits=data.get("exits", {}),
        )
        # room.items = [Item.from_dict(item_data) for item_data in data.get("items", [])]
        # Note: condition functions can't be easily serialized, so they'd need to be re-attached
        # after loading by custom code in the game initialization
        return room

    def __repr__(self) -> str:
        return f"Room({self.room_id}, exits: {self.exits}, items: {self.items})"
