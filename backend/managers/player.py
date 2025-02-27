# backend/managers/player.py

import json
import os
from models.player import Player

class PlayerManager:
    def __init__(self, save_file="storage/players.json", spawn_room="room_1_1"):
        self.save_file = save_file
        self.players = {}
        self.spawn_room = spawn_room
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
            json.dump({name: p.to_dict() for name, p in self.players.items()}, f, indent=4)

    def load_players(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, "r") as f:
                data = json.load(f)
                self.players = {name: Player.from_dict(p_data) for name, p_data in data.items()}
