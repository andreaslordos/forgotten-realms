# commands/parser.py

from typing import Dict, List, Optional, Any
from commands.natural_language_parser import (
    parse_command,
    is_movement_command,
    natural_language_parser,
    vocabulary_manager,
)
import logging

# Explicitly declare exports for type checking
__all__ = [
    "parse_command_wrapper",
    "parse_command",
    "is_movement_command",
    "natural_language_parser",
    "vocabulary_manager",
]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Main entry point for parsing
def parse_command_wrapper(
    command_str: str,
    context: Optional[Dict[str, Any]] = None,
    players_in_room: Optional[List[Any]] = None,
    online_sessions: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Parse a command string into command objects.
    Wrapper around the natural language parser for compatibility.

    Args:
        command_str: The raw command string
        context: Optional context dictionary with player and game_state
        players_in_room: Optional list of players in the current room
        online_sessions: Optional dictionary of online sessions

    Returns:
        A list of parsed command objects
    """
    logger.debug(f"Parse command wrapper called with: '{command_str}'")

    # Extract player, game_state, and mob_manager from context if available
    player: Any = None
    game_state: Any = None
    mob_manager: Any = None

    if context and isinstance(context, dict):
        player = context.get("player")
        game_state = context.get("game_state")
        mob_manager = context.get("mob_manager")
    elif context and hasattr(context, "get"):
        # Try to get player and game_state from context object
        get_method: Any = getattr(context, "get")
        player = get_method("player", None)
        game_state = get_method("game_state", None)
        mob_manager = get_method("mob_manager", None)

    # Try to extract player from players_in_room if needed
    if not player and players_in_room and len(players_in_room) > 0:
        for p in players_in_room:
            if hasattr(p, "current_room"):
                player = p
                break

    # Special case for empty command
    if not command_str.strip():
        logger.debug("Empty command string, returning empty list")
        return []

    # Special case for quoted commands (say)
    if command_str.startswith('"'):
        logger.debug(f"Processing quoted command: '{command_str}'")
        message_quoted: str = command_str[1:].strip()
        cmd_quoted: Dict[str, Any] = {
            "verb": "say",
            "subject": message_quoted,  # Use exact message
            "original": command_str,
            "players_in_room": players_in_room,
            "online_sessions": online_sessions,
        }
        return [cmd_quoted]

    # Check if this might be a direct player message
    first_word: str = command_str.split()[0].lower() if command_str.strip() else ""
    is_player_message: bool = False

    if online_sessions:
        for session in online_sessions.values():
            temp_data: Dict[str, Any] = session.get("temp_data", {})
            username: Optional[str] = temp_data.get("username")
            if username:
                if username.lower() == first_word.lower():
                    is_player_message = True
                    player_obj: Any = session.get("player")
                    if player_obj:
                        logger.debug(
                            f"Detected direct message to player: {player_obj.name}"
                        )
                    break

    # Set the direct message flag based on player message detection
    is_direct_message: bool = is_player_message

    # If this is a direct player message, handle it immediately without expansion
    if is_direct_message:
        parts: List[str] = command_str.split(maxsplit=1)
        recipient: str = parts[0]
        message_direct: str = parts[1] if len(parts) > 1 else ""

        cmd_direct: Dict[str, Any] = {
            "verb": "tell",
            "subject": recipient,
            "instrument": message_direct,  # Use exact message text with no expansion
            "original": command_str,
            "players_in_room": players_in_room,
            "online_sessions": online_sessions,
            "is_direct_message": True,
        }
        logger.debug(f"Returning direct message command: {cmd_direct}")
        return [cmd_direct]

    # For regular commands, use the natural language parser
    # Set mob_manager if available
    if mob_manager:
        natural_language_parser.set_mob_manager(mob_manager)
    commands: List[Dict[str, Any]] = parse_command(command_str, player, game_state)
    logger.debug(f"Parser returned: {commands}")

    # Add additional context for backwards compatibility
    for cmd in commands:
        cmd["players_in_room"] = players_in_room
        cmd["online_sessions"] = online_sessions

        # Set is_movement flag if verb is a direction
        if "verb" in cmd:
            verb_value: Any = cmd["verb"]
            if isinstance(verb_value, str) and is_movement_command(verb_value):
                cmd["is_movement"] = True

    # Special case: if no commands were parsed but we have a valid text, create a default command
    if not commands and command_str.strip():
        logger.debug(f"Creating default command for unparsed input: '{command_str}'")
        parts_default: List[str] = command_str.strip().split(maxsplit=1)
        verb: str = parts_default[0].lower()
        subject: Optional[str] = parts_default[1] if len(parts_default) > 1 else None

        # Try to expand verb abbreviation
        expanded_verb: str = vocabulary_manager.expand_word(verb)

        cmd_default: Dict[str, Any] = {
            "verb": expanded_verb,
            "subject": subject,
            "original": command_str,
            "players_in_room": players_in_room,
            "online_sessions": online_sessions,
        }

        # Check if it's a movement command
        if vocabulary_manager.is_direction(expanded_verb):
            cmd_default["is_movement"] = True

        commands = [cmd_default]

    logger.debug(f"Final commands after wrapping: {commands}")
    return commands
