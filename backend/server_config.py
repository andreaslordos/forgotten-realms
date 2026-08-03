"""Runtime network configuration for the Socket.IO server."""

from dataclasses import dataclass
import os
from pathlib import Path
import ssl
from typing import Mapping, Optional

DEFAULT_CERT_FILE = Path("/etc/letsencrypt/live/api.realms.lordos.tech/fullchain.pem")
DEFAULT_KEY_FILE = Path("/etc/letsencrypt/live/api.realms.lordos.tech/privkey.pem")
TLS_MODES = {"disabled", "letsencrypt"}


@dataclass(frozen=True)
class ServerConfig:
    """Configuration needed to bind the backend listener."""

    bind_host: str
    port: int
    tls_mode: str
    cert_file: Path
    key_file: Path

    @property
    def tls_enabled(self) -> bool:
        return self.tls_mode != "disabled"

    @classmethod
    def from_env(
        cls,
        *,
        test_mode: bool = False,
        environ: Optional[Mapping[str, str]] = None,
    ) -> "ServerConfig":
        """Build configuration while preserving the legacy production defaults."""
        values = os.environ if environ is None else environ
        bind_host = values.get("SERVER_BIND_HOST", "0.0.0.0").strip()
        if not bind_host:
            raise ValueError("SERVER_BIND_HOST cannot be empty")

        raw_port = values.get("PORT", "8080").strip()
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ValueError("PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")

        default_tls_mode = "disabled" if test_mode else "letsencrypt"
        tls_mode = values.get("SERVER_TLS_MODE", default_tls_mode).strip().lower()
        if tls_mode not in TLS_MODES:
            supported = ", ".join(sorted(TLS_MODES))
            raise ValueError(f"SERVER_TLS_MODE must be one of: {supported}")
        if (
            not test_mode
            and tls_mode == "disabled"
            and bind_host not in {"127.0.0.1", "::1", "localhost"}
        ):
            raise ValueError(
                "SERVER_TLS_MODE=disabled requires a loopback SERVER_BIND_HOST"
            )

        return cls(
            bind_host=bind_host,
            port=port,
            tls_mode=tls_mode,
            cert_file=Path(values.get("SERVER_CERT_FILE", str(DEFAULT_CERT_FILE))),
            key_file=Path(values.get("SERVER_KEY_FILE", str(DEFAULT_KEY_FILE))),
        )


def build_ssl_context(config: ServerConfig) -> Optional[ssl.SSLContext]:
    """Create the configured TLS context, or none for a local Tunnel origin."""
    if not config.tls_enabled:
        return None

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(
        certfile=str(config.cert_file),
        keyfile=str(config.key_file),
    )
    return context
