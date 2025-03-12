from globals import online_sessions

def get_online_players():
    """
    Returns a list of all online players using the global SESSIONS variable.
    
    Returns:
        list: List of all online Player objects
    """
    online_players = []
    
    # Extract players from the global SESSIONS variable
    for session_id, session_data in online_sessions.items():
        # Check if this session has a player
        if isinstance(session_data, dict) and 'player' in session_data:
            player = session_data['player']
            if player:
                online_players.append(player)
        elif hasattr(session_data, 'player') and session_data.player:
            online_players.append(session_data.player)
    
    return online_players
