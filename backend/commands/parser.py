# commands/parser.py

from typing import Dict, List, Any, Optional
from commands.natural_language_parser import parse_command, is_movement_command, natural_language_parser, vocabulary_manager
from commands.registry import command_registry
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Main entry point for parsing
def parse_command_wrapper(command_str: str, context=None, players_in_room=None, online_sessions=None):
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
    
    # Extract player and game_state from context if available
    player = None
    game_state = None
    
    if context and isinstance(context, dict):
        player = context.get('player')
        game_state = context.get('game_state')
    elif context and hasattr(context, 'get'):
        # Try to get player and game_state from context object
        player = getattr(context, 'get')('player', None)
        game_state = getattr(context, 'get')('game_state', None)
    
    # Try to extract player from players_in_room if needed
    if not player and players_in_room and len(players_in_room) > 0:
        for p in players_in_room:
            if hasattr(p, 'current_room'):
                player = p
                break
    
    # Create temporary player and game state if not provided
    if not player:
        from models.Player import Player
        player = Player("temp_player")
        logger.debug("Created temporary player for parsing")
    
    if not game_state:
        from managers.game_state import GameState
        game_state = GameState()
        logger.debug("Created temporary game state for parsing")
    
    # Special case for empty command
    if not command_str.strip():
        logger.debug("Empty command string, returning empty list")
        return []
    
    # Special case for quoted commands (say)
    if command_str.startswith('"'):
        logger.debug(f"Processing quoted command: '{command_str}'")
        cmd = {
            "verb": "say",
            "subject": command_str[1:].strip(),
            "original": command_str,
            "players_in_room": players_in_room,
            "online_sessions": online_sessions
        }
        return [cmd]
    
    # Parse the command
    commands = parse_command(command_str, player, game_state)
    logger.debug(f"Parser returned: {commands}")
    
    # Add additional context for backwards compatibility
    for cmd in commands:
        cmd['players_in_room'] = players_in_room
        cmd['online_sessions'] = online_sessions
        
        # Set is_movement flag if verb is a direction
        if 'verb' in cmd and is_movement_command(cmd['verb']):
            cmd['is_movement'] = True
    
    # Special case: if no commands were parsed but we have a valid text, create a default command
    if not commands and command_str.strip():
        logger.debug(f"Creating default command for unparsed input: '{command_str}'")
        parts = command_str.strip().split(maxsplit=1)
        verb = parts[0].lower()
        subject = parts[1] if len(parts) > 1 else None
        
        # Try to expand verb abbreviation
        expanded_verb = vocabulary_manager.expand_word(verb)
        
        cmd = {
            "verb": expanded_verb,
            "subject": subject,
            "original": command_str,
            "players_in_room": players_in_room,
            "online_sessions": online_sessions
        }
        
        # Check if it's a movement command
        if vocabulary_manager.is_direction(expanded_verb):
            cmd["is_movement"] = True
        
        commands = [cmd]
    
    logger.debug(f"Final commands after wrapping: {commands}")
    return commands