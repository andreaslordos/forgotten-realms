async def send_message(sio, sid, message):
    await sio.emit('message', message, room=sid)

async def send_stats_update(sio, sid, player):
    if not player:
        return
    stats_data = {
        "name": player.name,
        "score": player.points,
        "stamina": player.stamina,
        "max_stamina": player.max_stamina
    }
    await sio.emit("statsUpdate", stats_data, room=sid)
