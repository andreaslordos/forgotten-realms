import json
import os
import hashlib

class AuthManager:
    def __init__(self, save_file="storage/auth.json"):
        self.save_file = save_file
        self.credentials = {}
        self.load_credentials()

    def load_credentials(self):
        if os.path.exists(self.save_file):
            with open(self.save_file, "r") as f:
                self.credentials = json.load(f)
        else:
            self.credentials = {}

    def save_credentials(self):
        with open(self.save_file, "w") as f:
            json.dump(self.credentials, f, indent=4)

    def hash_password(self, username, password):
        salted = password + username
        return hashlib.sha256(salted.encode("utf-8")).hexdigest()

    def register(self, username, password):
        uname = username.lower()
        if uname in self.credentials:
            raise Exception("User already exists.")
        hashed = self.hash_password(uname, password)
        self.credentials[uname] = hashed
        self.save_credentials()
        return True

    def login(self, username, password):
        uname = username.lower()
        hashed = self.hash_password(uname, password)
        if uname in self.credentials and self.credentials[uname] == hashed:
            return True
        else:
            raise Exception("Invalid credentials")
