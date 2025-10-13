from typing import Any, List
from globals import online_sessions


def get_online_players() -> List[Any]:
    """
    Returns a list of all online players using the global SESSIONS variable.

    Returns:
        list: List of all online Player objects
    """
    online_players: List[Any] = []

    # Extract players from the global SESSIONS variable
    for session_id, session_data in online_sessions.items():
        # Check if this session has a player
        if isinstance(session_data, dict) and "player" in session_data:
            player: Any = session_data["player"]
            if player:
                online_players.append(player)
        elif hasattr(session_data, "player") and session_data.player:
            online_players.append(session_data.player)

    return online_players
