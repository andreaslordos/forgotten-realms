# backend/tick_service.py

import asyncio
from commands.executor import execute_command
from commands.communication import handle_pending_communication
import time

async def start_background_tick(sio, online_sessions, player_manager, game_state, utils):
    print("[Tick] Background tick service starting...")
    
    # Store the last activity time for inactivity reset
    last_activity = time.time()
    
    while True:
        try:
            await asyncio.sleep(0.5)
            
            # Check for inactivity reset (2 hours)
            current_time = time.time()
            if online_sessions and (current_time - last_activity) > 7200:  # 2 hours in seconds
                print("[Tick] Triggering inactivity reset after 2 hours...")
                # TODO: Implement mid-week reset here
                last_activity = current_time
            
            if not online_sessions:
                continue
            
            for sid, session in list(online_sessions.items()):
                # Update last activity time for this session
                if session.get('command_queue') or session.get('player'):
                    last_activity = current_time
                
                if not session.get('command_queue'):
                    continue
                
                player = session.get('player')
                if not player:
                    continue
                
                responses = []
                commands = session['command_queue'][:]
                session['command_queue'].clear()
                
                for cmd in commands:
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
                            responses.append(pending_result)
                            continue
                        
                        # Check for converse mode
                        if session.get('converse_mode') and not cmd.startswith('*') and not cmd.startswith('>'):
                            # Remove converse mode if starting with ( and ending with )
                            if cmd.startswith('(') and cmd.endswith(')'):
                                cmd = cmd[1:-1]
                                session['converse_mode'] = False
                                responses.append("Converse mode OFF.")
                            else:
                                # Treat as a say command
                                cmd = f"say {cmd}"
                        
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
                        
                        responses.append(result)
                        if result == "quit":
                            session['should_disconnect'] = True
                    except Exception as e:
                        print(f"[Error] Command '{cmd}' failed for {player.name}: {str(e)}")
                        responses.append(f"Error processing command: {str(e)}")
                
                if responses:
                    try:
                        await utils.send_message(sio, sid, "\n".join(responses))
                    except Exception as e:
                        print(f"[Error] Failed to send message to {player.name}: {str(e)}")
                
                if player:
                    await utils.send_stats_update(sio, sid, player)
                
                if session.get('should_disconnect'):
                    try:
                        await sio.disconnect(sid)
                    except Exception as e:
                        print(f"[Error] Failed to disconnect {player.name}: {str(e)}")
        
        except Exception as e:
            print(f"[Error] Critical background tick error: {str(e)}")
            await asyncio.sleep(1)