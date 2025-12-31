# backend/globals.py

from typing import Any, Dict

online_sessions: Dict[str, Dict[str, Any]] = {}
version: str = "0.76"
SPAWN_ROOM: str = "square"  # Default spawn room for new/respawning players
