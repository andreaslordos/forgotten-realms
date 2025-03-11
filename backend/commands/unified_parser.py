# backend/commands/unified_parser.py
"""
Unified Command Parser System

This module implements a flexible, extensible command parsing system for text-based games.
It uses a middleware pipeline architecture to process commands through a series of steps,
allowing for gradual transformation from raw text input to structured command objects.

Key features:
- Middleware pipeline for command processing
- Support for various command syntaxes (standard, reversed, container commands)
- Command chaining via comma separation
- Context tracking for pronoun resolution
- Pattern-based command matching

Architecture Overview:
1. Raw input → CommandParser.parse()
2. Command chaining detection/splitting
3. Tokenization
4. Processing through middleware pipeline:
   - Message command detection (say, tell)
   - Abbreviation resolution
   - Container command detection
   - Interaction syntax detection
   - Pronoun resolution
5. Final command object creation

Author: AI MUD Development Team
"""

import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyntaxPattern:
    """
    Defines a command syntax pattern that can be matched against input.
    
    This class allows defining formal syntax structures for commands using a simple
    pattern language. Variables are represented by uppercase words (VERB, SUBJECT, INSTRUMENT),
    while literals are represented by lowercase words.
    
    Example patterns:
    - "VERB SUBJECT" - Simple command like "look sword"
    - "VERB SUBJECT with INSTRUMENT" - Standard syntax like "unlock door with key"
    - "VERB INSTRUMENT to SUBJECT" - Reversed syntax like "tie rope to tree"
    
    Patterns have a priority value to resolve ambiguities. Higher priority patterns
    are matched first when multiple patterns could apply.
    """
    def __init__(self, pattern_str, priority=0, handler=None):
        # The raw pattern string (e.g., "VERB SUBJECT with INSTRUMENT")
        self.pattern_str = pattern_str  
        # Higher priority patterns take precedence if multiple patterns match
        self.priority = priority
        # Optional custom handler function for specialized parsing
        self.handler = handler
        # Parsed representation of the pattern components
        self.components = self._parse_pattern()
    
    def _parse_pattern(self):
        """
        Convert the pattern string to a structured representation for matching.
        
        This breaks the pattern into components, distinguishing between:
        - Variables (UPPERCASE words) - representing command parts like VERB, SUBJECT
        - Literals (lowercase words) - representing specific words like "with", "to"
        
        Returns:
            list: A list of component dictionaries, each with either a "type" key 
                 (for variables) or a "value" key (for literals)
        """
        parts = self.pattern_str.split()
        components = []
        
        for part in parts:
            if part.isupper():  # Variable component like VERB, SUBJECT
                components.append({"type": part})
            else:  # Literal component like "with", "to", "from"
                components.append({"value": part.lower()})
        
        return components
    
    def matches(self, tokens):
        """
        Check if a sequence of tokens matches this pattern and extract the components.
        
        This implements a simple state machine that walks through the pattern and
        tokens in parallel, binding variable components to spans of tokens.
        
        Args:
            tokens (list): List of token strings from the input command
            
        Returns:
            tuple: (success, components_dict) where:
                - success (bool): True if pattern matched, False otherwise
                - components_dict (dict): Extracted components (verb, subject, instrument)
        """
        if not tokens:
            return False, {}
        
        # Simple state machine to match tokens against pattern
        components_dict = {}
        pattern_index = 0
        token_index = 0
        
        while pattern_index < len(self.components) and token_index < len(tokens):
            component = self.components[pattern_index]
            
            if "value" in component:
                # Literal matching - must match exact word
                if token_index < len(tokens) and tokens[token_index].lower() == component["value"]:
                    token_index += 1
                    pattern_index += 1
                else:
                    # Failed to match literal
                    return False, {}
            elif "type" in component:
                # Variable component matching - captures spans of tokens
                component_type = component["type"]
                
                if component_type == "VERB":
                    # Verb should be a single token
                    components_dict["verb"] = tokens[token_index]
                    token_index += 1
                    pattern_index += 1
                elif component_type == "SUBJECT":
                    # Subject can span multiple tokens until next component
                    start_idx = token_index
                    end_idx = start_idx
                    
                    # Consume tokens until next pattern component or end
                    while (pattern_index + 1 < len(self.components) and 
                           token_index < len(tokens) and 
                           (not "value" in self.components[pattern_index + 1] or 
                            tokens[token_index].lower() != self.components[pattern_index + 1]["value"])):
                        end_idx += 1
                        token_index += 1
                        if token_index >= len(tokens):
                            break
                    
                    if start_idx < end_idx:
                        components_dict["subject"] = " ".join(tokens[start_idx:end_idx])
                    else:
                        components_dict["subject"] = None
                    
                    pattern_index += 1
                elif component_type == "INSTRUMENT":
                    # Instrument can span to the end
                    if token_index < len(tokens):
                        components_dict["instrument"] = " ".join(tokens[token_index:])
                        token_index = len(tokens)  # Consume all remaining tokens
                    else:
                        components_dict["instrument"] = None
                    
                    pattern_index += 1
                else:
                    # Unknown component type
                    return False, {}
            else:
                # Malformed component
                return False, {}
        
        # Check if we successfully processed the entire pattern
        if pattern_index >= len(self.components):
            # Add preposition information if present
            for i, component in enumerate(self.components):
                if "value" in component:
                    if component["value"] in STANDARD_PREPOSITIONS:
                        components_dict["preposition"] = component["value"]
                        components_dict["reversed_syntax"] = False
                    elif component["value"] in REVERSED_PREPOSITIONS:
                        components_dict["preposition"] = component["value"]
                        components_dict["reversed_syntax"] = True
            
            return True, components_dict
        
        return False, {}


class CommandContext:
    """
    Stores the context of previously executed commands for reference resolution.
    
    This class maintains a history of command elements (verbs, subjects, objects)
    that enables the resolution of pronouns like IT, HIM, HER, THEM to their 
    actual referents. This allows for more natural command sequences like:
    
    > look at sword
    > take it
    
    Where "it" refers back to "sword" from the previous command.
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

    def update(self, verb=None, subject=None, obj=None, instrument=None, player=None, gender=None):
        """
        Updates the command context with new values from the current command.
        
        This method is called after each command is processed to update the
        context for future pronoun resolution.
        
        Args:
            verb (str): The main command verb
            subject (str): The primary noun/target of the command
            obj (str): The secondary object (rarely used)
            instrument (str): The tool or item used with the command
            player (object): Player object if subject refers to a player
            gender (str): Gender of referenced player ('M' or 'F')
        """
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
        
        This looks up the appropriate referent from the command history
        and substitutes it for the pronoun.
        
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


class CommandParser:
    """
    Main parser class that implements the middleware pipeline architecture.
    
    The CommandParser handles the overall flow of command processing:
    1. Tokenization of input
    2. Command chaining detection and processing
    3. Running the command through the middleware pipeline
    4. Finalizing the command object
    
    The parser is designed to be extensible through middleware functions that
    can be added to the pipeline to handle specific command types or transformations.
    """
    def __init__(self, command_registry):
        # Reference to the command registry for command validation and alias resolution
        self.registry = command_registry
        # List of middleware functions for the processing pipeline
        self.middleware = []
    
    def add_middleware(self, func):
        """
        Add a processing step to the parser pipeline.
        
        Middleware functions are called in sequence, each receiving the command
        object and context, and returning a potentially modified command object.
        
        Args:
            func (callable): Function with signature (cmd, context, registry) -> cmd
        """
        self.middleware.append(func)
    
    def parse(self, command_str, context=None, players_in_room=None, online_sessions=None):
        """
        Parse a command string into structured command objects.
        
        This is the main entry point for command parsing. It handles:
        - Command chaining (comma-separated commands)
        - Tokenization
        - Running the command through the middleware pipeline
        
        Args:
            command_str (str): The raw command string from the user
            context (CommandContext): Optional context from previous commands
            players_in_room (list): Optional list of players in the room
            online_sessions (dict): Optional online session data
            
        Returns:
            list: A list of parsed command objects (dictionaries)
        """
        if not context:
            context = CommandContext()
        
        # Step 1: Check for chained commands first (comma-separated)
        chained_commands = self._detect_chained_commands(command_str)
        if len(chained_commands) > 1:
            # Process each command separately and combine results
            results = []
            for cmd in chained_commands:
                # Recursively parse each part
                parsed = self.parse(cmd, context, players_in_room, online_sessions)
                results.extend(parsed)
            return results
        
        # Not a chained command, process normally
        # Initialize command object with original text and tokenize
        cmd = {
            "original": command_str,
            "tokens": self._tokenize(command_str),
            "verb": None,
            "subject": None,
            "instrument": None,
            "preposition": None,
            "players_in_room": players_in_room,
            "online_sessions": online_sessions
        }
        
        # Run command through middleware pipeline
        for middleware_func in self.middleware:
            cmd = middleware_func(cmd, context, self.registry)
            # If a middleware function sets abort_pipeline, stop processing
            if cmd.get("abort_pipeline"):
                break
        
        return [self._finalize_command(cmd, context)]
    
    def _tokenize(self, command_str):
        """
        Split command into tokens, preserving quoted strings.
        
        This tokenizer handles quoted strings as single tokens, which is important
        for commands like 'say "hello there"' where the quoted message should be
        preserved as a single unit.
        
        Args:
            command_str (str): The raw command string
            
        Returns:
            list: A list of token strings
        """
        tokens = []
        
        # Regular expression pattern that preserves quoted strings
        # Matches either:
        # - A quoted string: "any text inside quotes"
        # - Any non-whitespace sequence: word
        pattern = r'("[^"]*"|\S+)'
        matches = re.finditer(pattern, command_str)
        
        for match in matches:
            token = match.group(0)
            # Remove quotes if it's a quoted string
            if token.startswith('"') and token.endswith('"'):
                token = token[1:-1]
            tokens.append(token)
        
        return tokens
    
    def _finalize_command(self, cmd, context):
        """
        Convert internal command representation to the final format.
        
        This creates the standard command object format expected by
        the command execution system.
        
        Args:
            cmd (dict): The processed command object
            context (CommandContext): The command context
            
        Returns:
            dict: Standardized command object
        """
        # Assemble the final command object with standard keys
        result = {
            "verb": cmd.get("verb"),
            "subject": cmd.get("subject"),
            "object": cmd.get("object"),
            "instrument": cmd.get("instrument"),
            "original": cmd.get("original"),
            "preposition": cmd.get("preposition"),
            "reversed_syntax": cmd.get("reversed_syntax", False)
        }
        
        # Add special flags if present
        if "from_container" in cmd:
            result["from_container"] = cmd["from_container"]
        
        # Update context with this command's components
        context.update(result["verb"], result["subject"], result["object"], result["instrument"])
        
        return result
    
    def _detect_chained_commands(self, command_str):
        """
        Detect and split comma-separated commands.
        
        Handles comma chaining like "get sword, look at it, drop it"
        while preserving commas inside quoted strings.
        
        Args:
            command_str (str): The raw command string
            
        Returns:
            list: A list of individual command strings
        """
        # Split by commas, but preserve commas inside quoted strings
        # The regex pattern uses a negative lookahead to ensure we're not inside quotes
        pattern = r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)'
        parts = re.split(pattern, command_str)
        
        # Return non-empty parts
        return [part.strip() for part in parts if part.strip()]


# -------------------------------------------------------------------------
# Preposition dictionaries for syntax detection
# -------------------------------------------------------------------------

# Prepositions that indicate standard syntax (verb X with Y)
STANDARD_PREPOSITIONS = {
    "with": "with", "w": "with", "wi": "with", 
    "using": "using", "u": "using",
    "by": "by", "via": "via", "through": "through", 
    "underneath": "underneath", "beneath": "beneath", "under": "under"
}

# Prepositions that indicate reversed syntax (verb X to/on/in Y)
REVERSED_PREPOSITIONS = {
    "to": "to", "t": "to", "onto": "onto", "toward": "toward", "towards": "towards",
    "on": "on", "upon": "upon", "over": "over",
    "in": "in", "i": "in", "into": "into", "inside": "inside", 
    "at": "at", "around": "around", "about": "about"
}

# -------------------------------------------------------------------------
# Middleware functions for the parser pipeline
# -------------------------------------------------------------------------

def detect_message_commands(cmd, context, registry):
    """
    Identify special message commands (say, tell, shout).
    
    This middleware detects two special command formats:
    1. "TEXT" - A quoted string at the beginning becomes a say command
    2. PLAYER TEXT - A player name followed by text becomes a tell command
    
    These are detected early in the pipeline to bypass normal parsing.
    
    Args:
        cmd (dict): The command object being built
        context (CommandContext): The command context
        registry: The command registry
        
    Returns:
        dict: The potentially modified command object
    """
    original = cmd["original"]
    tokens = cmd["tokens"]
    online_sessions = cmd.get("online_sessions")
    
    # Handle "TEXT" → say command
    if original.startswith('"'):
        cmd["verb"] = "say"
        cmd["subject"] = original[1:].strip()
        cmd["abort_pipeline"] = True  # Skip further processing
        return cmd
    
    # Handle PLAYER TEXT → tell command
    if len(tokens) > 1:
        first_word = tokens[0].lower()
        message = " ".join(tokens[1:])
        
        if online_sessions:
            all_players = [session.get('player') for session in online_sessions.values() 
                          if session.get('player') is not None]
            for player in all_players:
                if player.name.lower() == first_word:
                    cmd["verb"] = "tell"
                    cmd["subject"] = player.name
                    cmd["instrument"] = message
                    cmd["abort_pipeline"] = True
                    return cmd
        elif cmd.get("players_in_room"):
            for player in cmd["players_in_room"]:
                if player.name.lower() == first_word:
                    cmd["verb"] = "tell"
                    cmd["subject"] = player.name
                    cmd["instrument"] = message
                    cmd["abort_pipeline"] = True
                    return cmd
    
    return cmd

def resolve_abbreviations(cmd, context, registry):
    """
    Expand command abbreviations to their full form.
    
    This middleware identifies abbreviations for commands (like 'n' for 'north')
    and expands them to their full form. It handles both direction aliases and
    general command aliases.
    
    Args:
        cmd (dict): The command object being built
        context (CommandContext): The command context
        registry: The command registry with alias information
        
    Returns:
        dict: The modified command object with expanded verb
    """
    tokens = cmd["tokens"]
    if not tokens:
        return cmd
    
    # Get verb (first token)
    verb = tokens[0].lower()
    
    # Check all aliases in registry
    if hasattr(registry, "all_aliases") and verb in registry.all_aliases:
        cmd["verb"] = registry.all_aliases[verb]
    elif hasattr(registry, "direction_aliases") and verb in registry.direction_aliases:
        cmd["verb"] = registry.direction_aliases[verb]
        cmd["is_movement"] = True
    else:
        cmd["verb"] = verb
    
    return cmd

def detect_container_commands(cmd, context, registry):
    tokens = cmd["tokens"]
    if not tokens:
        return cmd
    
    # Normalize tokens and expand abbreviations
    normalized = []
    for token_index, token in enumerate(tokens):
        token_lower = token.lower()
        # Handle command abbreviations
        if token_index == 0:  # First token (verb)
            if token_lower == "g":
                normalized.append("get")
            elif token_lower == "t":
                normalized.append("take")
            else:
                normalized.append(token_lower)
        # Handle preposition abbreviations
        elif token_lower == "fr":
            normalized.append("from")
        elif token_lower == "i":
            normalized.append("in")
        else:
            normalized.append(token_lower)
    
    # Check for "put/insert X in Y" pattern (container commands)
    if normalized[0] in ["put", "insert"] and len(normalized) > 3:
        in_index = -1
        for i, token in enumerate(normalized[1:], 1):
            if token == "in":
                in_index = i
                break
        
        if in_index > 1 and in_index < len(normalized) - 1:
            item_name = " ".join(tokens[1:in_index])
            container_name = " ".join(tokens[in_index+1:])
            
            # Resolve pronouns
            item_name = context.resolve_pronoun(item_name)
            container_name = context.resolve_pronoun(container_name)
            
            cmd["verb"] = "put"
            cmd["subject"] = item_name
            cmd["instrument"] = container_name
            cmd["preposition"] = "in"
            cmd["abort_pipeline"] = True
            return cmd
    # Check for "get/take/remove X from Y" pattern
    if normalized[0] in ["get", "take", "remove"] and len(normalized) > 3:
        from_index = -1
        for i, token in enumerate(normalized[1:], 1):
            if token == "from":
                from_index = i
                break
        
        if from_index > 1 and from_index < len(normalized) - 1:
            item_name = " ".join(tokens[1:from_index])
            target_name = " ".join(tokens[from_index+1:])
            
            # Check if the target name matches a player
            is_player = False
            if cmd.get("players_in_room"):
                for player in cmd["players_in_room"]:
                    if target_name.lower() in player.name.lower():
                        is_player = True
                        break
            if not is_player and cmd.get("online_sessions"):
                for session in cmd["online_sessions"].values():
                    player = session.get("player")
                    if player and target_name.lower() in player.name.lower():
                        is_player = True
                        break
            if is_player:
                # If the target is a player, don't handle it as a container command.
                # Let the 'steal' middleware process this command.
                return cmd
            
            # Resolve pronouns
            item_name = context.resolve_pronoun(item_name)
            target_name = context.resolve_pronoun(target_name)
            
            cmd["verb"] = "get"
            cmd["subject"] = item_name
            cmd["instrument"] = target_name
            cmd["preposition"] = "from"
            cmd["from_container"] = True
            cmd["abort_pipeline"] = True
            return cmd
    
    return cmd

def detect_steal_command(cmd, context, registry):
    """
    Detect steal commands like get X from Y, steal X from Y
    
    This middleware identifies container-related command patterns with complex structure:
    - get/take/steal X from Y
    where Y = player
    
    It handles abbreviations and produces a standardized command format.
    
    Args:
        cmd (dict): The command object being built
        context (CommandContext): The command context
        registry: The command registry
        
    Returns:
        dict: The potentially modified command object
    """
    tokens = cmd["tokens"]
    if not tokens:
        return cmd
    
    # Normalize tokens and expand abbreviations
    normalized = []
    for token_index, token in enumerate(tokens):
        token_lower = token.lower()
        # Handle command abbreviations
        if token_index == 0:  # First token (verb)
            if token_lower == "g":
                normalized.append("get")
            else:
                normalized.append(token_lower)
        # Handle preposition abbreviations
        elif token_lower == "fr":
            normalized.append("from")
        else:
            normalized.append(token_lower)
    
    
    # Check for "get/take/remove X from Y" pattern
    if normalized[0] in ["get", "take", "steal"] and len(normalized) > 3:
        from_index = -1
        for i, token in enumerate(normalized[1:], 1):
            if token == "from":
                from_index = i
                break
        
        if from_index > 1 and from_index < len(normalized) - 1:
            # Get original tokens for better preservation of case
            item_name = " ".join(tokens[1:from_index])
            container_name = " ".join(tokens[from_index+1:])
            
            # Resolve pronouns
            item_name = context.resolve_pronoun(item_name)
            player_name = context.resolve_pronoun(container_name)
            
            cmd["verb"] = "steal"
            cmd["subject"] = player_name
            cmd["instrument"] = item_name
            cmd["preposition"] = "from"
            # cmd["from_container"] = True
            cmd["abort_pipeline"] = True
            return cmd
    
    return cmd

def detect_interaction_syntax(cmd, context, registry):
    """
    Handle interaction syntax with prepositions.
    
    This middleware detects and parses two main command syntaxes:
    - Standard syntax: verb subject with instrument (open door with key)
    - Reversed syntax: verb instrument to subject (tie rope to tree)
    
    It identifies prepositions and properly assigns subjects and instruments.
    
    Args:
        cmd (dict): The command object being built
        context (CommandContext): The command context
        registry: The command registry
        
    Returns:
        dict: The modified command object with parsed components
    """
    tokens = cmd["tokens"]
    if not tokens or cmd.get("abort_pipeline"):
        return cmd
    
    # Look for prepositions (skip the verb)
    standard_index = -1
    reversed_index = -1
    
    for i, token in enumerate(tokens[1:], 1):  # Skip verb
        token_lower = token.lower()
        if token_lower in STANDARD_PREPOSITIONS:
            standard_index = i
            cmd["preposition"] = STANDARD_PREPOSITIONS[token_lower]
            break
        elif token_lower in REVERSED_PREPOSITIONS:
            reversed_index = i
            cmd["preposition"] = REVERSED_PREPOSITIONS[token_lower]
            break
    
    if standard_index > 0:
        # Standard syntax: verb subject with instrument
        cmd["subject"] = " ".join(tokens[1:standard_index]) if standard_index > 1 else None
        cmd["instrument"] = " ".join(tokens[standard_index+1:]) if standard_index < len(tokens) - 1 else None
        cmd["reversed_syntax"] = False
    elif reversed_index > 0:
        # Reversed syntax: verb instrument to subject
        cmd["instrument"] = " ".join(tokens[1:reversed_index]) if reversed_index > 1 else None
        cmd["subject"] = " ".join(tokens[reversed_index+1:]) if reversed_index < len(tokens) - 1 else None
        cmd["reversed_syntax"] = True
    else:
        # No preposition, just subject
        cmd["subject"] = " ".join(tokens[1:]) if len(tokens) > 1 else None
    
    return cmd

def resolve_pronouns(cmd, context, registry):
    """
    Replace pronouns (it, him, her, them) with their referents.
    
    This middleware performs pronoun resolution by checking with the command
    context for appropriate referents from previous commands.
    
    Args:
        cmd (dict): The command object being built
        context (CommandContext): The command context
        registry: The command registry
        
    Returns:
        dict: The command object with resolved pronouns
    """
    if cmd.get("abort_pipeline"):
        return cmd
    
    if cmd.get("subject"):
        cmd["subject"] = context.resolve_pronoun(cmd["subject"])
    
    if cmd.get("instrument"):
        cmd["instrument"] = context.resolve_pronoun(cmd["instrument"])
    
    return cmd

def is_movement_command(verb):
    """
    Check if a verb is a movement command.
    
    Movement commands are directional verbs like "north", "south", "up", etc.
    
    Args:
        verb (str): The command verb to check
        
    Returns:
        bool: True if it's a movement command, False otherwise
    """
    if not verb:
        return False
    
    # Movement commands are directions
    directions = ["north", "south", "east", "west", 
                 "northeast", "northwest", "southeast", "southwest",
                 "up", "down", "in", "out"]
    
    # Also check abbreviations
    direction_abbrevs = ["n", "s", "e", "w", "ne", "nw", "se", "sw", "u", "d"]
    
    return verb.lower() in directions or verb.lower() in direction_abbrevs

# Factory function to create a parser with default middleware
def create_default_parser(registry):
    """
    Create a parser instance with the standard middleware pipeline.
    
    This configures a CommandParser with the standard middleware functions
    in the appropriate processing order.
    
    Args:
        registry: The command registry to use
        
    Returns:
        CommandParser: A configured parser instance
    """
    parser = CommandParser(registry)
    
    # Add middleware in processing order - the sequence matters!
    # 1. First detect special message commands
    parser.add_middleware(detect_message_commands)
    # 2. Resolve command abbreviations
    parser.add_middleware(resolve_abbreviations)
    # 3. Check for container commands
    parser.add_middleware(detect_container_commands)
    # 4. Detect interaction syntax
    parser.add_middleware(detect_interaction_syntax)
    # 5. Finally resolve pronouns
    parser.add_middleware(resolve_pronouns)
    # 6. Add steal
    parser.add_middleware(detect_steal_command)
    
    return parser

# Create a default parser instance for direct use
default_parser = create_default_parser(None)  # Will be initialized properly in __init__.py