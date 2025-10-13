# backend/managers/map_generator.py

from typing import Dict
from models.Room import Room


def generate_3x3_grid() -> Dict[str, Room]:
    """
    Generates a 3x3 grid of rooms with proper exits.
    Returns a dictionary mapping room_id to Room objects.
    """
    rooms: Dict[str, Room] = {}
    grid_size: int = 3
    for row in range(grid_size):
        for col in range(grid_size):
            room_id: str = f"room_{row}_{col}"
            name: str = f"Room ({row}, {col})"
            description: str = f"This is the room located at position ({row}, {col})."
            exits: Dict[str, str] = {}
            if row > 0:
                exits["north"] = f"room_{row-1}_{col}"
            if row < grid_size - 1:
                exits["south"] = f"room_{row+1}_{col}"
            if col > 0:
                exits["west"] = f"room_{row}_{col-1}"
            if col < grid_size - 1:
                exits["east"] = f"room_{row}_{col+1}"
            room: Room = Room(room_id, name, description, exits)
            rooms[room_id] = room
    return rooms
