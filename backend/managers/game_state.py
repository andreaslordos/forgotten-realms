import json
import os
from models.room import Room

class GameState:
    def __init__(self, save_file="backend/storage/rooms.json"):
        self.save_file = save_file
        self.rooms = {}
        self.load_rooms()

    def add_room(self, room):
        self.rooms[room.room_id] = room
        self.save_rooms()

    def get_room(self, room_id):
        return self.rooms.get(room_id, None)

    def save_rooms(self):
        with open(self.save_file, "w") as f:
            json.dump({rid: r.to_dict() for rid, r in self.rooms.items()}, f, indent=4)

    def load_rooms(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, "r") as f:
                data = json.load(f)
                self.rooms = {rid: Room.from_dict(r_data) for rid, r_data in data.items()}
