# backend/event_handlers.py

"""
event_handlers.py

This module registers the Socket.IO event handlers for the AI MUD.
It handles connection/disconnection, the authentication flow,
and dispatches in-game commands.
"""

import asyncio
from datetime import datetime
from commands.executor import build_look_description, execute_command
from commands.combat import handle_combat_disconnect, is_in_combat
from services.notifications import broadcast_arrival, broadcast_departure, broadcast_logout
import re
from globals import version

def register_handlers(sio, auth_manager, player_manager, game_state, online_sessions, utils):
    """
    Registers all Socket.IO event handlers.
    
    Parameters:
      sio: The Socket.IO AsyncServer instance.
      auth_manager: The authentication manager.
      player_manager: The player manager.
      game_state: The game state manager.
      online_sessions: A dict holding all active sessions.
      utils: A namespace with utility functions like send_message and send_stats_update.
             (These functions should have the signatures:
               send_message(sio, sid, message) and
               send_stats_update(sio, sid, player))
    """

    async def post_login(sid, player):
        """
        Called after a successful login or registration.
        Ensures the player is set to the spawn room, sends updated stats,
        sends the initial room description, and broadcasts the player's arrival.
        """
        # Ensure the player starts at the spawn room.
        player.set_current_room(player_manager.spawn_room)
        player.visited = set()
        player_manager.save_players()
        player.last_active = datetime.now()

        # Send updated stats to the client.
        await utils.send_stats_update(sio, sid, player)

        # Build and send the initial room description.
        initial_text = build_look_description(player, game_state, online_sessions=online_sessions)
        await utils.send_message(sio, sid, initial_text)

        # Notify other players in the room.
        await broadcast_arrival(player)

    async def process_auth_flow(sid, command_text, session):
        """
        Processes the authentication/registration flow.
        Depending on the current auth state, this function guides the user
        through login or registration and then calls post_login on success.
        """
        # Stage 1: Awaiting Persona Name
        if session['auth_state'] == 'awaiting_name':
            username = command_text.strip()
            if len(username) == 0:
                await utils.send_message(sio, sid, "Invalid input. Please enter a name.")
                return

            # Validate: Only ASCII letters and digits, length 2-20.
            if not re.match(r"^[A-Za-z0-9]{2,20}$", username):
                await utils.send_message(sio, sid, 
                    "Invalid username. Use only letters and numbers, 2 to 20 characters long, with no punctuation.")
                return

            # Check against reserved commands.
            reserved_commands = {"shout", "help", "info", "users", "look", "get", "drop", "inventory", "quit",
                                "n", "s", "e", "w", "north", "south", "east", "west", "levels", "out", "in"}
            if username.lower() in reserved_commands:
                await utils.send_message(sio, sid, 
                    "That username is reserved. Please choose a different name.")
                return

            session['temp_data']['username'] = username
            player = player_manager.login(username)
            if player:
                session['auth_state'] = 'awaiting_password'
                await utils.send_message(sio, sid, "This persona already exists – what's the password?")
                await sio.emit('setInputType', 'password', room=sid)
            else:
                session['auth_state'] = 'register_sex'
                await utils.send_message(sio, sid, "New persona detected. What is your sex? (M/F)")
            return

        # Stage 2: Awaiting Password for Existing Persona
        elif session['auth_state'] == 'awaiting_password':
            username = session['temp_data']['username']
            password = command_text.strip()
            try:
                auth_manager.login(username, password)
            except Exception as e:
                session['failedAttempts'] += 1
                if session['failedAttempts'] >= 3:
                    await utils.send_message(sio, sid, "Connection closed.")
                    await sio.disconnect(sid)
                    return
                else:
                    await utils.send_message(sio, sid, "Invalid password. Try again:")
                    return
            player = player_manager.login(username)
            session['player'] = player
            del session['auth_state']
            await sio.emit('setInputType', 'text', room=sid)
            last_login = player.last_active.strftime("%H:%M:%S")
            login_message = (f"\n\n"
                             f"Yes!\n"
                             f"Your last game was today at {last_login}.\n\n"
                             f"Hello again, {player.name} the {player.level}!\n\n")
            await utils.send_message(sio, sid, login_message)
            await post_login(sid, player)
            return

        # Stage 3: Registration – Ask for Sex
        elif session['auth_state'] == 'register_sex':
            sex = command_text.strip().upper()
            if sex not in ['M', 'F']:
                await utils.send_message(sio, sid, "Invalid input. Please enter M or F:")
                return
            session['temp_data']['sex'] = sex
            session['auth_state'] = 'register_email'
            await utils.send_message(sio, sid, "Enter an optional email address (or leave blank):")
            return

        # Stage 4: Registration – Ask for Email
        elif session['auth_state'] == 'register_email':
            email = command_text.strip() if command_text.strip() != "" else None
            session['temp_data']['email'] = email
            session['auth_state'] = 'register_password'
            await utils.send_message(sio, sid, "Select a password:")
            await sio.emit('setInputType', 'password', room=sid)
            return
        
        # Stage 5: Registration – Enter Password
        elif session['auth_state'] == 'register_password':
            password = command_text.strip()
            # Don't allow blank passwords
            if not password:
                await utils.send_message(sio, sid, "Password cannot be blank. Please enter a password:")
                await sio.emit('setInputType', 'password', room=sid)
                return
            
            session['temp_data']['password'] = password
            session['auth_state'] = 'register_confirm_password'
            await utils.send_message(sio, sid, "Confirm your password:")
            await sio.emit('setInputType', 'password', room=sid)
            return

        # Stage 6: Registration – Confirm Password
        elif session['auth_state'] == 'register_confirm_password':
            confirm_password = command_text.strip()
            # Don't allow blank confirmation passwords
            if not confirm_password:
                await utils.send_message(sio, sid, "Password confirmation cannot be blank. Please confirm your password:")
                await sio.emit('setInputType', 'password', room=sid)
                return
                
            if confirm_password != session['temp_data']['password']:
                await utils.send_message(sio, sid, "Passwords do not match. Please enter your password again:")
                session['auth_state'] = 'register_password'
                await sio.emit('setInputType', 'password', room=sid)
                return
            else:
                password = confirm_password
                username = session['temp_data']['username']
                sex = session['temp_data']['sex']
                email = session['temp_data']['email']
                try:
                    auth_manager.register(username, password)
                except Exception as e:
                    await utils.send_message(sio, sid, f"Registration failed: {str(e)}")
                    return
                player = player_manager.register(username, sex=sex, email=email)
                session['player'] = player
                del session['auth_state']
                reg_message = f"Hello, {player.name} the {player.level}!\n"
                await utils.send_message(sio, sid, reg_message)
                await sio.emit('setInputType', 'text', room=sid)
                await post_login(sid, player)
                return

    @sio.event
    async def connect(sid, environ, auth):
        """
        Handles a new client connection.
        Sets up the session and sends the introductory splash message.
        """
        print(f"[Socket.IO] Client connected: {sid}")
        online_sessions[sid] = {
            'auth_state': 'awaiting_name',
            'temp_data': {},
            'command_queue': [],
            'last_active': asyncio.get_event_loop().time(),
            'failedAttempts': 0
        }
        MYSTICAL_SPLASH = f"""\
                  Forgotten Realms - Version {version}

                  Veritas Domini manet in aeternum
********************************************************************
* In the mystic twilight of forgotten ages, a realm of ancient     *
* magic and untold legends awaits. Here, your choices echo through *
* the halls of eternity.                                           *
*                                                                  *
* Are you destined to shape the fate of this forgotten realm?      *
********************************************************************

Welcome! By what name shall I call you?
"""
        await utils.send_message(sio, sid, MYSTICAL_SPLASH)

    @sio.event
    async def disconnect(sid):
        """
        Handles client disconnection.
        Returns any carried items to the current room and cleans up session data.
        Also handles combat disconnection scenario.
        """
        print(f"[Socket.IO] Client disconnected: {sid}")
        if sid in online_sessions:
            session = online_sessions[sid]
            if 'player' in session:
                player = session['player']
                
                # Check if the player is in combat
                if is_in_combat(player.name):
                    # Handle combat disconnection before normal cleanup
                    await handle_combat_disconnect(
                        player.name, 
                        online_sessions, 
                        player_manager, 
                        game_state, 
                        sio, 
                        utils
                    )
                
                # Normal disconnection cleanup
                current_room = game_state.get_room(player.current_room)
                if current_room:
                    for item in list(player.inventory):
                        player.remove_item(item)
                        current_room.add_item(item)
                # game_state.save_rooms()
                player_manager.save_players()
                
                # Broadcast logout to room
                await broadcast_logout(player)
            
            # Remove the session
            del online_sessions[sid]

    @sio.event
    async def command(sid, command_text):
        """
        Handles all commands from a client.
        Routes authentication commands if needed; otherwise, queues in-game commands.
        """
        session = online_sessions.get(sid)
        if not session:
            return

        if 'auth_state' in session:
            await process_auth_flow(sid, command_text, session)
        else:
            session['last_active'] = asyncio.get_event_loop().time()            
            # Add command to the queue for processing
            session['command_queue'].append(command_text)
