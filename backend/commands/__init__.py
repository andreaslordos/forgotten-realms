# backend/commands/__init__.py

from globals import online_sessions

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Initializing commands package")

# Import core modules first
from commands import registry
from commands import natural_language_parser

# Import remaining modules
from commands import parser
from commands import executor
from commands import utils

# Export the main functions and objects for easy access
from commands.parser import parse_command_wrapper as parse_command
from commands.registry import command_registry
from commands.executor import execute_command, build_look_description

# Initialize vocabularies
logger.info("Initializing vocabulary manager")

# Add all verbs from the command registry to the vocabulary
for verb in command_registry.commands.keys():
    natural_language_parser.vocabulary_manager.add_verb(verb)
    logger.info(f"Added verb to vocabulary: {verb}")

# Add common directions
directions = ["north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest", "up", "down", "in", "out"]
for direction in directions:
    natural_language_parser.vocabulary_manager.add_direction(direction)
    logger.info(f"Added direction to vocabulary: {direction}")

# Make sure standard verbs are added
common_verbs = ["look", "get", "take", "drop", "inventory", "help", "quit", "say", "tell", "shout", "attack", "steal", "give"]
for verb in common_verbs:
    natural_language_parser.vocabulary_manager.add_verb(verb)

# Context-aware abbreviations
# Register "w" as an abbreviation that expands differently based on context
natural_language_parser.vocabulary_manager.add_abbreviation("w", "with", "in_prep_position")
natural_language_parser.vocabulary_manager.add_abbreviation("w", "west", "default")

# Import command handlers
try:
    from commands import standard
    from commands import communication
    from commands import combat
    from commands import container
    from commands import interaction
    from commands import auth
    from commands import archmage
    from commands import rest
    from commands import player_interaction
    logger.info("All command handlers imported successfully")

except ImportError as e:
    logger.error(f"Error importing command handlers: {e}")

# Initialize the parser's command registry reference
natural_language_parser.natural_language_parser.command_registry = command_registry

logger.info("Commands package initialization complete")