# backend/commands/__init__.py
from globals import online_sessions

# Set up logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.info("Initializing commands package")

# Import all command modules to ensure they register with the command registry
from commands import parser
from commands import registry
from commands import executor

# Export the main functions and objects for easy access
from commands.parser import parse_command, CommandContext
from commands.registry import command_registry
from commands.executor import execute_command, build_look_description

# Import command handlers
try:
    from commands import standard
    from commands import communication
    from commands import combat
    logger.info("All command handlers imported successfully")
except ImportError as e:
    logger.error(f"Error importing command handlers: {e}")

logger.info("Commands package initialization complete")