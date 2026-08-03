import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server_config import (  # noqa: E402
    DEFAULT_CERT_FILE,
    DEFAULT_KEY_FILE,
    ServerConfig,
    build_ssl_context,
)


class TestServerConfig(unittest.TestCase):
    def test_from_env_preserves_legacy_production_defaults(self) -> None:
        config = ServerConfig.from_env(environ={})

        self.assertEqual(config.bind_host, "0.0.0.0")
        self.assertEqual(config.port, 8080)
        self.assertEqual(config.tls_mode, "letsencrypt")
        self.assertEqual(config.cert_file, DEFAULT_CERT_FILE)
        self.assertEqual(config.key_file, DEFAULT_KEY_FILE)

    def test_from_env_test_mode_disables_tls_by_default(self) -> None:
        config = ServerConfig.from_env(test_mode=True, environ={})

        self.assertEqual(config.tls_mode, "disabled")
        self.assertFalse(config.tls_enabled)

    def test_from_env_supports_loopback_tunnel_origin(self) -> None:
        config = ServerConfig.from_env(
            environ={
                "SERVER_BIND_HOST": "127.0.0.1",
                "PORT": "9090",
                "SERVER_TLS_MODE": "disabled",
            }
        )

        self.assertEqual(config.bind_host, "127.0.0.1")
        self.assertEqual(config.port, 9090)
        self.assertFalse(config.tls_enabled)

    def test_from_env_rejects_invalid_tls_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "SERVER_TLS_MODE"):
            ServerConfig.from_env(environ={"SERVER_TLS_MODE": "sometimes"})

    def test_from_env_rejects_plaintext_on_a_public_production_bind(self) -> None:
        with self.assertRaisesRegex(ValueError, "loopback"):
            ServerConfig.from_env(
                environ={
                    "SERVER_BIND_HOST": "0.0.0.0",
                    "SERVER_TLS_MODE": "disabled",
                }
            )

    def test_from_env_rejects_invalid_port(self) -> None:
        with self.assertRaisesRegex(ValueError, "PORT"):
            ServerConfig.from_env(environ={"PORT": "70000"})

    @patch("server_config.ssl.create_default_context")
    def test_build_ssl_context_loads_configured_certificate(
        self, create_default_context: Mock
    ) -> None:
        context = Mock()
        create_default_context.return_value = context
        config = ServerConfig.from_env(
            environ={
                "SERVER_CERT_FILE": "/tmp/server.crt",
                "SERVER_KEY_FILE": "/tmp/server.key",
            }
        )

        self.assertIs(build_ssl_context(config), context)
        context.load_cert_chain.assert_called_once_with(
            certfile="/tmp/server.crt",
            keyfile="/tmp/server.key",
        )

    @patch("server_config.ssl.create_default_context")
    def test_build_ssl_context_skips_tls_when_disabled(
        self, create_default_context: Mock
    ) -> None:
        config = ServerConfig.from_env(
            environ={
                "SERVER_BIND_HOST": "127.0.0.1",
                "SERVER_TLS_MODE": "disabled",
            }
        )

        self.assertIsNone(build_ssl_context(config))
        create_default_context.assert_not_called()


if __name__ == "__main__":
    unittest.main()
