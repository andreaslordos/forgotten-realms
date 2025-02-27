# backend/tick_service.py

import asyncio
from commands.executor import execute_command
from commands.communication import process_communication_command
from commands.system import process_system_command

async def start_background_tick(sio, online_sessions, player_manager, game_state, utils):
    print("[Tick] Background tick service starting...")
    while True:
        try:
            await asyncio.sleep(0.5)
            if not online_sessions:
                continue
            for sid, session in list(online_sessions.items()):
                if not session['command_queue']:
                    continue
                player = session.get('player')
                responses = []
                commands = session['command_queue'][:]
                session['command_queue'].clear()
                for cmd in commands:
                    try:
                        # First, try processing communication commands.
                        if await process_communication_command(cmd, player, session, sid, online_sessions, sio, utils):
                            continue
                        # Then, try system commands (users, help, info).
                        if await process_system_command(cmd, player, online_sessions, sio, sid, utils):
                            continue
                        # Finally, process non-communication, non-system commands normally.
                        result = execute_command(cmd, player, game_state, player_manager, session.get('visited', set()))
                        responses.append(result)
                        if result == "quit":
                            session['should_disconnect'] = True
                    except Exception as e:
                        print(f"[Error] Command '{cmd}' failed for {player.name if player else 'Unknown'}: {str(e)}")
                        responses.append(f"Error processing command: {str(e)}")
                if responses:
                    try:
                        await utils.send_message(sio, sid, "\n".join(responses))
                    except Exception as e:
                        print(f"[Error] Failed to send message to {player.name if player else 'Unknown'}: {str(e)}")
                if player:
                    await utils.send_stats_update(sio, sid, player)
                if session.get('should_disconnect'):
                    try:
                        await sio.disconnect(sid)
                    except Exception as e:
                        print(f"[Error] Failed to disconnect {player.name if player else 'Unknown'}: {str(e)}")
        except Exception as e:
            print(f"[Error] Critical background tick error: {str(e)}")
            await asyncio.sleep(1)