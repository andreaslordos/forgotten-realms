from models.item import Item

class Room:
    def __init__(self, room_id, name, description, exits=None):
        self.room_id = room_id
        self.name = name
        self.description = description
        self.items = []  # Holds all items (spawned/dropped) in the room
        self.exits = exits if exits is not None else {}  # e.g., {"north": "room_0_1", "east": "room_1_2"}

    def add_item(self, item):
        self.items.append(item)

    def remove_item(self, item):
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def get_items(self):
        return self.items

    def to_dict(self):
        return {
            "room_id": self.room_id,
            "name": self.name,
            "description": self.description,
            "items": [item.to_dict() for item in self.items],
            "exits": self.exits,
        }

    @staticmethod
    def from_dict(data):
        room = Room(data["room_id"], data["name"], data["description"], exits=data.get("exits", {}))
        room.items = [Item.from_dict(item_data) for item_data in data.get("items", [])]
        return room

    def __repr__(self):
        return f"Room({self.room_id}, exits: {self.exits}, items: {self.items})"
