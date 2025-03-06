import asyncio
from commands.executor import execute_command
from commands.communication import handle_pending_communication
from commands.parser import parse_command
import time
import logging
from services.notifications import broadcast_logout
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_background_tick(sio, online_sessions, player_manager, game_state, utils):
    print("[Tick] Background tick service starting...")
    logger.info("Background tick service starting")
    
    # Track last activity time (for inactivity reset)
    last_activity = time.time()
    
    while True:
        try:
            await asyncio.sleep(0.5)
            
            # Inactivity reset check (2 hours)
            current_time = time.time()
            if online_sessions and (current_time - last_activity) > 7200:
                print("[Tick] Triggering inactivity reset after 2 hours...")
                logger.info("Triggering inactivity reset after 2 hours")
                # TODO: Implement mid-week reset here
                last_activity = current_time
            
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
                    
                    # Handle converse mode
                    if session.get('converse_mode'):
                        if cmd.startswith('*') or cmd.startswith('>'):
                            session['converse_mode'] = False
                            await utils.send_message(sio, sid, "Converse mode OFF.")
                            continue
                        else:
                            # For converse mode, prepend "say" (and do no further splitting)
                            cmd = f"say {cmd}"
                    
                    # Use the parser to detect if this is a message command.
                    # For example, if the command starts with a player's name, the parser should return a "tell" command.
                    parsed_cmds = parse_command(cmd, None, session.get('players_in_room'), online_sessions)
                    is_message_cmd = False
                    if parsed_cmds:
                        # We assume the parser returns a list with one command.
                        verb = parsed_cmds[0].get("verb", "")
                        if verb in {"say", "tell", "shout", "whisper"}:
                            is_message_cmd = True
                    
                    # If not a message command and it contains chaining tokens, split it.
                    conjunctions = [" and ", " then ", ",", "."]
                    if not is_message_cmd and any(conj in cmd for conj in conjunctions):
                        # Echo the original chained command for clarity.
                        await utils.send_message(sio, sid, f"> {cmd}")
                        
                        command_parts = [cmd]
                        for conj in conjunctions:
                            new_parts = []
                            for part in command_parts:
                                new_parts.extend(part.split(conj))
                            command_parts = new_parts
                        valid_parts = [part.strip() for part in command_parts if part.strip()]
                        # Re-add the split parts to the front of the queue (in reverse order).
                        for part in reversed(valid_parts):
                            session['command_queue'].insert(0, part)
                        continue  # Process the next tick (which will process the first split command)
                    
                    # Echo the individual command before executing it.
                    await utils.send_message(sio, sid, f"{cmd}")
                    
                    # Process the command.
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
                        await broadcast_logout(player)
                    except Exception as e:
                        logger.error(f"Failed to disconnect {player.name}: {str(e)}")
                        print(f"[Error] Failed to disconnect {player.name}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Critical background tick error: {str(e)}")
            print(f"[Error] Critical background tick error: {str(e)}")
            await asyncio.sleep(1)
