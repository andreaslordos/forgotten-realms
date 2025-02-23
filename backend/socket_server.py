# socket_server.py
import asyncio
import socketio
from aiohttp import web

# Set up a Socket.IO server with async_mode 'aiohttp'
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# Import your managers and command executor.
# (Assume these modules already exist and remain unchanged.)
from managers.auth import AuthManager
from managers.player import PlayerManager
from managers.game_state import GameState
from managers.map_generator import generate_3x3_grid
from commands.executor import execute_command  # must return string responses

# Initialize managers
auth_manager = AuthManager()
player_manager = PlayerManager(spawn_room="room_1_1")
game_state = GameState()

# Generate the map if not already present.
if not game_state.rooms:
    new_rooms = generate_3x3_grid()
    for room in new_rooms.values():
        game_state.add_room(room)
    from models.item import Item
    game_state.rooms["room_0_1"].add_item(Item("Sword", "A sharp steel sword.", weight=5))
    game_state.rooms["room_2_2"].add_item(Item("Shield", "A sturdy wooden shield.", weight=8))
    game_state.rooms["room_1_1"].add_item(Item("Golden Coin", "A valuable ancient coin.", weight=0.1, value=50))
    game_state.rooms["room_1_0"].add_item(Item("Emerald Gem", "A rare emerald.", weight=0.2, value=100))
    game_state.save_rooms()

# Global dictionary to track online sessions.
# Maps Socket.IO session id (sid) to a dictionary with keys: 'player', 'visited', and 'last_active'
online_sessions = {}

async def send_message(sid, message):
    await sio.emit('message', message, room=sid)

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    if sid in online_sessions:
        player = online_sessions[sid]['player']
        # On disconnect, drop all items into the current room.
        room = game_state.get_room(player.current_room)
        if room:
            for item in list(player.inventory):
                player.remove_item(item)
                room.add_item(item)
        player_manager.save_players()
        del online_sessions[sid]

@sio.event
async def login(sid, data):
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not username or not password:
        await sio.emit('loginFailure', "Username and password required", room=sid)
        return

    # Check if the player exists (login) or register.
    player = player_manager.login(username)
    if player:
        try:
            auth_manager.login(username, password)
        except Exception as e:
            await sio.emit('loginFailure', str(e), room=sid)
            return
    else:
        try:
            auth_manager.register(username, password)
        except Exception as e:
            await sio.emit('loginFailure', str(e), room=sid)
            return
        player = player_manager.register(username, email=data.get('email', ''))
    
    # Always reset player's current room to spawn on login.
    player.set_current_room(player_manager.spawn_room)
    player_manager.save_players()

    # Initialize session data.
    online_sessions[sid] = {
        'player': player,
        'visited': set(),
        'last_active': asyncio.get_event_loop().time()
    }

    # Send login success and initial room description.
    await sio.emit('loginSuccess', room=sid)
    current_room = game_state.get_room(player.current_room)
    initial_text = f"\n{current_room.name}\n{current_room.description}\n"
    for item in current_room.items:
        initial_text += f"{item.description}\n"
    initial_text += "\nEnter command:"
    await send_message(sid, initial_text)
    await broadcast_arrival(player)

@sio.event
@sio.event
async def command(sid, command_text):
    session = online_sessions.get(sid)
    if not session:
        return

    # If the player typed "users", return a list of online players
    if command_text.lower() == "users":
        online_player_names = [info['player'].name for info in online_sessions.values()]
        message = f"Online users: {', '.join(online_player_names)}"
        await send_message(sid, message)
        await send_message(sid, "Enter command:")
        return

    # Otherwise, pass this command to your existing executor
    player = session['player']
    visited = session['visited']
    response = execute_command(command_text, player, game_state, player_manager, visited)

    if response == "quit":
        await send_message(sid, "Goodbye!")
        await sio.disconnect(sid)
    else:
        await send_message(sid, response)
        await send_message(sid, "Enter command:")


async def broadcast_arrival(new_player):
    """Notify other sessions in the same room that this player has arrived."""
    room_id = new_player.current_room
    display_name = new_player.name
    for sid, session in online_sessions.items():
        other_player = session['player']
        if other_player.current_room == room_id and other_player.name != display_name:
            await send_message(sid, f"{display_name} has just arrived")

async def background_tick():
    """Background task for periodic game logic (e.g., NPC movement, combat, inactivity)."""
    while True:
        await asyncio.sleep(5)
        # (Implement any periodic updates here.)
        for sid in list(online_sessions.keys()):
            # Example: inactivity check can be implemented here.
            pass

if __name__ == '__main__':
    sio.start_background_task(background_tick)
    web.run_app(app, port=8888)
