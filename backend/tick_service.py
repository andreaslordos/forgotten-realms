import asyncio

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
                        # Process commands, for example:
                        if cmd.lower() == "users":
                            player_names = [info['player'].name for info in online_sessions.values() if 'player' in info]
                            responses.append(f"Online users: {', '.join(player_names)}")
                            continue
                        result = execute_command(cmd, player, game_state, player_manager, session.get('visited', set()))
                        responses.append(result)
                        if result == "quit":
                            session['should_disconnect'] = True
                    except Exception as e:
                        responses.append(f"Error processing command: {str(e)}")
                if responses:
                    try:
                        await utils.send_message(sio, sid, "\n".join(responses))
                    except Exception as e:
                        print(f"[Error] Failed to send message: {str(e)}")
                if player:
                    await utils.send_stats_update(sio, sid, player)
                if session.get('should_disconnect'):
                    try:
                        await sio.disconnect(sid)
                    except Exception as e:
                        print(f"[Error] Failed to disconnect: {str(e)}")
        except Exception as e:
            print(f"[Error] Critical background tick error: {str(e)}")
            await asyncio.sleep(1)
