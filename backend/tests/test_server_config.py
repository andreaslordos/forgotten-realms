import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server_config import ServerConfig  # noqa: E402


class TestServerConfig(unittest.TestCase):
    """Test ServerConfig.from_env listener configuration."""

    def test_from_env_defaults_to_loopback_tunnel_origin(self) -> None:
        """Test from_env defaults production to 127.0.0.1:8080."""
        # Act
        config = ServerConfig.from_env(environ={})

        # Assert
        self.assertEqual(config.bind_host, "127.0.0.1")
        self.assertEqual(config.port, 8080)

    def test_from_env_test_mode_defaults_to_loopback(self) -> None:
        """Test from_env keeps test mode off the local network by default."""
        # Act
        config = ServerConfig.from_env(test_mode=True, environ={})

        # Assert
        self.assertEqual(config.bind_host, "127.0.0.1")

    def test_from_env_accepts_explicit_host_and_port(self) -> None:
        """Test from_env reads SERVER_BIND_HOST and PORT from the environment."""
        # Arrange
        environ = {"SERVER_BIND_HOST": "::1", "PORT": "9090"}

        # Act
        config = ServerConfig.from_env(environ=environ)

        # Assert
        self.assertEqual(config.bind_host, "::1")
        self.assertEqual(config.port, 9090)

    def test_from_env_accepts_localhost_in_production(self) -> None:
        """Test from_env treats localhost as a loopback bind."""
        # Act
        config = ServerConfig.from_env(environ={"SERVER_BIND_HOST": "localhost"})

        # Assert
        self.assertEqual(config.bind_host, "localhost")

    def test_from_env_rejects_public_bind_in_production(self) -> None:
        """Test from_env refuses to serve plain HTTP on a public interface."""
        for bind_host in ("0.0.0.0", "::"):
            with self.subTest(bind_host=bind_host):
                # Act / Assert
                with self.assertRaisesRegex(ValueError, "loopback"):
                    ServerConfig.from_env(environ={"SERVER_BIND_HOST": bind_host})

    def test_from_env_allows_public_bind_in_test_mode(self) -> None:
        """Test from_env lets test mode opt in to a local-network bind."""
        # Act
        config = ServerConfig.from_env(
            test_mode=True, environ={"SERVER_BIND_HOST": "0.0.0.0"}
        )

        # Assert
        self.assertEqual(config.bind_host, "0.0.0.0")

    def test_from_env_rejects_empty_bind_host(self) -> None:
        """Test from_env rejects a blank SERVER_BIND_HOST."""
        # Act / Assert
        with self.assertRaisesRegex(ValueError, "SERVER_BIND_HOST cannot be empty"):
            ServerConfig.from_env(environ={"SERVER_BIND_HOST": "  "})

    def test_from_env_rejects_invalid_port(self) -> None:
        """Test from_env rejects non-integer and out-of-range ports."""
        for raw_port in ("http", "0", "70000"):
            with self.subTest(port=raw_port):
                # Act / Assert
                with self.assertRaisesRegex(ValueError, "PORT"):
                    ServerConfig.from_env(environ={"PORT": raw_port})


if __name__ == "__main__":
    unittest.main()
