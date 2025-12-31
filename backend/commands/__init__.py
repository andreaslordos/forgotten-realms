# backend/commands/__init__.py

import logging

from commands import executor, natural_language_parser, parser, registry, utils
from commands.executor import build_look_description, execute_command
from commands.parser import parse_command_wrapper as parse_command
from commands.registry import command_registry
from globals import online_sessions

# Export public API
__all__ = [
    "parse_command",
    "command_registry",
    "execute_command",
    "build_look_description",
    "online_sessions",
    "registry",
    "parser",
    "executor",
    "utils",
    "natural_language_parser",
    "standard",
    "communication",
    "combat",
    "container",
    "interaction",
    "auth",
    "archmage",
    "rest",
    "player_interaction",
    "magic",
    "pathfinding",
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.info("Initializing commands package")

# Initialize vocabularies
logger.info("Initializing vocabulary manager")

# Add all verbs from the command registry to the vocabulary
for verb in command_registry.commands.keys():
    natural_language_parser.vocabulary_manager.add_verb(verb)
    logger.info(f"Added verb to vocabulary: {verb}")

# Add common directions
directions = [
    "north",
    "south",
    "east",
    "west",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "up",
    "down",
    "in",
    "out",
]
for direction in directions:
    natural_language_parser.vocabulary_manager.add_direction(direction)
    logger.info(f"Added direction to vocabulary: {direction}")

# Make sure standard verbs are added
common_verbs = [
    "look",
    "get",
    "take",
    "drop",
    "inventory",
    "help",
    "quit",
    "say",
    "tell",
    "shout",
    "attack",
    "steal",
    "give",
]
for verb in common_verbs:
    natural_language_parser.vocabulary_manager.add_verb(verb)

# Context-aware abbreviations
# Register "w" as an abbreviation that expands differently based on context
natural_language_parser.vocabulary_manager.add_abbreviation(
    "w", "with", "in_prep_position"
)
natural_language_parser.vocabulary_manager.add_abbreviation("w", "west", "default")

# Import command handlers (for side effects - they register commands)
try:
    from commands import (
        archmage,
        auth,
        combat,
        communication,
        container,
        interaction,
        magic,
        pathfinding,
        player_interaction,
        rest,
        standard,
    )

    logger.info("All command handlers imported successfully")

    # Register cross-module aliases (after all commands are registered)
    command_registry.register_alias("remove", "get")
    logger.info("Registered cross-module alias: 'remove' → 'get'")

except ImportError as e:
    logger.error(f"Error importing command handlers: {e}")

# Initialize the parser's command registry reference
natural_language_parser.natural_language_parser.command_registry = command_registry

logger.info("Commands package initialization complete")
