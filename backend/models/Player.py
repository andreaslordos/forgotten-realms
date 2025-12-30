# backend/models/Player.py

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from models.Levels import levels
from models.Item import Item
from globals import SPAWN_ROOM


class Player:
    name: str
    email: Optional[str]
    sex: str
    points: int
    inventory: List[Item]
    stamina: int
    max_stamina: int
    strength: int
    dexterity: int
    magic: int
    carrying_capacity_num: int
    level: str
    visited: Set[str]
    current_level_at: int
    next_level_at: int
    created_at: datetime
    current_room: str
    last_active: datetime

    def __init__(
        self,
        name: str,
        sex: str = "M",
        email: Optional[str] = None,
        spawn_room: str = SPAWN_ROOM,
    ) -> None:
        self.name = name
        self.email = email
        self.sex = sex
        self.points = 0
        self.inventory = []  # List of Item objects
        self.stamina = levels[0]["stamina"]
        self.max_stamina = levels[0]["stamina"]
        self.strength = levels[0]["strength"]  # Strength determines max weight (in kg)
        self.dexterity = levels[0]["dexterity"]
        self.magic = levels[0]["magic"]
        self.carrying_capacity_num = levels[0][
            "carrying_capacity_num"
        ]  # Max number of items
        self.level = levels[0]["name"]
        self.visited = set()
        self.current_level_at = 0
        self.next_level_at = 400
        self.created_at = datetime.now()
        self.current_room = spawn_room  # Always start at spawn room on login/restart
        self.last_active = datetime.now()

    def level_up(
        self,
        sio: Optional[Any] = None,
        online_sessions: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Calculate the appropriate level based on current points.
        This version supports jumping multiple levels up or down.

        Args:
            sio (SocketIO, optional): Socket.IO instance for sending messages
            online_sessions (dict, optional): Dictionary of online sessions

        Returns:
            bool: Whether the level changed
        """
        # Get a sorted list of all level thresholds
        level_thresholds = sorted(levels.keys())

        # Find the highest threshold that the player's points exceed
        current_threshold = 0
        for threshold in level_thresholds:
            if self.points >= threshold:
                current_threshold = threshold
            else:
                break

        # Store the old level name for comparison
        old_level = self.level

        # Update player stats based on the determined level
        new_level = levels[current_threshold]
        self.level = new_level["name"]
        self.stamina = new_level["stamina"]
        self.max_stamina = new_level["stamina"]
        self.strength = new_level["strength"]
        self.dexterity = new_level["dexterity"]
        self.magic = new_level["magic"]
        self.carrying_capacity_num = new_level["carrying_capacity_num"]

        # Set current and next level thresholds
        self.current_level_at = current_threshold

        # Find the next level threshold
        next_index = level_thresholds.index(current_threshold) + 1
        if next_index < len(level_thresholds):
            self.next_level_at = level_thresholds[next_index]
        else:
            self.next_level_at = -1  # No next level (at max level)

        # Check if level changed
        leveled_up = old_level != self.level

        # Send level up notification if level changed
        if leveled_up and sio and online_sessions:
            # Find the player's session ID
            for sid, session in online_sessions.items():
                if session.get("player") == self:
                    # Send the level up notification to the player
                    notification = f"Your level of experience is now {self.level}."
                    asyncio.create_task(sio.emit("message", notification, room=sid))
                    break

        # Return whether the level changed
        return leveled_up

    def add_visited(self, room_id: str) -> None:
        self.visited.add(room_id)

    def add_points(
        self,
        points: int,
        sio: Optional[Any] = None,
        online_sessions: Optional[Dict[str, Any]] = None,
        send_notification: bool = True,
    ) -> Tuple[bool, str]:
        """
        Add points to the player's score and update level if needed.

        Args:
            points (int): The number of points to add
            sio (SocketIO, optional): Socket.IO instance for sending messages
            online_sessions (dict, optional): Dictionary of online sessions
            send_notification (bool): Whether to send the notification or return it

        Returns:
            tuple: (leveled_up, notification_text) - Whether the player leveled up and the notification text
        """
        self.points += points

        # Create the points notification
        notification = f"[{self.points}]"

        # Send points notification if requested
        if send_notification and sio and online_sessions:
            # Find the player's session ID
            for sid, session in online_sessions.items():
                if session.get("player") == self:
                    # Send just the points notification to the player
                    asyncio.create_task(sio.emit("message", notification, room=sid))
                    break

        # Call level_up to recalculate level based on new point total
        # Pass sio and online_sessions so level_up can send its own notification
        leveled_up = False
        if self.points >= self.next_level_at and self.next_level_at != -1:
            leveled_up = self.level_up(sio, online_sessions)

        return leveled_up, notification

    def total_inventory_weight(self) -> int:
        return sum(item.weight for item in self.inventory)

    def add_item(self, item: Item) -> Tuple[bool, str]:
        if not item.takeable:
            return False, "Don't be ridiculous!"
        # Check number capacity
        if len(self.inventory) >= self.carrying_capacity_num:
            return False, "You are carrying too many items."
        # Check weight capacity: weight capacity is equal to player's strength
        if self.total_inventory_weight() + item.weight > self.strength:
            return False, "This item is too heavy to carry."
        self.inventory.append(item)
        return True, f"{item.name} taken."

    def remove_item(self, item: Item) -> Tuple[bool, str]:
        if item in self.inventory:
            self.inventory.remove(item)
            return True, f"{item.name} dropped."
        return False, "Item not found in your inventory."

    def drop_all_items(self) -> List[Item]:
        dropped_items = self.inventory.copy()
        self.inventory.clear()
        return dropped_items

    def set_current_room(self, room_id: str) -> None:
        self.current_room = room_id

    def update_activity(self) -> None:
        self.last_active = datetime.now()

    def has_light_source(self) -> bool:
        """
        Check if player has a light-emitting item in inventory.

        Returns:
            bool: True if player has at least one light source
        """
        return any(
            hasattr(item, "emits_light") and item.emits_light for item in self.inventory
        )

    def get_effective_dexterity(
        self, room: Any, online_sessions: Dict[str, Any], game_state: Any
    ) -> int:
        """
        Get player's effective dexterity, accounting for darkness penalty.

        Args:
            room: The room the player is in
            online_sessions: Dictionary of online sessions
            game_state: The game state

        Returns:
            int: Effective dexterity (50% if in darkness without light)
        """
        # Import here to avoid circular dependency
        from commands.darkness_utils import room_is_visible

        if room_is_visible(room, online_sessions, game_state):
            return self.dexterity

        # In darkness without light - 50% penalty
        return self.dexterity // 2

    def return_summary(self) -> Dict[str, Any]:
        inv_items = (
            ", ".join(item.name for item in self.inventory)
            if self.inventory
            else "None"
        )
        return {
            "name": self.name,
            "level": self.level,
            "points": self.points,
            "stamina": self.stamina,
            "inventory": inv_items,
            "current_room": self.current_room,
            "last_active": self.last_active.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "email": self.email,
            "sex": self.sex,
            "points": self.points,
            "inventory": [item.to_dict() for item in self.inventory],
            "level": self.level,
            "current_room": self.current_room,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Player":
        player = Player(
            data["name"],
            data.get("sex", "M"),
            data.get("email"),
            spawn_room=data.get("current_room", SPAWN_ROOM),
        )
        player.points = data["points"]
        inventory_data = data.get("inventory", [])
        player.inventory = [Item.from_dict(item_data) for item_data in inventory_data]
        player.level = data["level"]
        player.current_room = data["current_room"]

        # Update the player's stats based on their level
        # First calculate what level threshold they should be at
        level_thresholds = sorted(levels.keys())
        current_threshold = 0
        for threshold in level_thresholds:
            if player.points >= threshold:
                current_threshold = threshold
            else:
                break

        # Update level-based stats
        level_data = levels[current_threshold]
        player.max_stamina = level_data["stamina"]
        # If stamina was saved in the data, use that value (capped at max_stamina)
        # Otherwise use max_stamina as default when first creating the character
        if "stamina" in data:
            player.stamina = min(data["stamina"], player.max_stamina)
        else:
            player.stamina = player.max_stamina

        player.strength = level_data["strength"]
        player.dexterity = level_data["dexterity"]
        player.magic = level_data["magic"]
        player.carrying_capacity_num = level_data["carrying_capacity_num"]

        # Set current and next level thresholds
        player.current_level_at = current_threshold

        # Find the next level threshold
        next_index = level_thresholds.index(current_threshold) + 1
        if next_index < len(level_thresholds):
            player.next_level_at = level_thresholds[next_index]
        else:
            player.next_level_at = -1  # No next level (at max level)

        return player
