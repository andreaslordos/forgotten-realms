# backend/commands/parser_adapter.py

import logging
from commands.registry import command_registry
from commands.unified_parser import create_default_parser

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the default parser
default_parser = create_default_parser(command_registry)

def is_movement_command(verb):
    """Check if a verb is a movement command."""
    return verb in command_registry.direction_aliases.values() or verb in command_registry.direction_aliases

def parse_command(command_str, context=None, players_in_room=None, online_sessions=None):
    """
    Main entry point for command parsing.
    Returns a list of parsed command dictionaries.
    """
    logger.debug(f"Parsing command: {command_str}")
    
    # Use the new unified parser
    parsed_commands = default_parser.parse(command_str, context, players_in_room, online_sessions)
    
    # Add special flag for movement commands
    for cmd in parsed_commands:
        if cmd.get("verb") in command_registry.direction_aliases.values():
            cmd["is_movement"] = True
    
    logger.debug(f"Parsed result: {parsed_commands}")
    return parsed_commands