# socket_server.py

import asyncio
import socketio
from aiohttp import web

# Import your existing managers and command logic.
from managers.auth import AuthManager
from managers.player import PlayerManager
from managers.game_state import GameState
from managers.map_generator import generate_3x3_grid
from commands.executor import execute_command  # Must return strings for each command.

from services.notifications import set_context
from globals import online_sessions

# ------------------------------------------------------------------------------
# 1) Socket.IO and Web Application Setup
# ------------------------------------------------------------------------------

# Create a Socket.IO server using aiohttp
# Allow your React dev server's origin (http://localhost:3000) if needed.
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',
)
app = web.Application()
sio.attach(app)

# ------------------------------------------------------------------------------
# 2) Initialize Managers / Game State
# ------------------------------------------------------------------------------

auth_manager = AuthManager()
player_manager = PlayerManager(spawn_room="room_1_1")
game_state = GameState()

# If no rooms exist yet, generate a small 3x3 map
if not game_state.rooms:
    new_rooms = generate_3x3_grid()
    for room in new_rooms.values():
        game_state.add_room(room)
    from models.item import Item
    game_state.rooms["room_0_1"].add_item(
        Item("Sword", "A sharp steel sword.", weight=5)
    )
    game_state.rooms["room_2_2"].add_item(
        Item("Shield", "A sturdy wooden shield.", weight=8)
    )
    game_state.rooms["room_1_1"].add_item(
        Item("Golden Coin", "A valuable ancient coin.", weight=0.1, value=50)
    )
    game_state.rooms["room_1_0"].add_item(
        Item("Emerald Gem", "A rare emerald.", weight=0.2, value=100)
    )
    game_state.save_rooms()

# ------------------------------------------------------------------------------
# 3) Global Dictionary to Track Sessions
# ------------------------------------------------------------------------------

# online_sessions maps sid -> {
#   'player': <Player>,
#   'visited': set(),
#   'last_active': float,
#   'command_queue': [str, ...],
#   ... (any other session data you want)
# }
# update: this is being imported from globals.py

# ------------------------------------------------------------------------------
# 4) Utility Functions
# ------------------------------------------------------------------------------

async def send_message(sid, message):
    """
    Emit a 'message' event to the specific sid (Socket.IO session).
    The React client listens for 'message' to display output lines.
    """
    await sio.emit('message', message, room=sid)

set_context(online_sessions, send_message)

async def broadcast_arrival(new_player):
    """
    Notify all players in the same room that `new_player` has arrived.
    """
    room_id = new_player.current_room
    display_name = new_player.name
    for sid, session_data in online_sessions.items():
        other_player = session_data['player']
        if other_player.current_room == room_id and other_player != new_player:
            await send_message(sid, f"{display_name} has just arrived")

# ------------------------------------------------------------------------------
# 5) Socket.IO Event Handlers
# ------------------------------------------------------------------------------

@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client disconnected: {sid}")
    if sid in online_sessions:
        session_data = online_sessions[sid]
        player = session_data['player']
        # Drop all items in the current room on disconnect
        current_room = game_state.get_room(player.current_room)
        if current_room:
            for item in list(player.inventory):
                player.remove_item(item)
                current_room.add_item(item)
        game_state.save_rooms()
        player_manager.save_players()
        del online_sessions[sid]

@sio.event
async def login(sid, data):
    """
    Handle a player's login or registration.
    Expects data: {username, password, [email]}
    """
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    email = data.get('email', '').strip() if data.get('email') else None

    if not username or not password:
        await sio.emit('loginFailure', "Username and password required", room=sid)
        return

    # Check if player exists
    player = player_manager.login(username)
    if player:
        # Existing player, check password.
        try:
            auth_manager.login(username, password)
        except Exception as e:
            await sio.emit('loginFailure', str(e), room=sid)
            return
    else:
        # Register new player.
        try:
            auth_manager.register(username, password)
        except Exception as e:
            await sio.emit('loginFailure', str(e), room=sid)
            return
        player = player_manager.register(username, email=email)

    # Reset the player's current room to the spawn room.
    player.set_current_room(player_manager.spawn_room)
    player_manager.save_players()

    # Create or update the session data.
    online_sessions[sid] = {
        'player': player,
        'visited': set(),
        'last_active': asyncio.get_event_loop().time(),
        'command_queue': []
    }

    # Notify the client of successful login.
    await sio.emit('loginSuccess', room=sid)

    # Build and send the initial room description, including other players present.
    # Import build_look_description from your executor (ensure no circular import issues).
    from commands.executor import build_look_description
    initial_text = build_look_description(player, game_state)
    await send_message(sid, initial_text)

    # Broadcast that the player has arrived to others in the room.
    await broadcast_arrival(player)


@sio.event
async def command(sid, command_text):
    """
    Instead of processing the command immediately, we enqueue it
    for processing in the 0.5s background tick.
    """
    session_data = online_sessions.get(sid)
    if not session_data:
        return  # Session doesn't exist or was disconnected

    session_data['last_active'] = asyncio.get_event_loop().time()
    session_data['command_queue'].append(command_text)


# ------------------------------------------------------------------------------
# 6) Tick-Based Processing
# ------------------------------------------------------------------------------

async def background_tick():
    """
    Runs every 0.5 seconds to process queued commands for all active sessions.
    """
    print("[Tick] Background tick service starting...")
    
    while True:
        try:
            await asyncio.sleep(0.5)  # 0.5 second interval
            
            # Skip if no active sessions
            if not online_sessions:
                continue
                
            # Process each active session
            for sid, session_data in list(online_sessions.items()):
                cmd_queue = session_data['command_queue']
                if not cmd_queue:
                    continue
                    
                player = session_data['player']
                visited = session_data['visited']
                responses = []
                
                # Process all queued commands
                commands_to_process = cmd_queue[:]
                cmd_queue.clear()
                
                for cmd in commands_to_process:
                    try:
                        if cmd.lower() == "users":
                            player_names = [info['player'].name for info in online_sessions.values()]
                            responses.append(f"Online users: {', '.join(player_names)}")
                            continue
                            
                        result = execute_command(cmd, player, game_state, player_manager, visited)
                        responses.append(result)
                        if result == "quit":
                            session_data['should_disconnect'] = True
                            
                    except Exception as e:
                        print(f"[Error] Command '{cmd}' failed for {player.name}: {str(e)}")
                        responses.append(f"Error processing command: {str(e)}")
                
                # Send combined response
                if responses:
                    try:
                        await send_message(sid, "\n".join(responses))
                    except Exception as e:
                        print(f"[Error] Failed to send message to {player.name}: {str(e)}")
                
                # Handle disconnect if requested
                if session_data.get('should_disconnect'):
                    try:
                        await sio.disconnect(sid)
                    except Exception as e:
                        print(f"[Error] Failed to disconnect {player.name}: {str(e)}")
                        
        except Exception as e:
            print(f"[Error] Critical background tick error: {str(e)}")
            await asyncio.sleep(1)  # Longer delay on critical errors


# ------------------------------------------------------------------------------
# 7) Main Entry Point
# ------------------------------------------------------------------------------

async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8888)
    
    print("Starting background task and web server...")
    await site.start()
    print("Server started at http://0.0.0.0:8888")
    
    try:
        # Run the background tick indefinitely
        await background_tick()
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down server...")
