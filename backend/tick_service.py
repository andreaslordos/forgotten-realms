# backend/tick_service.py

import asyncio
from commands.executor import execute_command
from commands.communication import handle_pending_communication
from commands.parser import parse_command
import time
import logging
from services.notifications import broadcast_logout

# Import the combat processing function
from commands.combat import process_combat_tick

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Combat tick interval (in seconds)
COMBAT_TICK_INTERVAL = 3.0  # Combat actions occur every 3 seconds

async def start_background_tick(sio, online_sessions, player_manager, game_state, utils):
    print("[Tick] Background tick service starting...")
    logger.info("Background tick service starting")
    
    # Track last activity time (for inactivity reset)
    last_activity = time.time()
    
    # Track last combat tick
    last_combat_tick = time.time()
    
    while True:
        try:
            await asyncio.sleep(0.5)
            
            # Inactivity reset check (30 minutes)
            current_time = time.time()
            if online_sessions and (current_time - last_activity) > (120*30):
                print("[Tick] Triggering inactivity reset after 2 hours...")
                logger.info("Triggering inactivity reset after 2 hours")
                # TODO: Implement mid-week reset here
                last_activity = current_time
            
            # Process combat ticks on their own interval
            if current_time - last_combat_tick >= COMBAT_TICK_INTERVAL:
                await process_combat_tick(sio, online_sessions, player_manager, game_state, utils)
                last_combat_tick = current_time
            
            if not online_sessions:
                continue
            
            for sid, session in list(online_sessions.items()):
                if session.get('command_queue') or session.get('player'):
                    last_activity = current_time
                
                if not session.get('command_queue') or len(session['command_queue']) == 0:
                    continue
                
                player = session.get('player')
                if not player:
                    continue
                
                # Process one command per tick
                cmd_str = session['command_queue'].pop(0)
                logger.info(f"Processing command: {cmd_str} for player {player.name}")
                
                try:
                    # Check for pending communications (add this new check for password flow)
                    if 'pwd_change' in session:
                        # We're in the middle of a password change, keep routing through the password handler
                        from commands.auth import handle_password
                        pwd_cmd = {
                            "verb": "password",
                            "original": cmd_str
                        }
                        result = await handle_password(pwd_cmd, player, game_state, player_manager, online_sessions, sio, utils)
                        if result:  # Only send if there's a message to send
                            await utils.send_message(sio, sid, result)
                        continue
                    
                    # Check for pending communications
                    if 'pending_comm' in session:
                        pending_result = await handle_pending_communication(
                            session['pending_comm'], 
                            cmd_str, 
                            player, 
                            sid, 
                            online_sessions, 
                            sio, 
                            utils
                        )
                        await utils.send_message(sio, sid, pending_result)
                        continue
                    
                    # Handle converse mode
                    if session.get('converse_mode'):
                        if cmd_str.startswith('*') or cmd_str.startswith('>'):
                            session['converse_mode'] = False
                            await utils.send_message(sio, sid, "Converse mode OFF.")
                            continue
                        else:
                            # For converse mode, prepend "say" (and do no further splitting)
                            cmd_str = f"say {cmd_str}"

                    # Set players in room for context
                    players_in_room = []
                    if online_sessions:
                        for osid, osession in online_sessions.items():
                            other_player = osession.get('player')
                            if other_player and other_player.current_room == player.current_room:
                                players_in_room.append(other_player)
                    session['players_in_room'] = players_in_room
                    
                    # Parse the command using the unified parser
                    parsed_cmds = parse_command(cmd_str, None, players_in_room, online_sessions)
                    
                    # Handle command chaining (from comma-separated commands)
                    if len(parsed_cmds) > 1:
                        # Echo the original chained command
                        await utils.send_message(sio, sid, f"{cmd_str}")
                        
                        # Process first command now
                        first_cmd = parsed_cmds[0]
                        
                        # Push the remaining commands back to the front of the queue
                        for i in range(len(parsed_cmds) - 1, 0, -1):
                            cmd_to_requeue = parsed_cmds[i].get('original', '')
                            if cmd_to_requeue:
                                session['command_queue'].insert(0, cmd_to_requeue)
                        
                        # Continue with just the first command
                        parsed_cmds = [first_cmd]
                    
                    # Get the command to process
                    cmd = parsed_cmds[0] if parsed_cmds else None
                    
                    if not cmd:
                        await utils.send_message(sio, sid, "Huh? I didn't understand that.")
                        continue
                    
                    # Echo the individual command before executing it
                    if len(parsed_cmds) <= 1:  # Only echo if not a chained command
                        await utils.send_message(sio, sid, f"{cmd.get('original', cmd_str)}")
                    
                    # Process the command
                    result = await execute_command(
                        cmd,  # Pass the parsed command object directly
                        player, 
                        game_state, 
                        player_manager, 
                        online_sessions, 
                        sio, 
                        utils
                    )
                    
                    if result:  # Only send if there's a message to send
                        await utils.send_message(sio, sid, result)
                    
                    if result == "quit":
                        session['should_disconnect'] = True
                except Exception as e:
                    logger.error(f"Command '{cmd_str}' failed for {player.name}: {str(e)}")
                    print(f"[Error] Command '{cmd_str}' failed for {player.name}: {str(e)}")
                    await utils.send_message(sio, sid, f"Error processing command: {str(e)}")
                
                # Update player stats after each command
                if player:
                    await utils.send_stats_update(sio, sid, player)
                
                if session.get('should_disconnect'):
                    try:
                        await sio.disconnect(sid)
                        await broadcast_logout(player)
                    except Exception as e:
                        logger.error(f"Failed to disconnect {player.name}: {str(e)}")
                        print(f"[Error] Failed to disconnect {player.name}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Critical background tick error: {str(e)}")
            print(f"[Error] Critical background tick error: {str(e)}")
            await asyncio.sleep(1)