# backend/commands/registry.py

from commands.parser import CommandContext

class CommandRegistry:
    """
    Registry for command handlers. Serves as a central repository
    for all commands in the game.
    """
    def __init__(self):
        self.commands = {}
        self.command_context = CommandContext()
    
    def register(self, verb, handler, help_text=None):
        """
        Register a command handler.
        
        Args:
            verb (str): The command verb
            handler (callable): The function to handle the command
            help_text (str): Optional help text for the command
        """
        self.commands[verb.lower()] = {
            "handler": handler,
            "help_text": help_text or f"No help available for '{verb}'."
        }
    
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
        if target_verb.lower() not in self.commands:
            raise ValueError(f"Cannot create alias '{alias}' for unknown command '{target_verb}'")
            
        target_info = self.commands[target_verb.lower()]
        self.commands[alias.lower()] = {
            "handler": target_info["handler"],
            "help_text": f"Alias for '{target_verb}'. {target_info['help_text']}"
        }
    
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