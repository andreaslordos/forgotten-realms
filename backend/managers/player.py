# backend/managers/player.py

import json
import os
from typing import Dict, Optional
from models.Player import Player
from managers.auth import AuthManager
from globals import SPAWN_ROOM


class PlayerManager:
    save_file: str
    players: Dict[str, Player]
    spawn_room: str
    auth_manager: Optional[AuthManager]

    def __init__(
        self,
        save_file: str = "storage/players.json",
        spawn_room: str = SPAWN_ROOM,
        auth_manager: Optional[AuthManager] = None,
    ) -> None:
        self.save_file = save_file
        self.players = {}
        self.spawn_room = spawn_room
        self.auth_manager = auth_manager  # Store reference to auth_manager
        self.load_players()

    def register(
        self, name: str, sex: str = "M", email: Optional[str] = None
    ) -> Player:
        uname = name.lower()
        if uname in self.players:
            return self.players[uname]
        display_name = name.capitalize()
        new_player = Player(display_name, sex, email, spawn_room=self.spawn_room)
        self.players[uname] = new_player
        self.save_players()
        return new_player

    def login(self, name: str) -> Optional[Player]:
        return self.players.get(name.lower(), None)

    def delete_player(self, name: str) -> bool:
        """
        Delete a player's persona and authentication credentials permanently.

        Args:
            name (str): The player's name (case-insensitive)

        Returns:
            bool: True if player was deleted, False if player not found
        """
        uname = name.lower()
        if uname in self.players:
            del self.players[uname]
            self.save_players()

            # Also delete authentication credentials if auth_manager is available
            if self.auth_manager:
                self.auth_manager.delete_user(uname)

            return True
        return False

    def save_players(self) -> None:
        with open(self.save_file, "w") as f:
            # Create a dictionary of player data without inventory
            player_data: Dict[str, Dict[str, object]] = {}
            for name, player in self.players.items():
                player_dict = player.to_dict()
                player_dict["inventory"] = []  # Clear inventory before saving
                player_data[name] = player_dict
            json.dump(player_data, f, indent=4)

    def load_players(self) -> None:
        if os.path.exists(self.save_file):
            with open(self.save_file, "r") as f:
                data = json.load(f)
                self.players = {
                    name: Player.from_dict(p_data) for name, p_data in data.items()
                }
                # Ensure all loaded players start with empty inventory
                for player in self.players.values():
                    player.inventory = []
