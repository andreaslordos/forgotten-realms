# backend/commands/natural_language_parser.py

import logging
import re
from typing import List, Dict, Tuple, Set, Optional, Any, Callable, Union
from services.get_online_players import get_online_players

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create file handler
file_handler = logging.FileHandler('parser_debug.log')
file_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.debug("Natural Language Parser module loading")

# -------------------------------------------------------------------------
# Error Classes
# -------------------------------------------------------------------------

class ParserError(Exception):
    """Base class for parser errors."""
    pass

class UnknownWordError(ParserError):
    """Error for when a word is not recognized."""
    def __init__(self, word):
        self.word = word
        super().__init__(f"I don't know the word '{word}'.")

class AmbiguousReferenceError(ParserError):
    """Error for when an object reference is ambiguous."""
    def __init__(self, noun, options):
        self.noun = noun
        self.options = options
        super().__init__(f"Which {noun} do you mean? I can see: {', '.join(str(o) for o in options)}.")

class MissingObjectError(ParserError):
    """Error for when a required object is missing."""
    def __init__(self, verb):
        self.verb = verb
        super().__init__(f"What do you want to {verb}?")

class SyntaxError(ParserError):
    """Error for when the command syntax is invalid."""
    def __init__(self, message):
        super().__init__(message)

# -------------------------------------------------------------------------
# Tokenization
# -------------------------------------------------------------------------

class TokenType:
    """Enum-like class for token types."""
    WORD = "WORD"
    QUOTED_STRING = "QUOTED_STRING"
    NUMBER = "NUMBER"
    PUNCTUATION = "PUNCTUATION"

class Token:
    """Represents a token in the command string."""
    def __init__(self, type_: str, value: str, position: int):
        self.type = type_
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', {self.position})"

def tokenize(command_str: str) -> List[Token]:
    """
    Split input string into tokens.
    
    Handles:
    - Regular words
    - Quoted strings
    - Numbers
    - Punctuation
    """
    tokens = []
    position = 0
    
    logger.debug(f"Tokenizing input: '{command_str}'")
    
    # Special case for commands that start with a quotation mark (say)
    if command_str.startswith('"'):
        logger.debug(f"Detected quote-prefixed command, mapping to say: '{command_str}'")
        # Create a special token for "say"
        tokens.append(Token(TokenType.WORD, "say", 0))
        # Rest of the string becomes the message content
        content = command_str[1:].strip()
        if content:
            tokens.append(Token(TokenType.QUOTED_STRING, content, 1))
        return tokens
    
    # Define regex patterns
    patterns = [
        (r'"([^"]*)"', TokenType.QUOTED_STRING),  # Quoted strings
        (r'\d+', TokenType.NUMBER),               # Numbers
        (r'[.,;:!?]', TokenType.PUNCTUATION),     # Punctuation
        (r'\S+', TokenType.WORD)                  # Words (anything non-whitespace)
    ]
    
    # Combined pattern
    pattern = '|'.join(f'({p})' for p, _ in patterns)
    
    # Find all matches
    for match in re.finditer(pattern, command_str):
        # Determine the type by finding which group matched
        matched_value = match.group(0)
        matched_position = match.start()
        
        # Default to WORD type
        token_type = TokenType.WORD
        
        # Check if it's a quoted string
        if matched_value.startswith('"') and matched_value.endswith('"'):
            token_type = TokenType.QUOTED_STRING
            # Remove the quotes
            matched_value = matched_value[1:-1]
        # Check if it's a number
        elif matched_value.isdigit():
            token_type = TokenType.NUMBER
        # Check if it's punctuation
        elif matched_value in ".,;:!?":
            token_type = TokenType.PUNCTUATION
        
        tokens.append(Token(token_type, matched_value.lower(), matched_position))
    
    logger.debug(f"Tokenization result: {tokens}")
    return tokens

# -------------------------------------------------------------------------
# Vocabulary Management
# -------------------------------------------------------------------------

class VocabularyManager:
    """Manages the vocabulary, abbreviations, and word recognition."""
    
    def __init__(self):
        # Dictionary of abbreviations: {"g": "get", "n": "north", ...}
        # Now enhanced to support context-aware abbreviations
        # Format: {
        #   "abbreviation": "expansion" (simple case),
        #   "abbreviation": {"default": "expansion1", "in_prep_position": "expansion2"} (context-aware)
        # }
        self.abbreviations = {}
        
        # Dictionary of synonyms: {"grab": "get", "take": "get", ...}
        self.synonyms = {}
        
        # Set of known verbs
        self.verbs = set()
        
        # Set of known prepositions
        self.prepositions = set()
        
        # Dictionary of preposition types: {"with": "standard", "to": "reversed", ...}
        self.preposition_types = {}
        
        # Set of known adverbs
        self.adverbs = set()
        
        # Set of known directions (for movement commands)
        self.directions = set()
        
        # Initialize the standard vocabularies
        self._initialize_vocabularies()
        
        logger.debug(f"VocabularyManager initialized with {len(self.abbreviations)} abbreviations")
    
    def _initialize_vocabularies(self):
        """Initialize standard vocabularies with default values."""
        # Standard prepositions (verb X with Y)
        standard_prepositions = {
            "with", "using", "by", "via", "through", "underneath", "beneath", "under"
        }
        for prep in standard_prepositions:
            self.prepositions.add(prep)
            self.preposition_types[prep] = "standard"
        
        # Reversed prepositions (verb X to/on/in Y)
        reversed_prepositions = {
            "to", "onto", "toward", "towards", "on", "upon", "over",
            "in", "into", "inside", "at", "around", "about", "from"
        }
        for prep in reversed_prepositions:
            self.prepositions.add(prep)
            self.preposition_types[prep] = "reversed"
        
        # Common verb abbreviations
        simple_abbreviations = {
            "g": "get",
            "dr": "drop",
            "fr": "from",
            "i": "inventory",
            "inv": "inventory",
            "l": "look",
            "k": "kill",
            "n": "north",
            "s": "south",
            "e": "east",
            "nw": "northwest",
            "se": "southeast",
            "sw": "southwest",
            "u": "up",
            "d": "down",
            "t": "treasure",
            "o": "out",
        }
        self.abbreviations.update(simple_abbreviations)
        
        # Context-aware abbreviations (different meaning based on position)
        self.abbreviations["w"] = {"default": "west", "in_prep_position": "with"}
        self.abbreviations["wi"] = {"default": "with", "in_prep_position": "with"}
        self.abbreviations["ne"] = {"default": "northeast", "in_prep_position": "northeast"}
        
        # Common verb synonyms
        self.synonyms.update({
            "grab": "get",
            "take": "get",
            "discard": "drop",
            "throw": "drop",
            "toss": "drop",
            "examine": "look",
            "check": "look",
            "inspect": "look",
            "bye": "quit",
            "go": "move"  # Add 'go' as a synonym for a special movement handler 
        })
        
        # Common directions
        self.directions.update({
            "north", "south", "east", "west", 
            "northeast", "northwest", "southeast", "southwest",
            "up", "down", "in", "out", "jump", "swamp"
        })
        
        # Common adverbs
        self.adverbs.update({
            "carefully", "quickly", "slowly", "quietly", "loudly", 
            "briefly", "again", "now", "up", "down", "away", "back"
        })
        
        # Add 'move' as a special verb for movement commands
        self.verbs.add("move")
    
    def add_abbreviation(self, abbreviation: str, full_word: str, context: str = None):
        """
        Add a new abbreviation.
        
        Args:
            abbreviation: The abbreviated form
            full_word: The expanded form
            context: Optional context specifier ('default', 'in_prep_position', etc.)
        """
        abbreviation = abbreviation.lower()
        full_word = full_word.lower()
        
        if context:
            if abbreviation not in self.abbreviations:
                self.abbreviations[abbreviation] = {"default": full_word}
            elif isinstance(self.abbreviations[abbreviation], dict):
                self.abbreviations[abbreviation][context] = full_word
            else:
                # Convert simple abbreviation to context-aware
                default_value = self.abbreviations[abbreviation]
                self.abbreviations[abbreviation] = {"default": default_value, context: full_word}
        else:
            # Simple abbreviation
            if isinstance(self.abbreviations.get(abbreviation), dict):
                self.abbreviations[abbreviation]["default"] = full_word
            else:
                self.abbreviations[abbreviation] = full_word
                
        logger.debug(f"Added abbreviation: {abbreviation} -> {full_word}" + 
                    (f" (context: {context})" if context else ""))
    
    def add_synonym(self, synonym: str, base_word: str):
        """Add a new synonym."""
        self.synonyms[synonym.lower()] = base_word.lower()
        logger.debug(f"Added synonym: {synonym} -> {base_word}")
    
    def add_verb(self, verb: str):
        """Add a new verb to the vocabulary."""
        self.verbs.add(verb.lower())
        logger.debug(f"Added verb: {verb}")
    
    def add_preposition(self, preposition: str, preposition_type: str = "standard"):
        """Add a new preposition to the vocabulary."""
        self.prepositions.add(preposition.lower())
        self.preposition_types[preposition.lower()] = preposition_type
        logger.debug(f"Added preposition: {preposition} (type: {preposition_type})")
    
    def add_adverb(self, adverb: str):
        """Add a new adverb to the vocabulary."""
        self.adverbs.add(adverb.lower())
        logger.debug(f"Added adverb: {adverb}")
    
    def add_direction(self, direction: str):
        """Add a new direction to the vocabulary."""
        self.directions.add(direction.lower())
        logger.debug(f"Added direction: {direction}")
    
    def expand_word(self, word: str, position: int = 0, total_words: int = 1) -> str:
        """
        Expand abbreviations and resolve synonyms with context awareness.
        
        Args:
            word: The word to expand
            position: The position of the word in the command (0-based)
            total_words: Total number of words in the command
            
        Returns:
            The expanded word
        """
        word = word.lower()
        original = word
        
        # Check if it's an abbreviation
        if word in self.abbreviations:
            # Handle context-aware abbreviations
            if isinstance(self.abbreviations[word], dict):
                # Improved context detection
                if position == 0:
                    # First word is likely a verb
                    expanded = self.abbreviations[word].get("default")
                elif position > 0 and position < total_words - 1:
                    # Middle position - more aggressive about using preposition expansion
                    if "in_prep_position" in self.abbreviations[word]:
                        # Prefer preposition expansions in non-first positions
                        expanded = self.abbreviations[word]["in_prep_position"]
                    else:
                        expanded = self.abbreviations[word].get("default")
                    
                    # Additional debugging
                    logger.debug(f"Context-based expansion: pos={position}, total={total_words}, "
                                f"original='{original}', expanded='{expanded}'")
                else:
                    # Last word - use default
                    expanded = self.abbreviations[word].get("default")
                
                if expanded:
                    word = expanded
                    logger.debug(f"Expanded context-aware abbreviation: {original} -> {word} (position {position})")
            else:
                # Simple abbreviation
                word = self.abbreviations[word]
                logger.debug(f"Expanded abbreviation: {original} -> {word}")
        
        # Check if it's a synonym
        if word in self.synonyms:
            word = self.synonyms[word]
            logger.debug(f"Resolved synonym: {original} -> {word}")
        
        return word
    
    def is_verb(self, word: str) -> bool:
        """Check if a word is a known verb."""
        return self.expand_word(word) in self.verbs
    
    def is_preposition(self, word: str) -> bool:
        """Check if a word is a known preposition."""
        return word.lower() in self.prepositions
    
    def is_standard_preposition(self, word: str) -> bool:
        """Check if a word is a standard preposition."""
        return word.lower() in self.prepositions and self.preposition_types.get(word.lower()) == "standard"
    
    def is_reversed_preposition(self, word: str) -> bool:
        """Check if a word is a reversed preposition."""
        return word.lower() in self.prepositions and self.preposition_types.get(word.lower()) == "reversed"
    
    def is_adverb(self, word: str) -> bool:
        """Check if a word is a known adverb."""
        return word.lower() in self.adverbs
    
    def is_direction(self, word: str) -> bool:
        """Check if a word is a known direction."""
        expanded = self.expand_word(word)
        result = expanded in self.directions
        logger.debug(f"Direction check: {word} -> {expanded} = {result}")
        return result

# -------------------------------------------------------------------------
# Command Context for Pronoun Resolution
# -------------------------------------------------------------------------

class CommandContext:
    """
    Stores command context for pronoun resolution.

    Keeps track of:
    - Last verb
    - Last subject
    - Last instrument
    - Last referenced creature (them)
    - Last referenced male (him)
    - Last referenced female (her)
    - Last referenced object (it)
    - mob_manager for binding mobs
    """

    def __init__(self, mob_manager=None):
        self.last_verb = None
        self.last_subject = None
        self.last_instrument = None
        self.last_them = None
        self.last_him = None
        self.last_her = None
        self.last_it = None
        self.mob_manager = mob_manager
    
    def get(self, key, default=None):
        """Get an attribute like a dictionary for compatibility."""
        return getattr(self, key, default)

    def update(self, verb=None, subject=None, instrument=None, gender=None):
        """Update the context with new references."""
        if verb:
            self.last_verb = verb

        if subject:
            if hasattr(subject, 'get') and subject.get('is_creature'):
                self.last_them = subject
                if gender == 'M':
                    self.last_him = subject
                elif gender == 'F':
                    self.last_her = subject
            else:
                self.last_it = subject

            self.last_subject = subject

        if instrument:
            self.last_instrument = instrument

    def resolve_pronoun(self, pronoun: str, game_state=None):
        """
        Resolve a pronoun to its referent.

        Args:
            pronoun: The pronoun to resolve
            game_state: Optional game state for contextual resolution

        Returns:
            The resolved referent or None if no referent is found
        """
        pronoun = pronoun.lower()

        if pronoun == "it":
            return self.last_it
        elif pronoun == "him":
            return self.last_him
        elif pronoun == "her":
            return self.last_her
        elif pronoun == "them":
            return self.last_them

        return None

# -------------------------------------------------------------------------
# Syntax Pattern Matching
# -------------------------------------------------------------------------

class SyntaxPattern:
    """
    Defines a command syntax pattern.
    
    Patterns are defined using the format:
    - "VERB" (single-word command)
    - "VERB SUBJECT" (verb-object command)
    - "VERB SUBJECT with INSTRUMENT" (standard syntax)
    - "VERB INSTRUMENT to SUBJECT" (reversed syntax)
    """
    
    def __init__(self, pattern_str: str, priority: int = 0):
        self.pattern_str = pattern_str
        self.priority = priority
        self.components = self._parse_pattern()
        logger.debug(f"Created SyntaxPattern: '{pattern_str}' with priority {priority}")
    
    def _parse_pattern(self):
        """Parse the pattern string into components."""
        parts = self.pattern_str.split()
        components = []
        
        for part in parts:
            if part.isupper():
                # Variable component (e.g., VERB, SUBJECT)
                components.append({"type": part})
            else:
                # Literal component (e.g., "with", "to")
                components.append({"value": part.lower()})
        
        logger.debug(f"Parsed pattern '{self.pattern_str}' into components: {components}")
        return components
    
    def matches(self, tokens: List[Token]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a sequence of tokens matches this pattern.
        
        Args:
            tokens: List of tokens to match against the pattern
            
        Returns:
            Tuple of (matched, bindings) where:
                matched: Boolean indicating if the pattern matched
                bindings: Dictionary of bindings for pattern variables
        """
        if not tokens:
            logger.debug(f"No tokens to match against pattern '{self.pattern_str}'")
            return False, {}
        
        # Simple state machine to match pattern
        components_dict = {}
        pattern_index = 0
        token_index = 0
        
        logger.debug(f"Trying to match {len(tokens)} tokens against pattern '{self.pattern_str}'")
        
        while pattern_index < len(self.components) and token_index < len(tokens):
            component = self.components[pattern_index]
            token = tokens[token_index]
            
            # In matches method for "value" components (literals):
            if "value" in component:
                # Literal matching - must match exact word
                if token_index < len(tokens) and tokens[token_index].value.lower() == component["value"].lower():
                    logger.debug(f"Matched literal '{component['value']}' at position {token_index}")
                    token_index += 1
                    pattern_index += 1
                else:
                    # Failed to match literal
                    logger.debug(f"Failed to match literal '{component['value']}' against token '{tokens[token_index].value}'")
                    return False, {}
            
            elif "type" in component:
                # Variable component
                component_type = component["type"]
                
                if component_type == "VERB":
                    # Verb should be a single token
                    components_dict["verb"] = token.value
                    logger.debug(f"Bound VERB to '{token.value}'")
                    token_index += 1
                    pattern_index += 1
                
                elif component_type == "SUBJECT":
                    # Subject can span multiple tokens until next component or end
                    start_idx = token_index
                    end_idx = start_idx
                    
                    # Special case: If SUBJECT is the last component, consume all remaining tokens
                    if pattern_index + 1 >= len(self.components):
                        # Consume all remaining tokens for the subject
                        while token_index < len(tokens):
                            end_idx += 1
                            token_index += 1
                    else:
                        # Original logic for when there are components after SUBJECT
                        while (token_index < len(tokens) and 
                            (not "value" in self.components[pattern_index + 1] or 
                                tokens[token_index].value != self.components[pattern_index + 1]["value"])):
                            end_idx += 1
                            token_index += 1
                            if token_index >= len(tokens):
                                break
                    
                    if start_idx < end_idx:
                        subject_tokens = tokens[start_idx:end_idx]
                        components_dict["subject"] = " ".join(t.value for t in subject_tokens)
                        logger.debug(f"Bound SUBJECT to '{components_dict['subject']}'")
                    else:
                        components_dict["subject"] = None
                        logger.debug("No tokens for SUBJECT, binding to None")
                    
                    pattern_index += 1

                elif component_type == "INSTRUMENT":
                    # Instrument can span multiple tokens until next component or end
                    start_idx = token_index
                    end_idx = start_idx
                    
                    # Special case: If INSTRUMENT is the last component, consume all remaining tokens
                    if pattern_index + 1 >= len(self.components):
                        # Consume all remaining tokens for the instrument
                        while token_index < len(tokens):
                            end_idx += 1
                            token_index += 1
                    else:
                        # Logic for when there are components after INSTRUMENT
                        while (token_index < len(tokens) and 
                            (not "value" in self.components[pattern_index + 1] or 
                                tokens[token_index].value != self.components[pattern_index + 1]["value"])):
                            end_idx += 1
                            token_index += 1
                            if token_index >= len(tokens):
                                break
                    
                    if start_idx < end_idx:
                        instrument_tokens = tokens[start_idx:end_idx]
                        components_dict["instrument"] = " ".join(t.value for t in instrument_tokens)
                        logger.debug(f"Bound INSTRUMENT to '{components_dict['instrument']}'")
                    else:
                        components_dict["instrument"] = None
                        logger.debug("No tokens for INSTRUMENT, binding to None")
                    
                    pattern_index += 1
                
                else:
                    # Unknown component type
                    logger.debug(f"Unknown component type: {component_type}")
                    return False, {}
            
            else:
                # Malformed component
                logger.debug(f"Malformed component: {component}")
                return False, {}
        
        # Check if we matched the entire pattern
        if pattern_index >= len(self.components):
            # Add preposition information if present
            for i, component in enumerate(self.components):
                if "value" in component and component["value"] in vocabulary_manager.prepositions:
                    preposition = component["value"]
                    components_dict["preposition"] = preposition
                    components_dict["reversed_syntax"] = vocabulary_manager.is_reversed_preposition(preposition)
                    logger.debug(f"Found preposition '{preposition}', reversed_syntax: {components_dict['reversed_syntax']}")
            
            logger.debug(f"Successfully matched pattern '{self.pattern_str}': {components_dict}")
            return True, components_dict
        
        logger.debug(f"Failed to match complete pattern '{self.pattern_str}'")
        return False, {}

class CommandStructure:
    """Base class for command structures."""
    
    def __init__(self, syntax_patterns: List[SyntaxPattern]):
        self.syntax_patterns = sorted(syntax_patterns, key=lambda p: -p.priority)
        logger.debug(f"Created CommandStructure with {len(syntax_patterns)} patterns")
    
    def parse(self, tokens: List[Token]) -> Optional[Dict[str, Any]]:
        """
        Parse tokens according to the syntax patterns.
        
        Args:
            tokens: List of tokens to parse
            
        Returns:
            Dictionary of parsed components or None if no pattern matched
        """
        for pattern in self.syntax_patterns:
            logger.debug(f"Trying pattern: '{pattern.pattern_str}'")
            matched, bindings = pattern.matches(tokens)
            if matched:
                logger.debug(f"Matched pattern '{pattern.pattern_str}': {bindings}")
                return bindings
        
        logger.debug("No patterns matched")
        return None

# -------------------------------------------------------------------------
# Command Structure Definitions
# -------------------------------------------------------------------------

# Standard command structures
ONE_WORD_COMMAND = CommandStructure([
    SyntaxPattern("VERB", priority=10)
])

# Lower the priority of VERB_OBJECT_COMMAND so more specific patterns are tried first
VERB_OBJECT_COMMAND = CommandStructure([
    SyntaxPattern("VERB SUBJECT", priority=11)  # Lower priority
])

# Increase the priority of standard syntax commands
STANDARD_SYNTAX_COMMAND = CommandStructure([
    SyntaxPattern("VERB SUBJECT with INSTRUMENT", priority=15),  # Higher priority
    SyntaxPattern("VERB SUBJECT using INSTRUMENT", priority=15),
    SyntaxPattern("VERB SUBJECT in INSTRUMENT", priority=15),
    SyntaxPattern("VERB SUBJECT on INSTRUMENT", priority=15),
    SyntaxPattern("VERB SUBJECT from INSTRUMENT", priority=15)
])

REVERSED_SYNTAX_COMMAND = CommandStructure([
    SyntaxPattern("VERB INSTRUMENT to SUBJECT", priority=15),  # Also higher priority
    SyntaxPattern("VERB INSTRUMENT at SUBJECT", priority=15),
    SyntaxPattern("VERB INSTRUMENT onto SUBJECT", priority=15),
    SyntaxPattern("VERB INSTRUMENT into SUBJECT", priority=15)
])

# Container commands should have the highest priority
CONTAINER_COMMAND = CommandStructure([
    SyntaxPattern("VERB SUBJECT in INSTRUMENT", priority=20),
    SyntaxPattern("VERB SUBJECT from INSTRUMENT", priority=20) 
])

# Movement command (just one word)
MOVEMENT_COMMAND = CommandStructure([
    SyntaxPattern("VERB", priority=10)
])


# -------------------------------------------------------------------------
# Object Binding
# -------------------------------------------------------------------------

class ObjectBinder:
    """
    Binds command components to actual game objects.
    
    This class handles:
    - Finding objects in inventory, room, or nested containers
    - Resolving ambiguous references
    - Handling quantity and "all" modifiers
    - Filtering by adjectives
    """
    def bind_entity(self, entity_name, entity_type, player, game_state, context):
        """
        General purpose binding function that tries to bind a name to an entity
        (player, item, etc.) based on context.
        """
        # Special case for 'all'
        if entity_name == 'all':
            logger.debug(f"Subject is 'all', returning special token")
            return 'all'
        
        # If there's a method to get online players
        online_players = get_online_players()
        
        for other_player in online_players:
            if other_player.name.lower() == entity_name.lower():
                logger.debug(f"Found {other_player.name} as entity, binding...")
                return other_player
        
        # If not a player, let the existing binding code handle it
        return None

    def bind_subject(self, subject_str: str, player, game_state, context):
        """
        Bind a subject string to game objects (including mobs).

        Args:
            subject_str: The subject string to bind
            player: The player object
            game_state: The game state
            context: The command context

        Returns:
            The bound object(s) or None if no matching object is found
        """
        logger.debug(f"Binding subject: '{subject_str}'")

        # First try to bind to a player using our helper function
        player_obj = self.bind_entity(subject_str, 'subject', player, game_state, context)
        if player_obj:
            return player_obj

        # Try to bind to a mob (if mob_manager is available in context)
        mob_manager = context.get('mob_manager') if context else None
        if mob_manager and player.current_room:
            mobs_in_room = mob_manager.get_mobs_in_room(player.current_room)
            for mob in mobs_in_room:
                if subject_str.lower() in mob.name.lower():
                    logger.debug(f"Found mob: {mob.name}")
                    return mob
        
        # Handle pronouns
        if subject_str.lower() in ["it", "him", "her", "them"]:
            result = context.resolve_pronoun(subject_str)
            logger.debug(f"Resolved pronoun '{subject_str}' to {result}")
            return result
        
        # Handle "all" as a special case
        if subject_str.lower() == "all":
            logger.debug("Subject is 'all', returning special token")
            return "all"
        
        # Handle "treasure" as a special case
        if subject_str.lower() in ["treasure", "t"]:
            logger.debug("Subject is 'treasure', returning special token")
            return "treasure"
        
        # Check player's inventory first
        for item in player.inventory:
            if subject_str.lower() == item.name.lower():
                logger.debug(f"Found exact matching item in inventory: {item.name}")
                return item
        
        # Then try exact name matching in room
        current_room = game_state.get_room(player.current_room)
        for item in current_room.get_items(game_state):
            if subject_str.lower() == item.name.lower():
                logger.debug(f"Found exact matching item in room: {item.name}")
                return item
        
        # Try exact name matching for other players
        for other_player in get_players_in_room(player.current_room, game_state):
            if subject_str.lower() == other_player.name.lower():
                logger.debug(f"Found exact matching player in room: {other_player.name}")
                return other_player
        
        # If no exact matches found, return None
        logger.debug(f"No matching object found for subject: '{subject_str}'")
        return None
    
    def bind_instrument(self, instrument_str: str, player, game_state, context):
        """
        Bind an instrument string to game objects (including mobs).

        Args:
            instrument_str: The instrument string to bind
            player: The player object
            game_state: The game state
            context: The command context

        Returns:
            The bound object(s) or None if no matching object is found
        """
        logger.debug(f"Binding instrument: '{instrument_str}'")

        # First try to bind to a player using our helper function
        player_obj = self.bind_entity(instrument_str, 'instrument', player, game_state, context)
        if player_obj:
            return player_obj

        # Try to bind to a mob (if mob_manager is available in context)
        mob_manager = context.get('mob_manager') if context else None
        if mob_manager and player.current_room:
            mobs_in_room = mob_manager.get_mobs_in_room(player.current_room)
            for mob in mobs_in_room:
                if instrument_str.lower() in mob.name.lower():
                    logger.debug(f"Found mob: {mob.name}")
                    return mob
        
        # Handle pronouns
        if instrument_str.lower() in ["it", "him", "her", "them"]:
            result = context.resolve_pronoun(instrument_str)
            logger.debug(f"Resolved pronoun '{instrument_str}' to {result}")
            return result
        
        # First try exact matches in inventory
        for item in player.inventory:
            if instrument_str.lower() == item.name.lower():
                logger.debug(f"Found exact matching item in inventory: {item.name}")
                return item
        
        # Then try exact matches in room
        current_room = game_state.get_room(player.current_room)
        for item in current_room.get_items(game_state):
            if instrument_str.lower() == item.name.lower():
                logger.debug(f"Found exact matching item in room: {item.name}")
                return item
        
        # Try exact matching for other players
        for other_player in get_players_in_room(player.current_room, game_state):
            if instrument_str.lower() == other_player.name.lower():
                logger.debug(f"Found exact matching player in room: {other_player.name}")
                return other_player
        
        # If no exact matches found, return None
        logger.debug(f"No matching object found for instrument: '{instrument_str}'")
        return None

# -------------------------------------------------------------------------
# Main Parser Class
# -------------------------------------------------------------------------

class NaturalLanguageParser:
    """
    Main parser class integrating all stages.

    This class handles:
    - Tokenizing input
    - Command chaining (splitting commands by comma or AND)
    - Syntax parsing with all command structures
    - Object binding
    - Error handling
    """

    def __init__(self, mob_manager=None):
        self.vocabulary = VocabularyManager()
        self.context = CommandContext(mob_manager=mob_manager)
        self.object_binder = ObjectBinder()
        self.command_registry = None  # Will be set by __init__.py
        logger.debug("NaturalLanguageParser initialized")

    def set_mob_manager(self, mob_manager):
        """Update the mob_manager in the context."""
        self.context.mob_manager = mob_manager
    
    def parse(self, command_str: str, player, game_state) -> List[Dict[str, Any]]:
        """
        Parse a command string into structured command objects.
        
        Args:
            command_str: The command string to parse
            player: The player object
            game_state: The game state
            
        Returns:
            A list of parsed command objects
        """
        logger.debug(f"Starting to parse command: '{command_str}'")
        
        # Handle empty commands
        if not command_str.strip():
            logger.debug("Empty command string, returning empty list")
            return []
        
        # Handle command chaining
        chained_commands = self._detect_chained_commands(command_str)
        if len(chained_commands) > 1:
            logger.debug(f"Detected chained command with {len(chained_commands)} parts")
            results = []
            for cmd in chained_commands:
                parsed = self.parse(cmd, player, game_state)
                results.extend(parsed)
            return results
        
        # Tokenize the command
        tokens = tokenize(command_str)
        if not tokens:
            logger.debug("No tokens found, returning empty list")
            return []
        
        # Special case for commands starting with a quote (say command)
        if command_str.startswith('"'):
            logger.debug("Processing quote-prefixed command as 'say'")
            cmd = {
                "verb": "say",
                "subject": command_str[1:].strip(),
                "original": command_str
            }
            return [cmd]
        
        # Check if first token might be a player name (for direct messaging)
        is_direct_message = False
        if tokens and player and game_state:
            first_token = tokens[0].value.lower()
            # Check if this matches a player name in the room
            players_in_room = get_players_in_room(player.current_room, game_state)
            for other_player in players_in_room:
                if other_player.name.lower() == first_token:
                    logger.debug(f"Detected potential direct message to player: {other_player.name}")
                    is_direct_message = True
                    break
        
        # Count total number of words for context-aware expansion
        total_words = len(tokens)
        
        # Only expand the first token (verb) - don't expand the rest of the tokens for communication commands
        if tokens:
            # Save original first token (verb)
            original_verb = tokens[0].value
            # Expand the verb (first token) with position context
            tokens[0].value = self.vocabulary.expand_word(original_verb, 0, total_words)
            expanded_verb = tokens[0].value
            logger.debug(f"Verb: '{original_verb}' -> '{expanded_verb}'")
            
            # Check if this is a communication command
            is_communication_cmd = expanded_verb in ["say", "tell", "shout", "act", "whisper"]
            
            # Only expand other tokens if this is NOT a communication command or direct message
            if not (is_communication_cmd or is_direct_message):
                # Now expand all other tokens with position context
                for i in range(1, len(tokens)):
                    original_value = tokens[i].value
                    expanded_value = self.vocabulary.expand_word(original_value, i, total_words)
                    if original_value != expanded_value:
                        tokens[i].value = expanded_value
                        logger.debug(f"Expanded token at position {i}: '{original_value}' -> '{expanded_value}'")
            
            # Handle special 'go' cases
            if original_verb.lower() == "go" and len(tokens) > 1:
                direction = tokens[1].value.lower()
                expanded_direction = self.vocabulary.expand_word(direction, 1, total_words)
                
                logger.debug(f"Checking for direction after 'go': '{direction}' -> '{expanded_direction}'")
                
                if self.vocabulary.is_direction(expanded_direction):
                    logger.debug(f"'go {direction}' is a movement command, using '{expanded_direction}'")
                    cmd = {"verb": expanded_direction, "is_movement": True, "original": command_str}
                    return [cmd]
        
        # Check for movement command (just single direction command)
        if tokens and self.vocabulary.is_direction(tokens[0].value):
            logger.debug(f"Detected simple movement command: '{tokens[0].value}'")
            cmd = {"verb": tokens[0].value, "is_movement": True, "original": command_str}
            return [cmd]
        
        # Try all command structures
        parsed_cmd = None
        
        # IMPORTANT CHANGE: Create a combined list of all syntax patterns
        all_patterns = []
        all_patterns.extend(CONTAINER_COMMAND.syntax_patterns)
        all_patterns.extend(STANDARD_SYNTAX_COMMAND.syntax_patterns)
        all_patterns.extend(REVERSED_SYNTAX_COMMAND.syntax_patterns)
        all_patterns.extend(ONE_WORD_COMMAND.syntax_patterns)
        all_patterns.extend(VERB_OBJECT_COMMAND.syntax_patterns)
        
        # Sort by priority (highest first)
        all_patterns.sort(key=lambda p: -p.priority)
        
        # Try patterns in order of priority
        for pattern in all_patterns:
            logger.debug(f"Trying pattern: '{pattern.pattern_str}' with priority {pattern.priority}")
            matched, bindings = pattern.matches(tokens)
            if matched:
                parsed_cmd = bindings
                logger.debug(f"Matched pattern '{pattern.pattern_str}' with priority {pattern.priority}: {bindings}")
                break
        
        # If no command structure matched but we have tokens, try a fallback approach
        if not parsed_cmd and tokens:
            # If we have exactly two tokens, it's most likely "VERB SUBJECT"
            if len(tokens) == 2:
                logger.debug(f"No pattern matched, but have 2 tokens. Using VERB SUBJECT fallback.")
                parsed_cmd = {
                    "verb": tokens[0].value,
                    "subject": tokens[1].value
                }
            # Otherwise just use the verb
            else:
                logger.debug(f"No command structure matched. Using verb-only default: '{tokens[0].value}'")
                parsed_cmd = {"verb": tokens[0].value}
        
        # Final fallback for parsing errors
        if not parsed_cmd:
            logger.debug("Parsing failed completely, returning empty list")
            return []
        
        # For communication commands, use the original message from the command string
        if parsed_cmd and "verb" in parsed_cmd:
            verb = parsed_cmd["verb"]
            if verb in ["say", "tell", "shout", "act", "whisper"]:
                # For "tell <player> <message>" format
                if verb == "tell" and "subject" in parsed_cmd:
                    # Extract the message part - everything after "tell player"
                    parts = command_str.split(maxsplit=2)
                    if len(parts) > 2:
                        parsed_cmd["instrument"] = parts[2]  # Use exact message
                        logger.debug(f"Using original message for tell command: {parsed_cmd['instrument']}")
                # For other communication commands
                elif "subject" in parsed_cmd:
                    # Extract the message part - everything after the verb
                    parts = command_str.split(maxsplit=1)
                    if len(parts) > 1:
                        parsed_cmd["subject"] = parts[1]  # Use exact message
                        logger.debug(f"Using original message for {verb} command: {parsed_cmd['subject']}")
        
        # Handle object binding
        logger.debug(f"Final parsed command before binding: {parsed_cmd}")
        
        # Add subject if present and not a communication command
        if "subject" in parsed_cmd and parsed_cmd["subject"]:
            # Skip binding for communication command messages
            if parsed_cmd.get("verb") not in ["say", "tell", "shout", "act", "whisper"]:
                logger.debug(f"Binding subject: {parsed_cmd['subject']}")
                parsed_cmd["subject_object"] = self.object_binder.bind_subject(
                    parsed_cmd["subject"], player, game_state, self.context
                )
        
        # Add instrument if present
        if "instrument" in parsed_cmd and parsed_cmd["instrument"]:
            # Skip binding for tell command messages
            if parsed_cmd.get("verb") != "tell":
                logger.debug(f"Binding instrument: {parsed_cmd['instrument']}")
                parsed_cmd["instrument_object"] = self.object_binder.bind_instrument(
                    parsed_cmd["instrument"], player, game_state, self.context
                )
        
        # Store the original command string
        parsed_cmd["original"] = command_str
        
        # Handle direct message special case
        if is_direct_message and not parsed_cmd.get("verb") == "tell":
            # If first token matched a player name, but wasn't parsed as a tell command
            # we'll convert it to one
            parts = command_str.split(maxsplit=1)
            recipient = parts[0]
            message = parts[1] if len(parts) > 1 else ""
            
            parsed_cmd = {
                "verb": "tell",
                "subject": recipient,
                "instrument": message,  # Use exact message
                "original": command_str,
                "is_direct_message": True
            }
            logger.debug(f"Converted to direct player message: {parsed_cmd}")
        
        # Update context with this command
        if not (is_direct_message or parsed_cmd.get("verb") in ["say", "tell", "shout", "act", "whisper"]):
            self.context.update(
                verb=parsed_cmd.get("verb"),
                subject=parsed_cmd.get("subject_object"),
                instrument=parsed_cmd.get("instrument_object")
            )
        
        logger.debug(f"Final parsed command after binding: {parsed_cmd}")
        return [parsed_cmd]
    
    def _detect_chained_commands(self, command_str: str) -> List[str]:
        """
        Detect and split chained commands.
        
        Args:
            command_str: The command string to check
            
        Returns:
            A list of individual command strings
        """
        # Split by commas, but preserve commas inside quoted strings
        pattern = r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)'
        parts = re.split(pattern, command_str)
        
        # Also split by "and" or "then" but not inside quotes
        final_parts = []
        for part in parts:
            # Split by " and " or " then "
            and_pattern = r'\s+and\s+(?=(?:[^"]*"[^"]*")*[^"]*$)'
            then_pattern = r'\s+then\s+(?=(?:[^"]*"[^"]*")*[^"]*$)'
            
            # First split by "and"
            and_parts = re.split(and_pattern, part, flags=re.IGNORECASE)
            
            # Then split each of those by "then"
            for and_part in and_parts:
                then_parts = re.split(then_pattern, and_part, flags=re.IGNORECASE)
                final_parts.extend(then_parts)
        
        # Return non-empty parts
        return [p.strip() for p in final_parts if p.strip()]

# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------

def get_players_in_room(room_id, game_state):
    """Get all players in a room."""
    players = []
    # This would need to be implemented based on your game state
    # For now, return an empty list as a placeholder
    return players

# -------------------------------------------------------------------------
# Global Instances and Exported Functions
# -------------------------------------------------------------------------

# Initialize global instances
vocabulary_manager = VocabularyManager()
natural_language_parser = NaturalLanguageParser()

# Export main parsing function
def parse_command(command_str: str, player, game_state):
    """
    Parse a command string into structured command objects.
    Main entry point for the parsing system.
    
    Args:
        command_str: The command string to parse
        player: The player object
        game_state: The game state
        
    Returns:
        A list of parsed command objects
    """
    logger.debug(f"parse_command called with: '{command_str}'")
    return natural_language_parser.parse(command_str, player, game_state)

def is_movement_command(verb: str) -> bool:
    """
    Check if a verb is a movement command.
    
    Args:
        verb: The verb to check
        
    Returns:
        True if it's a movement command, False otherwise
    """
    result = vocabulary_manager.is_direction(verb)
    logger.debug(f"is_movement_command check for '{verb}': {result}")
    return result