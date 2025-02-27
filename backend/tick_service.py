# backend/tick_service.py

import asyncio
from commands.executor import execute_command
from commands.communication import handle_pending_communication
from commands.parser import parse_command_string
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_background_tick(sio, online_sessions, player_manager, game_state, utils):
    print("[Tick] Background tick service starting...")
    logger.info("Background tick service starting")
    
    # Store the last activity time for inactivity reset
    last_activity = time.time()
    
    while True:
        try:
            await asyncio.sleep(0.5)
            
            # Check for inactivity reset (2 hours)
            current_time = time.time()
            if online_sessions and (current_time - last_activity) > 7200:  # 2 hours in seconds
                print("[Tick] Triggering inactivity reset after 2 hours...")
                logger.info("Triggering inactivity reset after 2 hours")
                # TODO: Implement mid-week reset here
                last_activity = current_time
            
            if not online_sessions:
                continue
            
            for sid, session in list(online_sessions.items()):
                # Update last activity time for this session
                if session.get('command_queue') or session.get('player'):
                    last_activity = current_time
                
                if not session.get('command_queue') or len(session['command_queue']) == 0:
                    continue
                
                player = session.get('player')
                if not player:
                    continue
                
                # Process only one command per tick
                cmd = session['command_queue'].pop(0)
                logger.info(f"Processing command: {cmd} for player {player.name}")
                
                try:
                    # Check for pending communications
                    if 'pending_comm' in session:
                        pending_result = await handle_pending_communication(
                            session['pending_comm'], 
                            cmd, 
                            player, 
                            sid, 
                            online_sessions, 
                            sio, 
                            utils
                        )
                        await utils.send_message(sio, sid, pending_result)
                        continue
                    
                    # Check for converse mode
                    if session.get('converse_mode'):
                        # Check for exit commands (* or >)
                        if cmd.startswith('*') or cmd.startswith('>'):
                            session['converse_mode'] = False
                            await utils.send_message(sio, sid, "Converse mode OFF.")
                            continue
                        else:
                            # Simply treat as a say command (no more parentheses parsing)
                            cmd = f"say {cmd}"
                    
                    # If this is a chained command (contains "and", "then", etc.), split it and add parts back to queue
                    if any(conj in cmd for conj in [" and ", " then ", ",", "."]):
                        # First, send the original command as an echo for clarity
                        await utils.send_message(sio, sid, f"> {cmd}")
                        
                        # Split the command and add parts back to the queue (in reverse to maintain order)
                        conjunctions = [" and ", " then ", ",", "."]
                        command_parts = [cmd]
                        for conj in conjunctions:
                            new_parts = []
                            for part in command_parts:
                                new_parts.extend(part.split(conj))
                            command_parts = new_parts
                        
                        # Remove empty parts and add valid ones back to the queue
                        valid_parts = [part.strip() for part in command_parts if part.strip()]
                        # Add in reverse order so they'll be processed in the correct order
                        for part in reversed(valid_parts):
                            session['command_queue'].insert(0, part)
                        
                        # Skip further processing this tick
                        continue
                    
                    # Echo the individual command before executing it
                    await utils.send_message(sio, sid, f"{cmd}")
                    
                    # Process the command
                    result = await execute_command(
                        cmd, 
                        player, 
                        game_state, 
                        player_manager, 
                        session.get('visited', set()), 
                        online_sessions, 
                        sio, 
                        utils
                    )
                    
                    # Send the result immediately
                    await utils.send_message(sio, sid, result)
                    
                    if result == "quit":
                        session['should_disconnect'] = True
                except Exception as e:
                    logger.error(f"Command '{cmd}' failed for {player.name}: {str(e)}")
                    print(f"[Error] Command '{cmd}' failed for {player.name}: {str(e)}")
                    await utils.send_message(sio, sid, f"Error processing command: {str(e)}")
                
                # Update player stats after each command
                if player:
                    await utils.send_stats_update(sio, sid, player)
                
                if session.get('should_disconnect'):
                    try:
                        await sio.disconnect(sid)
                    except Exception as e:
                        logger.error(f"Failed to disconnect {player.name}: {str(e)}")
                        print(f"[Error] Failed to disconnect {player.name}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Critical background tick error: {str(e)}")
            print(f"[Error] Critical background tick error: {str(e)}")
            await asyncio.sleep(1)