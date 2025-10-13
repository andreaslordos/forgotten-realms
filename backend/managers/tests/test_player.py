"""
Comprehensive tests for PlayerManager module.

Tests cover:
- PlayerManager initialization
- Player registration
- Player login
- Player save/load
- Inventory clearing behavior
- Integration with auth_manager
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import os
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.player import PlayerManager
from models.Player import Player


class PlayerManagerInitializationTest(unittest.TestCase):
    """Test PlayerManager initialization."""

    def test___init___sets_default_save_file(self):
        """Test __init__ sets default save file path."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            self.assertEqual(pm.save_file, temp_file)
        finally:
            os.remove(temp_file)

    def test___init___sets_default_spawn_room(self):
        """Test __init__ sets default spawn room."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            self.assertEqual(pm.spawn_room, "spawn")
        finally:
            os.remove(temp_file)

    def test___init___accepts_custom_spawn_room(self):
        """Test __init__ accepts custom spawn room."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file, spawn_room="custom_spawn")
            self.assertEqual(pm.spawn_room, "custom_spawn")
        finally:
            os.remove(temp_file)

    def test___init___stores_auth_manager_reference(self):
        """Test __init__ stores auth_manager reference."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            mock_auth = Mock()
            pm = PlayerManager(save_file=temp_file, auth_manager=mock_auth)
            self.assertEqual(pm.auth_manager, mock_auth)
        finally:
            os.remove(temp_file)

    def test___init___initializes_empty_players_dict(self):
        """Test __init__ initializes empty players dict."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            os.remove(temp_file)  # Remove so it doesn't exist
            pm = PlayerManager(save_file=temp_file)
            self.assertEqual(pm.players, {})
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test___init___loads_existing_players(self):
        """Test __init__ loads existing players from file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Create player data
            player_data = {
                "testplayer": {
                    "name": "TestPlayer",
                    "sex": "M",
                    "points": 500,
                    "inventory": [],
                    "level": "Novice",
                    "current_room": "spawn"
                }
            }
            json.dump(player_data, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            self.assertIn("testplayer", pm.players)
            self.assertEqual(pm.players["testplayer"].name, "TestPlayer")
        finally:
            os.remove(temp_file)


class PlayerManagerRegisterTest(unittest.TestCase):
    """Test PlayerManager.register functionality."""

    def test_register_creates_new_player(self):
        """Test register creates new player."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player = pm.register("TestPlayer")

            self.assertIsNotNone(player)
            self.assertIsInstance(player, Player)
        finally:
            os.remove(temp_file)

    def test_register_converts_username_to_lowercase(self):
        """Test register converts username to lowercase for storage."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player = pm.register("TestPlayer")

            self.assertIn("testplayer", pm.players)
            self.assertNotIn("TestPlayer", pm.players)
        finally:
            os.remove(temp_file)

    def test_register_capitalizes_display_name(self):
        """Test register capitalizes display name."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player = pm.register("testplayer")

            self.assertEqual(player.name, "Testplayer")
        finally:
            os.remove(temp_file)

    def test_register_sets_sex(self):
        """Test register sets player sex."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player = pm.register("TestPlayer", sex='F')

            self.assertEqual(player.sex, 'F')
        finally:
            os.remove(temp_file)

    def test_register_sets_email(self):
        """Test register sets player email."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player = pm.register("TestPlayer", email="test@example.com")

            self.assertEqual(player.email, "test@example.com")
        finally:
            os.remove(temp_file)

    def test_register_uses_spawn_room_from_manager(self):
        """Test register uses spawn room from manager."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file, spawn_room="custom_spawn")
            player = pm.register("TestPlayer")

            self.assertEqual(player.current_room, "custom_spawn")
        finally:
            os.remove(temp_file)

    def test_register_returns_existing_player_if_already_registered(self):
        """Test register returns existing player if already registered."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player1 = pm.register("TestPlayer")
            player1.points = 100  # Modify to verify it's the same object

            player2 = pm.register("TestPlayer")

            self.assertEqual(player1, player2)
            self.assertEqual(player2.points, 100)
        finally:
            os.remove(temp_file)

    def test_register_saves_players_to_file(self):
        """Test register saves players to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            pm.register("TestPlayer")

            # Verify file was written
            with open(temp_file, 'r') as f:
                data = json.load(f)

            self.assertIn("testplayer", data)
        finally:
            os.remove(temp_file)

    def test_register_adds_player_to_players_dict(self):
        """Test register adds player to players dict."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player = pm.register("TestPlayer")

            self.assertIn("testplayer", pm.players)
            self.assertEqual(pm.players["testplayer"], player)
        finally:
            os.remove(temp_file)


class PlayerManagerLoginTest(unittest.TestCase):
    """Test PlayerManager.login functionality."""

    def test_login_returns_player_when_exists(self):
        """Test login returns player when exists."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            registered_player = pm.register("TestPlayer")

            player = pm.login("TestPlayer")

            self.assertEqual(player, registered_player)
        finally:
            os.remove(temp_file)

    def test_login_returns_none_when_player_not_found(self):
        """Test login returns None when player doesn't exist."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)

            player = pm.login("NonExistent")

            self.assertIsNone(player)
        finally:
            os.remove(temp_file)

    def test_login_is_case_insensitive(self):
        """Test login is case insensitive."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            registered_player = pm.register("TestPlayer")

            player1 = pm.login("testplayer")
            player2 = pm.login("TESTPLAYER")
            player3 = pm.login("TestPlayer")

            self.assertEqual(player1, registered_player)
            self.assertEqual(player2, registered_player)
            self.assertEqual(player3, registered_player)
        finally:
            os.remove(temp_file)


class PlayerManagerSaveLoadTest(unittest.TestCase):
    """Test PlayerManager save/load functionality."""

    def test_save_players_writes_to_file(self):
        """Test save_players writes players to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            pm.register("TestPlayer1")
            pm.register("TestPlayer2")

            pm.save_players()

            with open(temp_file, 'r') as f:
                data = json.load(f)

            self.assertEqual(len(data), 2)
            self.assertIn("testplayer1", data)
            self.assertIn("testplayer2", data)
        finally:
            os.remove(temp_file)

    def test_save_players_clears_inventory_before_saving(self):
        """Test save_players clears inventory before saving."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player = pm.register("TestPlayer")

            # Add mock item to inventory
            mock_item = Mock()
            player.inventory.append(mock_item)

            pm.save_players()

            with open(temp_file, 'r') as f:
                data = json.load(f)

            # Inventory should be empty in saved data
            self.assertEqual(data["testplayer"]["inventory"], [])
        finally:
            os.remove(temp_file)

    def test_save_players_uses_player_to_dict(self):
        """Test save_players uses player.to_dict method."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)
            player = pm.register("TestPlayer")
            player.points = 500

            pm.save_players()

            with open(temp_file, 'r') as f:
                data = json.load(f)

            self.assertEqual(data["testplayer"]["points"], 500)
            self.assertEqual(data["testplayer"]["name"], "Testplayer")
        finally:
            os.remove(temp_file)

    def test_load_players_loads_from_existing_file(self):
        """Test load_players loads players from existing file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            player_data = {
                "player1": {
                    "name": "Player1",
                    "sex": "M",
                    "points": 100,
                    "inventory": [],
                    "level": "Neophyte",
                    "current_room": "spawn"
                },
                "player2": {
                    "name": "Player2",
                    "sex": "F",
                    "points": 500,
                    "inventory": [],
                    "level": "Novice",
                    "current_room": "spawn"
                }
            }
            json.dump(player_data, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)

            self.assertEqual(len(pm.players), 2)
            self.assertIn("player1", pm.players)
            self.assertIn("player2", pm.players)
        finally:
            os.remove(temp_file)

    def test_load_players_creates_player_objects_from_dict(self):
        """Test load_players creates Player objects from dict."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            player_data = {
                "testplayer": {
                    "name": "TestPlayer",
                    "sex": "M",
                    "points": 800,
                    "inventory": [],
                    "level": "Acolyte",
                    "current_room": "spawn"
                }
            }
            json.dump(player_data, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)

            player = pm.players["testplayer"]
            self.assertIsInstance(player, Player)
            self.assertEqual(player.name, "TestPlayer")
            self.assertEqual(player.points, 800)
        finally:
            os.remove(temp_file)

    def test_load_players_ensures_empty_inventory(self):
        """Test load_players ensures all loaded players have empty inventory."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            # Save player with items in inventory (shouldn't happen, but test it)
            player_data = {
                "testplayer": {
                    "name": "TestPlayer",
                    "sex": "M",
                    "points": 100,
                    "inventory": [{
                        "id": "sword_1",
                        "name": "iron sword",
                        "description": "A basic sword",
                        "keywords": ["sword", "iron"],
                        "room_id": None,
                        "takeable": True,
                        "weight": 5,
                        "interactions": {}
                    }],  # Has items
                    "level": "Neophyte",
                    "current_room": "spawn"
                }
            }
            json.dump(player_data, f)
            temp_file = f.name

        try:
            pm = PlayerManager(save_file=temp_file)

            player = pm.players["testplayer"]
            # Inventory should be cleared by load_players
            self.assertEqual(player.inventory, [])
        finally:
            os.remove(temp_file)

    def test_load_players_handles_missing_file(self):
        """Test load_players handles missing file gracefully."""
        temp_file = "/tmp/nonexistent_players_test.json"

        # Ensure file doesn't exist
        if os.path.exists(temp_file):
            os.remove(temp_file)

        try:
            pm = PlayerManager(save_file=temp_file)
            # Should not crash, just have empty players dict
            self.assertEqual(pm.players, {})
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_players_persist_across_instances(self):
        """Test players persist across PlayerManager instances."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            # First instance - register player
            pm1 = PlayerManager(save_file=temp_file)
            pm1.register("TestPlayer", sex='F')
            player1 = pm1.players["testplayer"]
            player1.points = 500

            # Save explicitly
            pm1.save_players()

            # Second instance - should load same player
            pm2 = PlayerManager(save_file=temp_file)
            player2 = pm2.login("TestPlayer")

            self.assertIsNotNone(player2)
            self.assertEqual(player2.name, "Testplayer")
            self.assertEqual(player2.sex, 'F')
            self.assertEqual(player2.points, 500)
        finally:
            os.remove(temp_file)


if __name__ == "__main__":
    unittest.main()
