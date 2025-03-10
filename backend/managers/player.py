# backend/managers/player.py

import json
import os
from models.Player import Player

class PlayerManager:
    def __init__(self, save_file="storage/players.json", spawn_room="spawn", auth_manager=None):
        self.save_file = save_file
        self.players = {}
        self.spawn_room = spawn_room
        self.auth_manager = auth_manager  # Store reference to auth_manager
        self.load_players()

    def register(self, name, sex='M', email=None):
        uname = name.lower()
        if uname in self.players:
            return self.players[uname]
        display_name = name.capitalize()
        new_player = Player(display_name, sex, email, spawn_room=self.spawn_room)
        self.players[uname] = new_player
        self.save_players()
        return new_player

    def login(self, name):
        return self.players.get(name.lower(), None)

    def save_players(self):
        with open(self.save_file, "w") as f:
            # Create a dictionary of player data without inventory
            player_data = {}
            for name, player in self.players.items():
                player_dict = player.to_dict()
                player_dict['inventory'] = []  # Clear inventory before saving
                player_data[name] = player_dict
            json.dump(player_data, f, indent=4)

    def load_players(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, "r") as f:
                data = json.load(f)
                self.players = {name: Player.from_dict(p_data) for name, p_data in data.items()}
                # Ensure all loaded players start with empty inventory
                for player in self.players.values():
                    player.inventory = []
