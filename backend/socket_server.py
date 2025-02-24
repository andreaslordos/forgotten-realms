# socket_server.py

import asyncio
import socketio
from aiohttp import web
from datetime import datetime

# Import your existing managers and command logic.
from managers.auth import AuthManager
from managers.player import PlayerManager
from managers.game_state import GameState
from managers.map_generator import generate_3x3_grid
from commands.executor import execute_command, build_look_description

from services.notifications import set_context
from globals import online_sessions

# ------------------------------------------------------------------------------
# 1) Socket.IO and Web Application Setup
# ------------------------------------------------------------------------------

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

# If no rooms exist yet, generate a small 3x3 map.
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
# 3) Global Dictionary for Sessions (imported from globals.py)
# ------------------------------------------------------------------------------

# online_sessions is defined in globals.py

# ------------------------------------------------------------------------------
# 4) Utility Functions
# ------------------------------------------------------------------------------

async def send_message(sid, message):
    """
    Emit a 'message' event to the specific Socket.IO session.
    The React client listens for 'message' to display output lines.
    """
    await sio.emit('message', message, room=sid)

async def send_stats_update(sid, player):
    """
    Emit a 'statsUpdate' event to update the player's HUD in the client.
    """
    if not player:
        return
    stats_data = {
        "name": player.name,
        "score": player.points,
        "stamina": player.stamina,
        "max_stamina": player.max_stamina
    }
    await sio.emit("statsUpdate", stats_data, room=sid)

# Inject shared globals into the notifications module.
set_context(online_sessions, send_message)

async def broadcast_arrival(new_player):
    """
    Notify all players in the same room that `new_player` has arrived.
    """
    room_id = new_player.current_room
    display_name = new_player.name
    for sid, session_data in online_sessions.items():
        if ('player' in session_data and 
            session_data['player'] is not None and 
            session_data['player'].current_room == room_id and 
            session_data['player'] != new_player):
            await send_message(sid, f"{display_name} has just arrived")

async def post_login(sid):
    """
    Called after successful login or registration.
    Sets the player's room, sends the initial room description,
    updates stats, and broadcasts the arrival to other players.
    """
    session = online_sessions[sid]
    player = session['player']
    # Ensure the player starts at the spawn room.
    player.set_current_room(player_manager.spawn_room)
    player_manager.save_players()
    # Update last_active as current login time.
    player.last_active = datetime.now()

    # Send stats to client (so the top bar is correct).
    await send_stats_update(sid, player)

    # Build and send the initial room description.
    initial_text = build_look_description(player, game_state)
    await send_message(sid, initial_text)

    # Notify others in the room.
    await broadcast_arrival(player)

# ------------------------------------------------------------------------------
# 5) Socket.IO Event Handlers
# ------------------------------------------------------------------------------

@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] Client connected: {sid}")
    # Set up the session with an authentication state.
    online_sessions[sid] = {
        'auth_state': 'awaiting_name',  # awaiting the player's name input
        'temp_data': {},
        'command_queue': [],
        'last_active': asyncio.get_event_loop().time(),
        'visited': set(),
        'failedAttempts': 0
    }
    # Send the mystical splash message.
    MYSTICAL_SPLASH = """\
                       Forgotten Realms - Version 1.1

                      Veritas Domini manet in aeternum
    ********************************************************************
    * In the mystic twilight of forgotten ages, a realm of ancient     *
    * magic and untold legends awaits. Here, your choices echo through *
    * the halls of eternity.                                           *
    *                                                                  *
    * Are you destined to shape the fate of the realm?                 *
    ********************************************************************

Welcome! By what name shall I call you?
"""
    await send_message(sid, MYSTICAL_SPLASH)

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client disconnected: {sid}")
    if sid in online_sessions:
        session_data = online_sessions[sid]
        if 'player' in session_data:
            player = session_data['player']
            current_room = game_state.get_room(player.current_room)
            if current_room:
                for item in list(player.inventory):
                    player.remove_item(item)
                    current_room.add_item(item)
            game_state.save_rooms()
            player_manager.save_players()
        del online_sessions[sid]

@sio.event
async def command(sid, command_text):
    """
    Handles both login/registration and in-game commands via a unified terminal.
    Blank input is allowed in login mode; in game mode, blank input just produces a new prompt.
    """
    session = online_sessions.get(sid)
    if not session:
        return

    # Allow blank input by not trimming command_text.
    text = command_text

    # Integrated Login/Registration Flow
    if 'auth_state' in session:
        auth_state = session['auth_state']
        # Stage 1: Awaiting Persona Name
        if auth_state == 'awaiting_name':
            username = text
            session['temp_data']['username'] = username
            player = player_manager.login(username)
            if player:
                session['auth_state'] = 'awaiting_password'
                await send_message(sid, "This persona already exists – what's the password?")
                await sio.emit('setInputType', 'password', room=sid)
            else:
                session['auth_state'] = 'register_sex'
                await send_message(sid, "New persona detected. What is your sex? (M/F)")
            return

        # Stage 2: Awaiting Password for Existing Persona
        elif auth_state == 'awaiting_password':
            username = session['temp_data']['username']
            password = text
            try:
                auth_manager.login(username, password)
            except Exception as e:
                session['failedAttempts'] += 1
                if session['failedAttempts'] >= 3:
                    await send_message(sid, "Connection closed.")
                    await sio.disconnect(sid)
                    return
                else:
                    await send_message(sid, "Invalid password. Try again:")
                    return
            player = player_manager.login(username)
            session['player'] = player
            del session['auth_state']
            await sio.emit('setInputType', 'text', room=sid)
            # Build the custom login success message.
            masked = '*' * len(password)
            last_login = player.last_active.strftime("%H:%M:%S")
            login_message = (
                f"*{masked}\n\n"
                f"Yes!\n"
                f"Your last game was today at {last_login}.\n\n"
                f"Hello again, {player.name} the {player.level}!\n\n"
            )
            await send_message(sid, login_message)
            await post_login(sid)
            return

        # Stage 3: Registration – Ask for Sex
        elif auth_state == 'register_sex':
            sex = text.upper()
            if sex not in ['M', 'F']:
                await send_message(sid, "Invalid input. Please enter M or F:")
                return
            session['temp_data']['sex'] = sex
            session['auth_state'] = 'register_email'
            await send_message(sid, "Enter an optional email address (or leave blank):")
            return

        # Stage 4: Registration – Ask for Email
        elif auth_state == 'register_email':
            email = text if text != "" else None
            session['temp_data']['email'] = email
            session['auth_state'] = 'register_password'
            await send_message(sid, "Select a password:")
            await sio.emit('setInputType', 'password', room=sid)
            return

        # Stage 5: Registration – Enter Password
        elif auth_state == 'register_password':
            # Store the entered password and ask for confirmation.
            session['temp_data']['password'] = text
            session['auth_state'] = 'register_confirm_password'
            await send_message(sid, "Confirm your password:")
            await sio.emit('setInputType', 'password', room=sid)
            return

        # Stage 6: Registration – Confirm Password
        elif auth_state == 'register_confirm_password':
            if text != session['temp_data']['password']:
                await send_message(sid, "Passwords do not match. Please enter your password again:")
                session['auth_state'] = 'register_password'
                await sio.emit('setInputType', 'password', room=sid)
                return
            else:
                password = text
                username = session['temp_data']['username']
                sex = session['temp_data']['sex']
                email = session['temp_data']['email']
                try:
                    auth_manager.register(username, password)
                except Exception as e:
                    await send_message(sid, f"Registration failed: {str(e)}")
                    return
                player = player_manager.register(username, sex=sex, email=email)
                session['player'] = player
                del session['auth_state']
                # Build the custom registration welcome message.
                reg_message = f"Hello, {player.name} the {player.level}!\n"
                await send_message(sid, reg_message)
                await sio.emit('setInputType', 'text', room=sid)
                await post_login(sid)
                return

    # Otherwise, process as an in-game command.
    session['last_active'] = asyncio.get_event_loop().time()
    session['command_queue'].append(text)

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
            await asyncio.sleep(0.5)
            if not online_sessions:
                continue
            for sid, session_data in list(online_sessions.items()):
                cmd_queue = session_data['command_queue']
                if not cmd_queue:
                    continue
                player = session_data.get('player')
                visited = session_data.get('visited', set())
                responses = []
                commands_to_process = cmd_queue[:]
                cmd_queue.clear()
                for cmd in commands_to_process:
                    try:
                        if cmd.lower() == "users":
                            player_names = [info['player'].name for info in online_sessions.values() if 'player' in info]
                            responses.append(f"Online users: {', '.join(player_names)}")
                            continue
                        result = execute_command(cmd, player, game_state, player_manager, visited)
                        responses.append(result)
                        if result == "quit":
                            session_data['should_disconnect'] = True
                    except Exception as e:
                        print(f"[Error] Command '{cmd}' failed for {player.name if player else 'Unknown'}: {str(e)}")
                        responses.append(f"Error processing command: {str(e)}")

                # Send combined response
                if responses:
                    try:
                        await send_message(sid, "\n".join(responses))
                    except Exception as e:
                        print(f"[Error] Failed to send message to {player.name if player else 'Unknown'}: {str(e)}")

                # After processing commands, send updated stats to the client.
                if player:
                    await send_stats_update(sid, player)

                # Handle disconnect if requested
                if session_data.get('should_disconnect'):
                    try:
                        await sio.disconnect(sid)
                    except Exception as e:
                        print(f"[Error] Failed to disconnect {player.name if player else 'Unknown'}: {str(e)}")
        except Exception as e:
            print(f"[Error] Critical background tick error: {str(e)}")
            await asyncio.sleep(1)

# ------------------------------------------------------------------------------
# 7) Main Entry Point
# ------------------------------------------------------------------------------
import os
# If you're not using a CLI argument or config for port:
port = int(os.environ.get('PORT', 8080))

async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    print("Starting background task and web server...")
    await site.start()
    print(f"Server started at http://0.0.0.0:{port}")
    try:
        await background_tick()
    finally:
        await runner.cleanup()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down server...")
