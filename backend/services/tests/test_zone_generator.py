# backend/services/tests/test_zone_generator.py
"""Tests for the Anthropic-backed zone generator (no network calls)."""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.zone_generator import (
    ZONE_MODEL,
    ZoneGenerationError,
    ZoneGenerator,
    load_fallback_spec,
)
from services.zone_schema import ZONE_SCHEMA


def make_fake_client(content):
    """Build a fake async Anthropic client returning the given content."""
    response = SimpleNamespace(content=content)
    return SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(return_value=response))
    )


class ZoneGeneratorAvailabilityTest(unittest.TestCase):
    """Test is_available and client-less construction."""

    def test_is_available_true_with_injected_client(self):
        """Test an injected client makes the generator available."""
        # Arrange
        client = make_fake_client([])

        # Act
        generator = ZoneGenerator(client=client)

        # Assert
        self.assertTrue(generator.is_available())

    def test_is_available_false_without_client_or_key(self):
        """Test no client and no API key leaves the generator unavailable."""
        # Arrange / Act
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            generator = ZoneGenerator()

        # Assert
        self.assertFalse(generator.is_available())


class GenerateZoneSpecTest(unittest.IsolatedAsyncioTestCase):
    """Test generate_zone_spec request shape and response parsing."""

    async def test_generate_zone_spec_raises_without_client(self):
        """Test generation without a client raises ZoneGenerationError."""
        # Arrange
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            generator = ZoneGenerator()

        # Act / Assert
        with self.assertRaises(ZoneGenerationError):
            await generator.generate_zone_spec("a theme")

    async def test_generate_zone_spec_returns_tool_use_input(self):
        """Test the tool_use block's input dict is returned as the spec."""
        # Arrange
        spec = {"zone_name": "The Test Zone"}
        block = SimpleNamespace(type="tool_use", input=spec)
        client = make_fake_client([block])
        generator = ZoneGenerator(client=client)

        # Act
        result = await generator.generate_zone_spec("a theme")

        # Assert
        self.assertIs(result, spec)

    async def test_generate_zone_spec_forces_create_zone_tool(self):
        """Test the API call uses ZONE_MODEL, forced tool choice and schema."""
        # Arrange
        block = SimpleNamespace(type="tool_use", input={"zone_name": "x"})
        client = make_fake_client([block])
        generator = ZoneGenerator(client=client)

        # Act
        await generator.generate_zone_spec("a theme")

        # Assert
        kwargs = client.messages.create.await_args.kwargs
        self.assertEqual(kwargs["model"], ZONE_MODEL)
        self.assertEqual(kwargs["tool_choice"], {"type": "tool", "name": "create_zone"})
        self.assertEqual(len(kwargs["tools"]), 1)
        self.assertEqual(kwargs["tools"][0]["name"], "create_zone")
        self.assertIs(kwargs["tools"][0]["input_schema"], ZONE_SCHEMA)

    async def test_generate_zone_spec_raises_without_tool_use_block(self):
        """Test a response with no tool_use block raises ZoneGenerationError."""
        # Arrange
        block = SimpleNamespace(type="text", text="I refuse.")
        client = make_fake_client([block])
        generator = ZoneGenerator(client=client)

        # Act / Assert
        with self.assertRaises(ZoneGenerationError):
            await generator.generate_zone_spec("a theme")

    async def test_generate_zone_spec_includes_hints_in_user_prompt(self):
        """Test theme, avoid_names and previous_errors reach the prompt."""
        # Arrange
        block = SimpleNamespace(type="tool_use", input={"zone_name": "x"})
        client = make_fake_client([block])
        generator = ZoneGenerator(client=client)

        # Act
        await generator.generate_zone_spec(
            "a theme of glass",
            avoid_names=["The Old Mill", "The Chapel"],
            previous_errors=["zone is not a single connected area"],
        )

        # Assert
        kwargs = client.messages.create.await_args.kwargs
        prompt = kwargs["messages"][0]["content"]
        self.assertIn("a theme of glass", prompt)
        self.assertIn("The Old Mill", prompt)
        self.assertIn("The Chapel", prompt)
        self.assertIn("zone is not a single connected area", prompt)


class LoadFallbackSpecTest(unittest.TestCase):
    """Test the hand-authored fallback zone loader."""

    def test_load_fallback_spec_returns_shipped_zone(self):
        """Test the shipped fallback file loads as a dict."""
        # Act
        spec = load_fallback_spec()

        # Assert
        self.assertIsInstance(spec, dict)
        self.assertIn("rooms", spec)
        self.assertIn("entry_room_id", spec)


if __name__ == "__main__":
    unittest.main()
