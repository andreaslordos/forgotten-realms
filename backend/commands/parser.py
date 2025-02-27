# backend/commands/parser.py

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommandContext:
    """
    Stores the context of previously executed commands.
    This allows for command chaining and using pronouns like IT, HIM, HER, THEM.
    """
    def __init__(self):
        self.last_verb = None
        self.last_subject = None
        self.last_object = None
        self.last_instrument = None
        self.last_player = None  # Last player referenced (for THEM)
        self.last_male = None    # Last male referenced (for HIM)
        self.last_female = None  # Last female referenced (for HER)
        self.last_it = None      # Last non-player referenced (for IT)

    def update(self, verb, subject=None, obj=None, instrument=None, player=None, gender=None):
        """Updates the command context with new values."""
        logger.debug(f"Updating context: verb={verb}, subject={subject}, obj={obj}, instrument={instrument}")
        if verb:
            self.last_verb = verb
        if subject:
            self.last_subject = subject
            if player:
                if gender == 'M':
                    self.last_male = subject
                elif gender == 'F':
                    self.last_female = subject
                self.last_player = subject
            else:
                self.last_it = subject
        if obj:
            self.last_object = obj
        if instrument:
            self.last_instrument = instrument

    def resolve_pronoun(self, word, players_in_room=None):
        """
        Resolves pronouns like IT, HIM, HER, THEM to their actual referents.
        
        Args:
            word (str): The word to check if it's a pronoun
            players_in_room (list): Optional list of players in the room
            
        Returns:
            str: The resolved referent or the original word if not a pronoun
        """
        if not word:
            return word
            
        word_lower = word.lower()
        
        if word_lower == "it":
            return self.last_it or word
        elif word_lower == "him":
            return self.last_male or word
        elif word_lower == "her":
            return self.last_female or word
        elif word_lower == "them":
            return self.last_player or word
        
        return word


def parse_command_string(command_str, command_context=None, abbreviations=None, players_in_room=None, online_sessions=None):
    """
    Parses a command string using the format: <verb> <subject> WITH <object>.
    Handles conjunctions, pronouns, and command chaining.
    
    Args:
        command_str (str): The command string to parse
        command_context (CommandContext): Optional context from previous commands
        abbreviations (dict): Optional mapping of abbreviations to full commands
        players_in_room (list): Optional list of players in the room
        online_sessions (dict): Optional dictionary of all online sessions
        
    Returns:
        list: A list of parsed command dictionaries
    """
    logger.debug(f"Parsing command string: '{command_str}'")
    
    if not command_str:
        return []
    
    if not command_context:
        command_context = CommandContext()
    
    if not abbreviations:
        abbreviations = {}
    
    # Normalize the command string
    command_str = command_str.strip().lower()
    
    # Handle quote-prefixed say commands
    if command_str.startswith('"'):
        # Remove the quote and treat as a say command
        return [{"verb": "say", "subject": command_str[1:].strip(), "object": None, "instrument": None, "original": command_str}]
    
    # Check if command starts with a player name (for tell command)
    # This needs to check all online players, not just those in the room
    if len(command_str.split()) > 1:
        first_word = command_str.split()[0]
        message = " ".join(command_str.split()[1:])
        
        # First check online_sessions if provided (this includes all players)
        if online_sessions:
            all_players = [session.get('player') for session in online_sessions.values() 
                          if session.get('player') is not None]
            
            for player in all_players:
                if player.name.lower() == first_word.lower():
                    # Convert to a tell command
                    return [{"verb": "tell", "subject": player.name, "object": None, "instrument": message, "original": command_str}]
        
        # Then check players_in_room as a fallback
        elif players_in_room:
            for player in players_in_room:
                if player.name.lower() == first_word.lower():
                    # Convert to a tell command
                    return [{"verb": "tell", "subject": player.name, "object": None, "instrument": message, "original": command_str}]
    
    # Split on conjunctions (and, then, comma, period)
    conjunctions = [" and ", " then ", ",", "."]
    command_parts = [command_str]
    for conj in conjunctions:
        new_parts = []
        for part in command_parts:
            new_parts.extend(part.split(conj))
        command_parts = new_parts
    
    logger.debug(f"Command parts after splitting: {command_parts}")
    
    # Process each command part
    parsed_commands = []
    for part in command_parts:
        part = part.strip()
        if not part:
            continue
        
        # Parse the command into components
        command_dict = parse_single_command(part, command_context, abbreviations, players_in_room)
        if command_dict:
            parsed_commands.append(command_dict)
    
    logger.debug(f"Parsed commands: {parsed_commands}")
    return parsed_commands


def parse_single_command(command_str, context, abbreviations, players_in_room=None):
    """
    Parses a single command using the format: <verb> <subject> WITH <object>
    
    Args:
        command_str (str): The command string to parse
        context (CommandContext): The command context
        abbreviations (dict): Mapping of abbreviations to full commands
        players_in_room (list): Optional list of players in the room
        
    Returns:
        dict: A dictionary with the parsed command components
    """
    logger.debug(f"Parsing single command: '{command_str}'")
    
    tokens = command_str.split()
    if not tokens:
        logger.debug("No tokens found, returning None")
        return None
    
    # Check if we have a verb
    verb = tokens[0]
    
    # Try to expand abbreviation
    full_verb = abbreviations.get(verb, verb)
    logger.debug(f"Verb: {verb}, expanded to: {full_verb}")
    
    # Create the result dictionary
    result = {
        "verb": full_verb,
        "subject": None,
        "object": None,
        "instrument": None,
        "original": command_str
    }
    
    # Process the remaining tokens
    remaining_tokens = tokens[1:]
    logger.debug(f"Remaining tokens: {remaining_tokens}")
    
    # Special case for pronouns in communication commands
    if len(remaining_tokens) >= 2 and remaining_tokens[0] in ["him", "her", "them", "it"]:
        if full_verb in ["tell", "ask", "whisper"]:
            pronoun = remaining_tokens[0]
            message = " ".join(remaining_tokens[1:])
            
            # Resolve the pronoun
            if pronoun == "him" and context.last_male:
                result["subject"] = context.last_male
            elif pronoun == "her" and context.last_female:
                result["subject"] = context.last_female
            elif pronoun == "them" and context.last_player:
                result["subject"] = context.last_player
            elif pronoun == "it" and context.last_it:
                result["subject"] = context.last_it
            else:
                result["subject"] = pronoun
                
            result["instrument"] = message
            context.update(full_verb, result["subject"], None, result["instrument"])
            return result
    
    # Look for "with" or equivalent to split subject and instrument
    with_index = -1
    with_equivalents = ["with", "wi", "using", "by", "via", "at", "to", "from"]
    
    for i, token in enumerate(remaining_tokens):
        if token.lower() in with_equivalents:
            with_index = i
            break
    
    logger.debug(f"'With' token found at index: {with_index}")
    
    # Extract subject (before "with") and instrument (after "with")
    if with_index >= 0:
        subject_part = " ".join(remaining_tokens[:with_index]) if with_index > 0 else None
        instrument_part = " ".join(remaining_tokens[with_index+1:]) if with_index < len(remaining_tokens) - 1 else None
        
        logger.debug(f"Subject part: '{subject_part}', Instrument part: '{instrument_part}'")
        
        # Resolve pronouns
        if subject_part == "him" and context.last_male:
            result["subject"] = context.last_male
        elif subject_part == "her" and context.last_female:
            result["subject"] = context.last_female
        elif subject_part == "it" and context.last_it:
            result["subject"] = context.last_it
        elif subject_part == "them" and context.last_player:
            result["subject"] = context.last_player
        else:
            result["subject"] = subject_part
            
        if instrument_part == "him" and context.last_male:
            result["instrument"] = context.last_male
        elif instrument_part == "her" and context.last_female:
            result["instrument"] = context.last_female
        elif instrument_part == "it" and context.last_it:
            result["instrument"] = context.last_it
        elif instrument_part == "them" and context.last_player:
            result["instrument"] = context.last_player
        else:
            result["instrument"] = instrument_part
    elif remaining_tokens:
        # No "with" found, treat everything as subject
        subject_part = " ".join(remaining_tokens)
        
        # Handle pronoun resolution
        if subject_part == "him" and context.last_male:
            result["subject"] = context.last_male
        elif subject_part == "her" and context.last_female:
            result["subject"] = context.last_female
        elif subject_part == "it" and context.last_it:
            result["subject"] = context.last_it
        elif subject_part == "them" and context.last_player:
            result["subject"] = context.last_player
        else:
            result["subject"] = subject_part
    
    logger.debug(f"Final result: {result}")
    
    # Update the context with this command
    context.update(full_verb, result["subject"], None, result["instrument"])
    
    return result


# Mapping of direction abbreviations to full directions
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
    # Removed "i": "in" as requested
    # Removed "o": "out" as requested
}

# Command abbreviations
COMMAND_ABBREVIATIONS = {
    "g": "get",
    "dr": "drop",
    "i": "inventory",  # Now this is unambiguous since "i" was removed from DIRECTION_ALIASES
    "inv": "inventory",
    "l": "look",
    "sh": "shout",
    "k": "kill",
    "att": "attack",
    "ret": "retaliate",
    "fl": "flee",
    "x": "exits",
    "sc": "score",
    "u": "users",  # Note: this conflicts with DIRECTION_ALIASES["u"]
    "h": "help",
    "qq": "quit",  # Changed from "q" to "qq" as requested
}

def is_movement_command(verb):
    """Check if a verb is a movement command."""
    return verb in DIRECTION_ALIASES.values() or verb in DIRECTION_ALIASES.keys()

def parse_command(command_str, context=None, players_in_room=None, online_sessions=None):
    """
    Main entry point for command parsing.
    
    Args:
        command_str (str): The command string to parse
        context (CommandContext): Optional context from previous commands
        players_in_room (list): Optional list of players in the current room
        online_sessions (dict): Optional dictionary of all online sessions
        
    Returns:
        list: A list of parsed command dictionaries
    """
    logger.debug(f"Main parse_command called with: '{command_str}'")
    
    if not command_str:
        return []
    
    if not context:
        context = CommandContext()
    
    # Initialize commands list to avoid reference error
    commands = []

    # Handle commands starting with quote (say command)
    if command_str.startswith('"'):
        # Create a say command explicitly
        say_text = command_str[1:].strip()
        commands = [{"verb": "say", "subject": say_text, "object": None, "instrument": None, "original": command_str}]
    # First check if it's a single-letter command that could be ambiguous
    elif command_str == "u":
        # For "u", we prioritize the direction "up" for consistency
        all_abbreviations = {"u": "up"}
        commands = parse_command_string(command_str, context, all_abbreviations, players_in_room, online_sessions)
    elif command_str in DIRECTION_ALIASES:
        # For other direction aliases, prioritize them
        all_abbreviations = {command_str: DIRECTION_ALIASES[command_str]}
        commands = parse_command_string(command_str, context, all_abbreviations, players_in_room, online_sessions)
    else:
        # For all other commands, combine abbreviations with command abbreviations taking precedence
        all_abbreviations = {**DIRECTION_ALIASES, **COMMAND_ABBREVIATIONS}
        commands = parse_command_string(command_str, context, all_abbreviations, players_in_room, online_sessions)
    
    # Special handling for movement commands (go north, north, n, etc.)
    for cmd in commands:
        # If the verb is "go", change it to the direction
        if cmd["verb"] == "go" and cmd["subject"] in DIRECTION_ALIASES.values():
            cmd["verb"] = cmd["subject"]
            cmd["subject"] = None
        
        # If the verb is a direction alias, expand it
        if cmd["verb"] in DIRECTION_ALIASES:
            cmd["verb"] = DIRECTION_ALIASES[cmd["verb"]]
    
    logger.debug(f"Final parsed commands: {commands}")
    return commands