# backend/commands/parser.py

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add these at the top of parser.py with the other constants

# Prepositions that indicate reversed syntax (verb X to/on/in Y)
REVERSED_PREPOSITIONS = {
    "to": "to", "t": "to", "onto": "onto", "toward": "toward", "towards": "towards",
    "on": "on", "upon": "upon", "over": "over",
    "in": "in", "i": "in", "into": "into", "inside": "inside", 
    "at": "at", "around": "around", "about": "about"
}

# Prepositions that indicate standard syntax (verb X with/using Y)
STANDARD_PREPOSITIONS = {
    "with": "with", "w": "with", "wi": "with", 
    "using": "using", "u": "using",
    "by": "by", "via": "via", "through": "through", 
    "underneath": "underneath", "beneath": "beneath", "under": "under"
}

def is_reversed_preposition(word):
    """Check if a word is a preposition indicating reversed syntax."""
    return word.lower() in REVERSED_PREPOSITIONS

def is_standard_preposition(word):
    """Check if a word is a preposition indicating standard syntax."""
    return word.lower() in STANDARD_PREPOSITIONS

def get_full_preposition(word):
    """Get the full form of an abbreviated preposition."""
    word_lower = word.lower()
    if word_lower in REVERSED_PREPOSITIONS:
        return REVERSED_PREPOSITIONS[word_lower]
    if word_lower in STANDARD_PREPOSITIONS:
        return STANDARD_PREPOSITIONS[word_lower]
    return word_lower

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
    Parses a command string into a single command dictionary.
    (Any splitting on chaining tokens is now handled later in the tick service.)
    
    Args:
        command_str (str): The command string to parse.
        command_context (CommandContext): Optional context from previous commands.
        abbreviations (dict): Optional mapping of abbreviations to full commands.
        players_in_room (list): Optional list of players in the room.
        online_sessions (dict): Optional dictionary of all online sessions.
        
    Returns:
        list: A list with a single parsed command dictionary.
    """
    logger.debug(f"Parsing command string: '{command_str}'")
    
    if not command_str:
        return []
    
    if not command_context:
        command_context = CommandContext()
    
    if not abbreviations:
        abbreviations = {}
    
    # Normalize the command string (but do not split by punctuation here)
    command_str = command_str.strip().lower()
    
    # Handle quote-prefixed say commands (these are message commands that must remain intact)
    if command_str.startswith('"'):
        return [{
            "verb": "say",
            "subject": command_str[1:].strip(),
            "object": None,
            "instrument": None,
            "original": command_str
        }]
    
    # Check if the command starts with a player's name (for tell commands)
    if len(command_str.split()) > 1:
        first_word = command_str.split()[0]
        message = " ".join(command_str.split()[1:])
        
        if online_sessions:
            all_players = [session.get('player') for session in online_sessions.values() if session.get('player') is not None]
            for player in all_players:
                if player.name.lower() == first_word:
                    return [{
                        "verb": "tell",
                        "subject": player.name,
                        "object": None,
                        "instrument": message,
                        "original": command_str
                    }]
        elif players_in_room:
            for player in players_in_room:
                if player.name.lower() == first_word:
                    return [{
                        "verb": "tell",
                        "subject": player.name,
                        "object": None,
                        "instrument": message,
                        "original": command_str
                    }]
    
    # For all other commands, simply parse the entire string as one command.
    # Combine any needed abbreviation mappings.
    all_abbreviations = {**DIRECTION_ALIASES, **COMMAND_ABBREVIATIONS}
    cmd_dict = parse_single_command(command_str, command_context, all_abbreviations, players_in_room)
    return [cmd_dict]


# Updated parse_container_commands function for commands/parser.py

def parse_container_commands(command_str, context):
    """
    Parse special container commands like "put/insert X in Y" or "get/take/remove X from Y".
    Supports abbreviations like 'g' for 'get' and 'fr' for 'from'.
    
    Args:
        command_str (str): The command string to parse
        context (CommandContext): Command context for pronouns
        
    Returns:
        dict or None: The parsed command or None if not a container command
    """
    # Normalize command_str (apply common abbreviations)
    normalized_cmd = command_str.lower()
    
    # Apply abbreviations at the start of the command
    if normalized_cmd.startswith("g "):
        normalized_cmd = "get " + normalized_cmd[2:]
    elif normalized_cmd.startswith("t "):
        normalized_cmd = "take " + normalized_cmd[2:]
    
    # Handle "fr" as abbreviation for "from"
    normalized_cmd = normalized_cmd.replace(" fr ", " from ")
    
    # Check for "put/insert X in Y" pattern
    put_matches = ["put ", "insert "]
    for prefix in put_matches:
        if normalized_cmd.startswith(prefix):
            # Split by " in " without the maxsplit parameter
            parts = normalized_cmd.split(" in ")
            if len(parts) == 2:
                item_name = parts[0][len(prefix):].strip()  # Remove prefix
                container_name = parts[1].strip()
                
                # Resolve pronouns
                item_name = context.resolve_pronoun(item_name)
                container_name = context.resolve_pronoun(container_name)
                
                return {
                    "verb": "put",  # Always use "put" as the verb
                    "subject": item_name,
                    "object": None,
                    "instrument": container_name,
                    "original": command_str
                }
    
    # Check for "get/take/remove X from Y" pattern
    get_matches = ["get ", "take ", "remove "]
    for prefix in get_matches:
        if normalized_cmd.startswith(prefix):
            # Split by " from " without the maxsplit parameter
            parts = normalized_cmd.split(" from ")
            if len(parts) == 2:
                item_name = parts[0][len(prefix):].strip()  # Remove prefix
                container_name = parts[1].strip()
                
                # Resolve pronouns
                item_name = context.resolve_pronoun(item_name)
                container_name = context.resolve_pronoun(container_name)
                
                # Use "get" as the standard verb with a container flag
                return {
                    "verb": "get",  # Always use "get" as the verb
                    "subject": item_name,
                    "object": None,
                    "instrument": container_name,
                    "original": command_str,
                    "from_container": True  # Special flag to indicate this is a container retrieval
                }
    
    return None

# Modified parse_command function to include container command parsing
# Modified parse_command function to include container command parsing and use our new syntax
def parse_command(command_str, context=None, players_in_room=None, online_sessions=None):
    """
    Main entry point for command parsing.
    Returns a list containing a single parsed command dictionary.
    
    This version has been updated to include container command parsing
    and support for reversed syntax (tie rope to well).
    """
    if not command_str:
        return []
    
    if not context:
        context = CommandContext()
    
    # Check for special container commands first
    container_cmd = parse_container_commands(command_str, context)
    if container_cmd:
        context.update(container_cmd["verb"], container_cmd["subject"], None, container_cmd["instrument"])
        return [container_cmd]
    
    # Original logic for say commands (starting with a quote)
    if command_str.startswith('"'):
        return [{
            "verb": "say",
            "subject": command_str[1:].strip(),
            "object": None,
            "instrument": None,
            "original": command_str
        }]
    
    # Original logic for abbreviations
    if command_str == "u":
        all_abbreviations = {"u": "up"}
    elif command_str in DIRECTION_ALIASES:
        all_abbreviations = {command_str: DIRECTION_ALIASES[command_str]}
    else:
        all_abbreviations = {**DIRECTION_ALIASES, **COMMAND_ABBREVIATIONS}
    
    # Parse the command string using the enhanced parser
    cmds = parse_command_string(command_str, context, all_abbreviations, players_in_room, online_sessions)
    
    # Special handling: if the verb is a direction, expand it.
    for cmd in cmds:
        if cmd["verb"] == "go" and cmd["subject"] in DIRECTION_ALIASES.values():
            cmd["verb"] = cmd["subject"]
            cmd["subject"] = None
        if cmd["verb"] in DIRECTION_ALIASES:
            cmd["verb"] = DIRECTION_ALIASES[cmd["verb"]]
    
    return cmds

def parse_single_command(command_str, context, abbreviations, players_in_room=None):
    """
    Parses a single command supporting both:
    - <verb> <subject> with <instrument> format
    - <verb> <instrument> to/on/in <subject> format
    
    Args:
        command_str (str): The command string to parse.
        context (CommandContext): The command context.
        abbreviations (dict): Mapping of abbreviations to full commands.
        players_in_room (list): Optional list of players in the room.
        
    Returns:
        dict: A dictionary with the parsed command components.
    """
    logger.debug(f"Parsing single command: '{command_str}'")
    
    tokens = command_str.split()
    if not tokens:
        logger.debug("No tokens found, returning None")
        return None
    
    # The first token is the verb
    verb = tokens[0]
    full_verb = abbreviations.get(verb, verb)
    logger.debug(f"Verb: {verb}, expanded to: {full_verb}")
    
    result = {
        "verb": full_verb,
        "subject": None,
        "object": None,
        "instrument": None,
        "preposition": "with",  # Default preposition
        "reversed_syntax": False,  # Flag for reversed syntax
        "original": command_str
    }
    
    remaining_tokens = tokens[1:]
    logger.debug(f"Remaining tokens: {remaining_tokens}")
    
    # Look for reversed prepositions (to, on, in, etc.)
    reversed_index = -1
    for i, token in enumerate(remaining_tokens):
        if is_reversed_preposition(token):
            reversed_index = i
            result["preposition"] = get_full_preposition(token)
            break
    
    # Look for standard prepositions (with, using, by, etc.)
    standard_index = -1
    for i, token in enumerate(remaining_tokens):
        if is_standard_preposition(token):
            standard_index = i
            result["preposition"] = get_full_preposition(token)
            break
    
    # Determine if we're using reversed syntax
    if reversed_index >= 0 and (standard_index < 0 or reversed_index < standard_index):
        # Using reversed syntax (e.g., "tie rope to well")
        instrument_part = " ".join(remaining_tokens[:reversed_index]) if reversed_index > 0 else None
        subject_part = " ".join(remaining_tokens[reversed_index+1:]) if reversed_index < len(remaining_tokens) - 1 else None
        result["reversed_syntax"] = True
    elif standard_index >= 0:
        # Using standard syntax (e.g., "open door with key")
        subject_part = " ".join(remaining_tokens[:standard_index]) if standard_index > 0 else None
        instrument_part = " ".join(remaining_tokens[standard_index+1:]) if standard_index < len(remaining_tokens) - 1 else None
    else:
        # No preposition, just a subject
        subject_part = " ".join(remaining_tokens) if remaining_tokens else None
        instrument_part = None
    
    # Process pronoun substitutions for subject
    if subject_part in ["him", "her", "it", "them"]:
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
    else:
        result["subject"] = subject_part
    
    # Process pronoun substitutions for instrument
    if instrument_part in ["him", "her", "it", "them"]:
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
    else:
        result["instrument"] = instrument_part
    
    logger.debug(f"Final result: {result}")
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
    "out": "out",
    "in": "in",
}

# Command abbreviations
COMMAND_ABBREVIATIONS = {
    "g": "get",
    "dr": "drop",
    "i": "inventory",  # Now unambiguous since "i" was removed from DIRECTION_ALIASES
    "inv": "inventory",
    "l": "look",
    "sh": "shout",
    "k": "kill",
    "att": "attack",
    "ret": "retaliate",
    "fl": "flee",
    "x": "exits",
    "sc": "score",
    "u": "users",  # Note: conflicts with DIRECTION_ALIASES["u"]
    "h": "help",
    "qq": "quit",  # Changed from "q" to "qq" as requested
}

def is_movement_command(verb):
    """Check if a verb is a movement command."""
    return verb in DIRECTION_ALIASES.values() or verb in DIRECTION_ALIASES.keys()