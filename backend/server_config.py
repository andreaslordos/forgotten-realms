"""Runtime network configuration for the Socket.IO server."""

from dataclasses import dataclass
import os
from typing import Mapping, Optional

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


@dataclass(frozen=True)
class ServerConfig:
    """Configuration needed to bind the backend listener."""

    bind_host: str
    port: int

    @classmethod
    def from_env(
        cls,
        *,
        test_mode: bool = False,
        environ: Optional[Mapping[str, str]] = None,
    ) -> "ServerConfig":
        """Build configuration for a plain-HTTP listener behind Cloudflare Tunnel."""
        values = os.environ if environ is None else environ
        bind_host = values.get("SERVER_BIND_HOST", "127.0.0.1").strip()
        if not bind_host:
            raise ValueError("SERVER_BIND_HOST cannot be empty")

        raw_port = values.get("PORT", "8080").strip()
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ValueError("PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")

        # TLS ends at Cloudflare's edge, so production must never listen publicly.
        if not test_mode and bind_host not in LOOPBACK_HOSTS:
            raise ValueError(
                "SERVER_BIND_HOST must be loopback: the server speaks plain HTTP "
                "behind Cloudflare Tunnel"
            )

        return cls(bind_host=bind_host, port=port)
