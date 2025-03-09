#!/usr/bin/env python3
import os
import sys
import asyncio
import ssl
import socketio
from aiohttp import web
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import your managers, game state, and helper modules.
from managers.auth import AuthManager
from managers.player import PlayerManager
from managers.game_state import GameState
from managers.map_generator import generate_3x3_grid
from managers.village_generator import generate_village_of_chronos
from globals import online_sessions
from services.notifications import set_context
from event_handlers import register_handlers
from tick_service import start_background_tick
import utils  # This module contains send_message and send_stats_update

# Determine if we're in test mode (skip SSL) using a -test flag
TEST_MODE = "-test" in sys.argv

# Setup Socket.IO server and the web app.
logger.info("Initializing Socket.IO server and web app.")
sio = socketio.AsyncServer(
    async_mode='aiohttp', 
    cors_allowed_origins='*',
    ping_timeout=30,
    ping_interval=10,
    reconnection=False,
    logger=True,
    engineio_logger=True
)
app = web.Application()
sio.attach(app)

# Initialize managers and game state.
logger.info("Initializing game managers and state...")
auth_manager = AuthManager()
player_manager = PlayerManager(spawn_room="spawn")
game_state = GameState()
if not game_state.rooms:
    logger.info("No game rooms found. Generating a new 3x3 grid...")
    new_rooms = generate_village_of_chronos()
    for room in new_rooms.values():
        game_state.add_room(room)
    # game_state.save_rooms()
    logger.info("Game rooms generated and saved.")
else:
    logger.info("Game rooms loaded from existing state.")

# Set context for notifications.
set_context(online_sessions, lambda sid, msg: utils.send_message(sio, sid, msg))
logger.info("Notification context set successfully.")

# Register Socket.IO event handlers.
logger.info("Registering Socket.IO event handlers...")
register_handlers(sio, auth_manager, player_manager, game_state, online_sessions, utils)
logger.info("Socket.IO event handlers registered.")

# Determine the port.
port = int(os.environ.get('PORT', 8080))
logger.info(f"Configured to run on port: {port}")

# Setup SSL only if not in test mode.
ssl_context = None
if not TEST_MODE:
    try:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            certfile='/etc/letsencrypt/live/api.realms.lordos.tech/fullchain.pem',
            keyfile='/etc/letsencrypt/live/api.realms.lordos.tech/privkey.pem'
        )
        logger.info("🔒 Running with SSL enabled (Production Mode)")
    except Exception as e:
        logger.error(f"Failed to set up SSL: {e}")
        sys.exit(1)
else:
    logger.info("🛠 Running without SSL (Test Mode)")

async def main():
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port, ssl_context=ssl_context)
        logger.info(f"Server starting at {'https' if ssl_context else 'http'}://0.0.0.0:{port}")
        await site.start()
        
        # Start background tick in a separate task.
        asyncio.create_task(start_background_tick(sio, online_sessions, player_manager, game_state, utils))
        logger.info("Background tick service started.")
        
        # Keep the server running.
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        logger.exception("An error occurred in the main loop:")
    finally:
        await runner.cleanup()
        logger.info("Server runner cleanup complete.")

async def handle_root(request):
    logger.info("Received request on root endpoint.")
    return web.Response(text="Socket.IO server is running" + (" over HTTPS." if ssl_context else "."))

app.router.add_get('/', handle_root)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down server...")
        print("\nShutting down server...")