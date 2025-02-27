# backend/socket_server.py

import os
import asyncio
import socketio
from aiohttp import web

# Import your managers, game state, and helper modules.
from managers.auth import AuthManager
from managers.player import PlayerManager
from managers.game_state import GameState
from managers.map_generator import generate_3x3_grid
from globals import online_sessions
from services.notifications import set_context
from event_handlers import register_handlers
from tick_service import start_background_tick
import utils  # This module contains send_message and send_stats_update

# Setup Socket.IO server and the web app.
sio = socketio.AsyncServer(async_mode='aiohttp', 
                          cors_allowed_origins='*',
                          ping_timeout=30,
                          ping_interval=10,
                          reconnection=False)
app = web.Application()
sio.attach(app)

# Initialize managers and game state.
auth_manager = AuthManager()
player_manager = PlayerManager(spawn_room="room_1_1")
game_state = GameState()
if not game_state.rooms:
    new_rooms = generate_3x3_grid()
    for room in new_rooms.values():
        game_state.add_room(room)
    # (Add items to rooms as needed...)
    game_state.save_rooms()

# Set context for notifications.
set_context(online_sessions, lambda sid, msg: utils.send_message(sio, sid, msg))

# Register Socket.IO event handlers.
register_handlers(sio, auth_manager, player_manager, game_state, online_sessions, utils)

# Determine the port.
port = int(os.environ.get('PORT', 8080))

async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    print(f"Server starting at http://0.0.0.0:{port}")
    await site.start()
    
    # Start background tick in a separate task.
    asyncio.create_task(start_background_tick(sio, online_sessions, player_manager, game_state, utils))
    
    # Keep the server running.
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()

async def handle_root(request):
    return web.Response(text="Socket.IO server is running.")

app.router.add_get('/', handle_root)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down server...")
