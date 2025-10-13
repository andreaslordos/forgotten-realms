# backend/managers/auth.py

import json
import os
import hashlib
from typing import Dict


class AuthManager:
    save_file: str
    credentials: Dict[str, str]

    def __init__(self, save_file: str = "storage/auth.json") -> None:
        self.save_file = save_file
        self.credentials = {}
        # Ensure storage directory exists
        directory = os.path.dirname(self.save_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        self.load_credentials()

    def load_credentials(self) -> None:
        if os.path.exists(self.save_file):
            with open(self.save_file, "r") as f:
                self.credentials = json.load(f)
        else:
            self.credentials = {}

    def save_credentials(self) -> None:
        with open(self.save_file, "w") as f:
            json.dump(self.credentials, f, indent=4)

    def hash_password(self, username: str, password: str) -> str:
        salted = password + username
        return hashlib.sha256(salted.encode("utf-8")).hexdigest()

    def register(self, username: str, password: str) -> bool:
        uname = username.lower()
        if uname in self.credentials:
            raise Exception("User already exists.")
        hashed = self.hash_password(uname, password)
        self.credentials[uname] = hashed
        self.save_credentials()
        return True

    def login(self, username: str, password: str) -> bool:
        uname = username.lower()
        hashed = self.hash_password(uname, password)
        if uname in self.credentials and self.credentials[uname] == hashed:
            return True
        else:
            raise Exception("Invalid credentials")
