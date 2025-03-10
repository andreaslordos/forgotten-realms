# backend/commands/__init__.py

from globals import online_sessions

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Initializing commands package")

# Import core modules first
from commands import registry
from commands import unified_parser

# Register the command registry with the default parser
unified_parser.default_parser.registry = registry.command_registry

# Import remaining modules
from commands import parser
from commands import executor
from commands import utils

# Export the main functions and objects for easy access
from commands.parser import parse_command, CommandContext
from commands.registry import command_registry
from commands.executor import execute_command, build_look_description

# Export unified parser components
from commands.unified_parser import (
    CommandParser, 
    SyntaxPattern,
    create_default_parser
)

# Import command handlers
try:
    from commands import standard
    from commands import communication
    from commands import combat
    from commands import container
    from commands import interaction
    from commands import auth
    from commands import archmage
    logger.info("All command handlers imported successfully")
except ImportError as e:
    logger.error(f"Error importing command handlers: {e}")

logger.info("Commands package initialization complete")