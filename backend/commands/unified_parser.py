# backend/commands/unified_parser.py

import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyntaxPattern:
    """Defines a command syntax pattern that can be matched against input."""
    def __init__(self, pattern_str, priority=0, handler=None):
        self.pattern_str = pattern_str  # e.g. "VERB SUBJECT with INSTRUMENT"
        self.priority = priority  # Higher numbers take precedence
        self.handler = handler  # Optional custom parser function
        self.components = self._parse_pattern()
    
    def _parse_pattern(self):
        """Convert pattern string to structured representation."""
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
        Check if tokens match this pattern and extract components.
        Returns (success, components_dict)
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
                # Check for literal match
                if token_index < len(tokens) and tokens[token_index].lower() == component["value"]:
                    token_index += 1
                    pattern_index += 1
                else:
                    # Failed to match literal
                    return False, {}
            elif "type" in component:
                # Variable component
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

    def update(self, verb=None, subject=None, obj=None, instrument=None, player=None, gender=None):
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
    """Unified command parser with middleware pipeline architecture."""
    def __init__(self, command_registry):
        self.registry = command_registry
        self.middleware = []
    
    def add_middleware(self, func):
        """Add a processing step to the parser pipeline."""
        self.middleware.append(func)
    
    def parse(self, command_str, context=None, players_in_room=None, online_sessions=None):
        """
        Parse a command string into structured command objects.
        Returns a list of parsed commands (for handling chained commands).
        """
        if not context:
            context = CommandContext()
        
        # Step 1: Check for chained commands first
        chained_commands = self._detect_chained_commands(command_str)
        if len(chained_commands) > 1:
            # Process each command separately
            results = []
            for cmd in chained_commands:
                # Recursively parse each part
                parsed = self.parse(cmd, context, players_in_room, online_sessions)
                results.extend(parsed)
            return results
        
        # Not a chained command, process normally
        # Initialize command object with original text
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
            if cmd.get("abort_pipeline"):
                break
        
        return [self._finalize_command(cmd, context)]
    
    def _tokenize(self, command_str):
        """Split command into tokens, preserving quoted strings."""
        tokens = []
        
        # Simple tokenizer that preserves quoted strings
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
        """Convert internal command representation to the final format."""
        # Make sure the command is in the expected format
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
        
        # Update context
        context.update(result["verb"], result["subject"], result["object"], result["instrument"])
        
        return result
    
    def _detect_chained_commands(self, command_str):
        """Detect and split comma-separated commands."""
        # Split by commas, preserving quoted strings
        pattern = r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)'
        parts = re.split(pattern, command_str)
        
        # Return non-empty parts
        return [part.strip() for part in parts if part.strip()]


# Lists of prepositions for syntax detection
STANDARD_PREPOSITIONS = {
    "with": "with", "w": "with", "wi": "with", 
    "using": "using", "u": "using",
    "by": "by", "via": "via", "through": "through", 
    "underneath": "underneath", "beneath": "beneath", "under": "under"
}

REVERSED_PREPOSITIONS = {
    "to": "to", "t": "to", "onto": "onto", "toward": "toward", "towards": "towards",
    "on": "on", "upon": "upon", "over": "over",
    "in": "in", "i": "in", "into": "into", "inside": "inside", 
    "at": "at", "around": "around", "about": "about"
}

# Standard middleware functions

def detect_message_commands(cmd, context, registry):
    """Identify special message commands (say, tell, shout)."""
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
    """Expand command abbreviations to their full form."""
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
    """Detect special container commands like put X in Y and get X from Y."""
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
    
    # Check for "put/insert X in Y" pattern
    if normalized[0] in ["put", "insert"] and len(normalized) > 3:
        in_index = -1
        for i, token in enumerate(normalized[1:], 1):
            if token == "in":
                in_index = i
                break
        
        if in_index > 1 and in_index < len(normalized) - 1:
            # Get original tokens for better preservation of case
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
            # Get original tokens for better preservation of case
            item_name = " ".join(tokens[1:from_index])
            container_name = " ".join(tokens[from_index+1:])
            
            # Resolve pronouns
            item_name = context.resolve_pronoun(item_name)
            container_name = context.resolve_pronoun(container_name)
            
            cmd["verb"] = "get"
            cmd["subject"] = item_name
            cmd["instrument"] = container_name
            cmd["preposition"] = "from"
            cmd["from_container"] = True
            cmd["abort_pipeline"] = True
            return cmd
    
    return cmd

def detect_interaction_syntax(cmd, context, registry):
    """Handle interaction syntax with prepositions."""
    tokens = cmd["tokens"]
    if not tokens or cmd.get("abort_pipeline"):
        return cmd
    
    # Look for prepositions
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
    """Replace pronouns (it, him, her, them) with their referents."""
    if cmd.get("abort_pipeline"):
        return cmd
    
    if cmd.get("subject"):
        cmd["subject"] = context.resolve_pronoun(cmd["subject"])
    
    if cmd.get("instrument"):
        cmd["instrument"] = context.resolve_pronoun(cmd["instrument"])
    
    return cmd

# Factory function to create a parser with default middleware
def create_default_parser(registry):
    """Create a parser instance with the standard middleware."""
    parser = CommandParser(registry)
    
    # Add middleware in processing order
    parser.add_middleware(detect_message_commands)
    parser.add_middleware(resolve_abbreviations)
    parser.add_middleware(detect_container_commands)
    parser.add_middleware(detect_interaction_syntax)
    parser.add_middleware(resolve_pronouns)
    
    return parser