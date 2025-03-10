# backend/commands/parser.py

# Simply re-export key elements from unified_parser
from commands.unified_parser import (
    CommandContext, 
    SyntaxPattern,
    create_default_parser,
    CommandParser
)

# Create a reference to the default parser for direct use
from commands.unified_parser import default_parser

# Export the main parse function directly
def parse_command(command_str, context=None, players_in_room=None, online_sessions=None):
    """Parse a command string into command objects."""
    return default_parser.parse(command_str, context, players_in_room, online_sessions)

# Re-export movement detection
from commands.unified_parser import is_movement_command