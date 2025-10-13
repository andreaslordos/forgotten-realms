# commands/registry.py (Updated)

from typing import List, Callable, Optional
from commands.natural_language_parser import vocabulary_manager


class CommandRegistry:
    """
    Registry for command handlers.

    This class is responsible for:
    - Registering command handlers
    - Retrieving handlers for specific verbs
    - Managing command aliases
    - Providing help information
    """

    def __init__(self):
        self.commands = {}
        self.command_context = None  # Initialized later by parser

        # Initialize vocabularies in the parser
        self._initialize_commands()

    def _initialize_commands(self):
        """Initialize the basic command vocabulary."""
        # Register standard movement directions
        for direction in [
            "north",
            "south",
            "east",
            "west",
            "northeast",
            "northwest",
            "southeast",
            "southwest",
            "up",
            "down",
            "in",
            "out",
        ]:
            vocabulary_manager.add_direction(direction)

    def register(self, verb: str, handler: Callable, help_text: Optional[str] = None):
        """
        Register a command handler.

        Args:
            verb: The command verb
            handler: The function to handle the command
            help_text: Optional help text for the command
        """
        verb_lower = verb.lower()

        self.commands[verb_lower] = {
            "handler": handler,
            "help_text": help_text or f"No help available for '{verb}'.",
        }

        # Add to vocabulary
        vocabulary_manager.add_verb(verb_lower)

    def get_handler(self, verb: str) -> Optional[Callable]:
        """
        Get the handler for a specific verb.

        Args:
            verb: The verb to look up

        Returns:
            The handler function or None if not found
        """
        if not verb:
            return None

        verb = verb.lower()
        # Expand abbreviations and synonyms
        verb = vocabulary_manager.expand_word(verb)

        return self.commands.get(verb, {}).get("handler")

    def get_help(self, verb: Optional[str] = None) -> str:
        """
        Get help text for a specific verb or all commands.

        Args:
            verb: Optional verb to get help for

        Returns:
            The help text
        """
        if verb:
            verb = verb.lower()
            # Expand abbreviations and synonyms
            verb = vocabulary_manager.expand_word(verb)

            command_info = self.commands.get(verb)
            if command_info:
                return command_info["help_text"]
            return f"No help available for '{verb}'."

        # Return help for all commands
        help_text = "Available commands:\n\n"
        for v, info in sorted(self.commands.items()):
            help_text += f"{v}: {info['help_text']}\n"
        return help_text

    def register_alias(self, alias: str, target_verb: str):
        """
        Register an alias for an existing command.

        Args:
            alias: The alias to register
            target_verb: The existing command verb
        """
        alias_lower = alias.lower()
        target_lower = target_verb.lower()

        if target_lower not in self.commands:
            raise ValueError(
                f"Cannot create alias '{alias}' for unknown command '{target_verb}'"
            )

        # Add abbreviation to vocabulary manager
        vocabulary_manager.add_abbreviation(alias_lower, target_lower)

    def register_aliases(self, aliases: List[str], target_verb: str):
        """
        Register multiple aliases for an existing command.

        Args:
            aliases: List of aliases to register
            target_verb: The existing command verb
        """
        for alias in aliases:
            self.register_alias(alias, target_verb)


# Global command registry instance
command_registry = CommandRegistry()
