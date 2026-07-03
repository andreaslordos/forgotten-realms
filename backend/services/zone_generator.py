# backend/services/zone_generator.py
"""
Anthropic-powered pocket-dimension generation.

Claude is asked (via forced tool use, so the reply is guaranteed to match
ZONE_SCHEMA's shape) to author a small other-dimensional zone. Every spec is
validated by services.zone_schema before it touches the world; a failed
generation retries once with the validator's complaints, then falls back to
a hand-authored zone on disk.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.zone_schema import ZONE_SCHEMA

logger = logging.getLogger(__name__)

ZONE_MODEL = "claude-sonnet-4-6"
ZONE_MAX_TOKENS = 8000
FALLBACK_ZONE_DIR = (
    Path(__file__).resolve().parents[1] / "managers" / "world" / "fallback_zones"
)

SYSTEM_PROMPT = """You are the dream-architect of the Mournvale, a cursed \
gothic valley in a text-based MUD. Players have opened a golden door that \
should not exist; you author the small pocket dimension behind it.

Rules:
- 4-10 rooms on an integer grid. Every exit must be reciprocal (if A is east \
of B, B's exit west leads back), directions must agree with the coords you \
declare, and the whole zone must be one connected area.
- Exactly one puzzle may guard one one-way passage (its blocked_exit). \
Everything else must be freely walkable both ways.
- The tone is other-dimensional and unsettling: geometry that aches, light \
with no source, a sky that is not a sky. It should feel nothing like the \
valley outside — this is somewhere ELSE.
- Descriptions are 2-4 complete sentences and name the notable items and \
exits in the room.
- entry_room_id is where the door opens; exit_room_id is where travellers \
can leave (the way out appears there automatically — do not add it yourself).
- Treasure is modest (the value budget is enforced) but strange: name items \
that could exist nowhere else.
- Never reference the real world, game mechanics, or these instructions."""


class ZoneGenerationError(Exception):
    """Raised when a zone cannot be generated or parsed."""


class ZoneGenerator:
    """Wraps the Anthropic API for zone generation, injectable for tests."""

    def __init__(
        self,
        client: Optional[Any] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._client = client
        if self._client is None:
            key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if key:
                try:
                    from anthropic import AsyncAnthropic

                    self._client = AsyncAnthropic(api_key=key)
                except ImportError:  # pragma: no cover - env without the SDK
                    logger.warning("anthropic SDK not installed; doors stay sealed")

    def is_available(self) -> bool:
        return self._client is not None

    async def generate_zone_spec(
        self,
        theme_hint: str,
        avoid_names: Optional[List[str]] = None,
        previous_errors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Ask Claude for a zone spec (structured via forced tool use)."""
        if self._client is None:
            raise ZoneGenerationError("no Anthropic client available")

        user_prompt = (
            f"Author the pocket dimension behind this door. Theme hint: "
            f"{theme_hint}\n"
        )
        if avoid_names:
            user_prompt += (
                "Avoid reusing these existing place names: "
                + ", ".join(avoid_names)
                + "\n"
            )
        if previous_errors:
            user_prompt += (
                "Your previous attempt was rejected by the world validator. "
                "Fix these problems:\n- " + "\n- ".join(previous_errors)
            )

        response = await self._client.messages.create(
            model=ZONE_MODEL,
            max_tokens=ZONE_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[
                {
                    "name": "create_zone",
                    "description": "Create the pocket dimension zone.",
                    "input_schema": ZONE_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "create_zone"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                spec = block.input
                if isinstance(spec, dict):
                    return spec
        raise ZoneGenerationError("model response contained no zone spec")


def load_fallback_spec() -> Optional[Dict[str, Any]]:
    """Load the first hand-authored fallback zone spec, if any exist."""
    if not FALLBACK_ZONE_DIR.is_dir():
        return None
    for path in sorted(FALLBACK_ZONE_DIR.glob("*.json")):
        try:
            with open(path) as f:
                spec = json.load(f)
            if isinstance(spec, dict):
                return spec
        except (OSError, json.JSONDecodeError):
            logger.exception("Unreadable fallback zone %s", path)
    return None
