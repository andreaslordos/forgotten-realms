from models.room import Room

def generate_3x3_grid():
    """
    Generates a 3x3 grid of rooms with proper exits.
    Returns a dictionary mapping room_id to Room objects.
    """
    rooms = {}
    grid_size = 3
    for row in range(grid_size):
        for col in range(grid_size):
            room_id = f"room_{row}_{col}"
            name = f"Room ({row}, {col})"
            description = f"This is the room located at position ({row}, {col})."
            exits = {}
            if row > 0:
                exits["north"] = f"room_{row-1}_{col}"
            if row < grid_size - 1:
                exits["south"] = f"room_{row+1}_{col}"
            if col > 0:
                exits["west"] = f"room_{row}_{col-1}"
            if col < grid_size - 1:
                exits["east"] = f"room_{row}_{col+1}"
            room = Room(room_id, name, description, exits)
            rooms[room_id] = room
    return rooms
