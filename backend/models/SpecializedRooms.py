# backend/models/SpecializedRooms.py

from models.Room import Room

class SwampRoom(Room):
    """
    A specialized room for swamp areas that can consume treasure and award points.
    """
    def __init__(self, room_id, name, description, exits=None, treasure_destination=None, awards_points=True):
        """
        Initialize a SwampRoom.
        
        Args:
            room_id (str): Unique identifier for the room
            name (str): Display name of the room
            description (str): Text description of the room
            exits (dict): Dictionary mapping directions to destination room IDs
            treasure_destination (str): Room ID where treasure gets moved when dropped
            awards_points (bool): Whether dropping treasure here rewards points
        """
        super().__init__(room_id, name, description, exits)
        self.treasure_destination = treasure_destination
        self.awards_points = awards_points
    
    def handle_treasure_drop(self, item, player, game_state, player_manager=None, sio=None, online_sessions=None):
        """
        Special handler for when treasure is dropped in this room.
        
        Args:
            item: The treasure item being dropped
            player: The player dropping the item
            game_state: The game state
            player_manager: Optional player manager for saving player state
            sio: Optional socket.io instance for notifications
            online_sessions: Optional session data for notifications
            
        Returns:
            tuple: (bool, str) indicating success and a message
        """
        points_awarded = 0
        
        # Move the item to the destination room if specified
        if self.treasure_destination:
            dest_room = game_state.get_room(self.treasure_destination)
            if dest_room:
                dest_room.add_item(item)
            
        # Award points if enabled
        if self.awards_points and hasattr(item, 'value') and item.value > 0:
            points_awarded = item.value
            if player_manager:
                player.add_points(points_awarded, sio, online_sessions)
                player_manager.save_players()
        
        return True, f"{item.name.capitalize()} dropped."
    
    def to_dict(self):
        """Convert the SwampRoom to a dictionary for serialization."""
        data = super().to_dict()
        data["room_type"] = "swamp"  # Add type identifier
        data["treasure_destination"] = self.treasure_destination
        data["awards_points"] = self.awards_points
        return data
    
    @staticmethod
    def from_dict(data):
        """Create a SwampRoom from a dictionary representation."""
        return SwampRoom(
            data["room_id"],
            data["name"],
            data["description"],
            exits=data.get("exits", {}),
            treasure_destination=data.get("treasure_destination"),
            awards_points=data.get("awards_points", True)
        )