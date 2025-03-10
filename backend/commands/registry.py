# backend/commands/registry.py (Updated)

from commands.unified_parser import SyntaxPattern, CommandContext

class CommandRegistry:
    """
    Registry for command handlers. Serves as a central repository
    for all commands in the game.
    """
    def __init__(self):
        self.commands = {}
        self.command_context = CommandContext()
        self.all_aliases = {}  # Maps all aliases to their target verbs
        self.direction_aliases = {
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
        # Add directions to all_aliases
        for alias, direction in self.direction_aliases.items():
            self.all_aliases[alias] = direction
    
    def register(self, verb, handler, help_text=None, syntax_patterns=None):
        """
        Register a command handler.
        
        Args:
            verb (str): The command verb
            handler (callable): The function to handle the command
            help_text (str): Optional help text for the command
            syntax_patterns (list): Optional list of SyntaxPattern objects
        """
        verb_lower = verb.lower()
        
        # Create default syntax pattern if none provided
        if syntax_patterns is None:
            syntax_patterns = [SyntaxPattern("VERB SUBJECT")]
        
        self.commands[verb_lower] = {
            "handler": handler,
            "help_text": help_text or f"No help available for '{verb}'.",
            "patterns": syntax_patterns
        }
        
        # Add to all_aliases
        self.all_aliases[verb_lower] = verb_lower
    
    def get_handler(self, verb):
        """Get the handler for a specific verb."""
        verb = verb.lower() if verb else ""
        return self.commands.get(verb, {}).get("handler")
    
    def get_help(self, verb=None):
        """
        Get help text for a specific verb or all commands.
        
        Args:
            verb (str): Optional verb to get help for. If None, returns all help.
            
        Returns:
            str: The help text
        """
        if verb:
            verb = verb.lower()
            command_info = self.commands.get(verb)
            if command_info:
                return command_info["help_text"]
            return f"No help available for '{verb}'."
        
        # Return help for all commands
        help_text = "Available commands:\n\n"
        for v, info in sorted(self.commands.items()):
            help_text += f"{v}: {info['help_text']}\n"
        return help_text
    
    def register_alias(self, alias, target_verb):
        """
        Register an alias for an existing command.
        
        Args:
            alias (str): The alias to register
            target_verb (str): The existing command verb
        """
        alias_lower = alias.lower()
        target_lower = target_verb.lower()
        
        if target_lower not in self.commands:
            raise ValueError(f"Cannot create alias '{alias}' for unknown command '{target_verb}'")
            
        target_info = self.commands[target_lower]
        self.commands[alias_lower] = {
            "handler": target_info["handler"],
            "help_text": f"Alias for '{target_verb}'. {target_info['help_text']}",
            "patterns": target_info.get("patterns", [])
        }
        
        # Add to all_aliases
        self.all_aliases[alias_lower] = target_lower
    
    def register_aliases(self, aliases, target_verb):
        """
        Register multiple aliases for an existing command.
        
        Args:
            aliases (list): List of aliases to register
            target_verb (str): The existing command verb
        """
        for alias in aliases:
            self.register_alias(alias, target_verb)

# Global registry of commands
command_registry = CommandRegistry()