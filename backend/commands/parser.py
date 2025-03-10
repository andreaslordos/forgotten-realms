# backend/commands/parser.py (Updated)

# Re-export from unified_parser for backward compatibility
from commands.unified_parser import CommandContext, SyntaxPattern
from commands.parser_adapter import parse_command, is_movement_command

# Keep these for backward compatibility
DIRECTION_ALIASES = {
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "ne": "northeast",
    "nw": "northwest",
    "se": "southeast",
    "sw": "southwest",
    "u": "up",
    "d": "down",
    "out": "out",
    "in": "in",
}

COMMAND_ABBREVIATIONS = {
    "g": "get",
    "dr": "drop",
    "i": "inventory",
    "inv": "inventory",
    "l": "look",
    "sh": "shout",
    "k": "kill",
    "att": "attack",
    "ret": "retaliate",
    "fl": "flee",
    "x": "exits",
    "sc": "score",
    "u": "users",
    "h": "help",
    "qq": "quit",
}

# Backward compatibility functions
def parse_command_string(command_str, command_context=None, abbreviations=None, players_in_room=None, online_sessions=None):
    """Legacy function for backward compatibility."""
    return parse_command(command_str, command_context, players_in_room, online_sessions)

def parse_single_command(command_str, context, abbreviations, players_in_room=None):
    """Legacy function for backward compatibility."""
    parsed = parse_command(command_str, context, players_in_room)
    return parsed[0] if parsed else None

def parse_container_commands(command_str, context):
    """Legacy function for backward compatibility."""
    from commands.unified_parser import detect_container_commands
    cmd = {
        "original": command_str,
        "tokens": command_str.split(),
    }
    result = detect_container_commands(cmd, context, None)
    
    if result.get("abort_pipeline"):
        return result
    return None