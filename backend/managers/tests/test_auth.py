"""
Comprehensive tests for auth module (managers).

Tests cover:
- AuthManager initialization
- Password hashing
- User registration
- User login
- Credential persistence
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import tempfile
import os
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from managers.auth import AuthManager


class AuthManagerInitializationTest(unittest.TestCase):
    """Test AuthManager initialization."""

    @patch('managers.auth.os.path.exists')
    @patch('managers.auth.os.makedirs')
    def test___init___creates_storage_directory(self, mock_makedirs, mock_exists):
        """Test __init__ creates storage directory if it doesn't exist."""
        mock_exists.return_value = False

        AuthManager(save_file="storage/auth.json")

        mock_makedirs.assert_called_once_with("storage")

    @patch('managers.auth.os.path.exists')
    @patch('managers.auth.os.makedirs')
    def test___init___skips_directory_creation_if_exists(self, mock_makedirs, mock_exists):
        """Test __init__ skips directory creation if it exists."""
        mock_exists.return_value = True

        with patch('builtins.open', mock_open(read_data='{}')):
            AuthManager(save_file="storage/auth.json")

        mock_makedirs.assert_not_called()

    def test___init___initializes_empty_credentials(self):
        """Test __init__ initializes empty credentials dict."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            os.remove(temp_file)  # Remove so it doesn't exist
            auth = AuthManager(save_file=temp_file)
            self.assertEqual(auth.credentials, {})
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test___init___loads_existing_credentials(self):
        """Test __init__ loads existing credentials from file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({"user1": "hash1", "user2": "hash2"}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            self.assertEqual(len(auth.credentials), 2)
            self.assertIn("user1", auth.credentials)
        finally:
            os.remove(temp_file)


class AuthManagerPasswordHashingTest(unittest.TestCase):
    """Test password hashing."""

    def test_hash_password_returns_string(self):
        """Test hash_password returns a string."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            hashed = auth.hash_password("user", "password")
            self.assertIsInstance(hashed, str)
        finally:
            os.remove(temp_file)

    def test_hash_password_is_deterministic(self):
        """Test hash_password returns same hash for same input."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            hash1 = auth.hash_password("user", "password")
            hash2 = auth.hash_password("user", "password")
            self.assertEqual(hash1, hash2)
        finally:
            os.remove(temp_file)

    def test_hash_password_uses_username_as_salt(self):
        """Test hash_password uses username as salt."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            hash1 = auth.hash_password("user1", "password")
            hash2 = auth.hash_password("user2", "password")
            self.assertNotEqual(hash1, hash2)
        finally:
            os.remove(temp_file)

    def test_hash_password_produces_different_hash_for_different_passwords(self):
        """Test hash_password produces different hashes for different passwords."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            hash1 = auth.hash_password("user", "password1")
            hash2 = auth.hash_password("user", "password2")
            self.assertNotEqual(hash1, hash2)
        finally:
            os.remove(temp_file)


class AuthManagerRegisterTest(unittest.TestCase):
    """Test user registration."""

    def test_register_adds_user_to_credentials(self):
        """Test register adds user to credentials."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.register("TestUser", "password123")

            self.assertIn("testuser", auth.credentials)
        finally:
            os.remove(temp_file)

    def test_register_converts_username_to_lowercase(self):
        """Test register converts username to lowercase."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.register("TestUser", "password123")

            self.assertIn("testuser", auth.credentials)
            self.assertNotIn("TestUser", auth.credentials)
        finally:
            os.remove(temp_file)

    def test_register_stores_hashed_password(self):
        """Test register stores hashed password, not plaintext."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.register("user", "password123")

            self.assertNotEqual(auth.credentials["user"], "password123")
        finally:
            os.remove(temp_file)

    def test_register_raises_exception_for_duplicate_user(self):
        """Test register raises exception for duplicate username."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.register("user", "password1")

            with self.assertRaises(Exception) as context:
                auth.register("user", "password2")

            self.assertIn("already exists", str(context.exception))
        finally:
            os.remove(temp_file)

    def test_register_returns_true_on_success(self):
        """Test register returns True on successful registration."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            result = auth.register("user", "password")

            self.assertTrue(result)
        finally:
            os.remove(temp_file)

    def test_register_saves_credentials_to_file(self):
        """Test register saves credentials to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.register("user", "password")

            # Load from file
            with open(temp_file, 'r') as f:
                data = json.load(f)

            self.assertIn("user", data)
        finally:
            os.remove(temp_file)


class AuthManagerLoginTest(unittest.TestCase):
    """Test user login."""

    def test_login_succeeds_with_correct_credentials(self):
        """Test login succeeds with correct username and password."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.register("user", "password123")

            result = auth.login("user", "password123")

            self.assertTrue(result)
        finally:
            os.remove(temp_file)

    def test_login_is_case_insensitive_for_username(self):
        """Test login is case insensitive for username."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.register("TestUser", "password123")

            result = auth.login("testuser", "password123")

            self.assertTrue(result)
        finally:
            os.remove(temp_file)

    def test_login_raises_exception_for_wrong_password(self):
        """Test login raises exception for incorrect password."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.register("user", "password123")

            with self.assertRaises(Exception) as context:
                auth.login("user", "wrongpassword")

            self.assertIn("Invalid credentials", str(context.exception))
        finally:
            os.remove(temp_file)

    def test_login_raises_exception_for_nonexistent_user(self):
        """Test login raises exception for nonexistent username."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)

            with self.assertRaises(Exception) as context:
                auth.login("nonexistent", "password")

            self.assertIn("Invalid credentials", str(context.exception))
        finally:
            os.remove(temp_file)


class AuthManagerPersistenceTest(unittest.TestCase):
    """Test credential persistence."""

    def test_save_credentials_writes_to_file(self):
        """Test save_credentials writes credentials to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.credentials = {"user1": "hash1", "user2": "hash2"}
            auth.save_credentials()

            with open(temp_file, 'r') as f:
                data = json.load(f)

            self.assertEqual(len(data), 2)
            self.assertEqual(data["user1"], "hash1")
        finally:
            os.remove(temp_file)

    def test_load_credentials_reads_from_file(self):
        """Test load_credentials reads credentials from file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({"user1": "hash1", "user2": "hash2"}, f)
            temp_file = f.name

        try:
            auth = AuthManager(save_file=temp_file)
            auth.credentials = {}
            auth.load_credentials()

            self.assertEqual(len(auth.credentials), 2)
            self.assertEqual(auth.credentials["user1"], "hash1")
        finally:
            os.remove(temp_file)

    def test_credentials_persist_across_instances(self):
        """Test credentials persist across AuthManager instances."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({}, f)
            temp_file = f.name

        try:
            # First instance - register user
            auth1 = AuthManager(save_file=temp_file)
            auth1.register("user", "password")

            # Second instance - should load same credentials
            auth2 = AuthManager(save_file=temp_file)
            result = auth2.login("user", "password")

            self.assertTrue(result)
        finally:
            os.remove(temp_file)


if __name__ == "__main__":
    unittest.main()
