# backend/models/Player.py

import asyncio
from datetime import datetime
from models.Levels import levels
from models.Item import Item

class Player:
    def __init__(self, name, sex='M', email=None, spawn_room="village_center"):
        self.name = name
        self.email = email
        self.sex = sex
        self.points = 0
        self.inventory = []  # List of Item objects
        self.stamina = levels[0]['stamina']
        self.max_stamina = levels[0]['stamina']
        self.strength = levels[0]['strength']  # Strength determines max weight (in kg)
        self.dexterity = levels[0]['dexterity']
        self.magic = levels[0]['magic']
        self.carrying_capacity_num = levels[0]['carrying_capacity_num']  # Max number of items
        self.level = levels[0]['name']
        self.visited = set()
        self.current_level_at = 0
        self.next_level_at = 400
        self.created_at = datetime.now()
        self.current_room = spawn_room  # Always start at spawn room on login/restart
        self.last_active = datetime.now()

    def level_up(self, sio=None, online_sessions=None):
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
        self.level = new_level['name']
        self.stamina = new_level['stamina']
        self.max_stamina = new_level['stamina']
        self.strength = new_level['strength']
        self.dexterity = new_level['dexterity']
        self.magic = new_level['magic']
        self.carrying_capacity_num = new_level['carrying_capacity_num']
        
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
                if session.get('player') == self:
                    # Send the level up notification to the player
                    notification = f"Your level of experience is now {self.level}."
                    asyncio.create_task(sio.emit('message', notification, room=sid))
                    break
                    
        # Return whether the level changed
        return leveled_up
    
    def add_visited(self, room_id):
        self.visited.add(room_id)

    def add_points(self, points, sio=None, online_sessions=None):
        """
        Add points to the player's score and update level if needed.
        Sends points notification and triggers level-up notification if applicable.
        
        Args:
            points (int): The number of points to add
            sio (SocketIO, optional): Socket.IO instance for sending messages
            online_sessions (dict, optional): Dictionary of online sessions
            
        Returns:
            bool: Whether the player leveled up
        """
        self.points += points
        
        # Send points notification
        if sio and online_sessions:
            # Find the player's session ID
            for sid, session in online_sessions.items():
                if session.get('player') == self:
                    # Send just the points notification to the player
                    notification = f"[{self.points}]"
                    asyncio.create_task(sio.emit('message', notification, room=sid))
                    break
        
        # Call level_up to recalculate level based on new point total
        # Pass sio and online_sessions so level_up can send its own notification
        leveled_up = self.level_up(sio, online_sessions)
            
        return leveled_up

    def total_inventory_weight(self):
        return sum(item.weight for item in self.inventory)

    def add_item(self, item):
        if item.takeable == False:
            return False, "Don't be ridiculous!"
        # Check number capacity
        if len(self.inventory) >= self.carrying_capacity_num:
            return False, "You are carrying too many items."
        # Check weight capacity: weight capacity is equal to player's strength
        if self.total_inventory_weight() + item.weight > self.strength:
            return False, "This item is too heavy to carry."
        self.inventory.append(item)
        return True, f"{item.name} taken."

    def remove_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)
            return True, f"{item.name} dropped."
        return False, "Item not found in your inventory."

    def drop_all_items(self):
        dropped_items = self.inventory.copy()
        self.inventory.clear()
        return dropped_items

    def set_current_room(self, room_id):
        self.current_room = room_id

    def update_activity(self):
        self.last_active = datetime.now()

    def return_summary(self):
        inv_items = ", ".join(item.name for item in self.inventory) if self.inventory else "None"
        return {
            "name": self.name,
            "level": self.level,
            "points": self.points,
            "stamina": self.stamina,
            "inventory": inv_items,
            "current_room": self.current_room,
            "last_active": self.last_active.isoformat(),
        }

    def to_dict(self):
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
    def from_dict(data):
        player = Player(data["name"], data.get("sex", "M"), data.get("email"), spawn_room=data.get("current_room", "village_center"))
        player.points = data["points"]
        inventory_data = data.get("inventory", [])
        player.inventory = [Item.from_dict(item_data) for item_data in inventory_data]
        player.level = data["level"]
        player.current_room = data["current_room"]
        return player