# backend/commands/system.py

async def process_system_command(cmd, player, online_sessions, sio, sid, utils):
    """
    Processes system-level commands:
      - USERS: Lists all online users.
      - HELP: Displays help information.
      - INFO: Provides game and objective details.
    
    Returns True if the command was handled, otherwise False.
    """
    if cmd.lower() == "users":
        user_list = []
        for osid, osession in online_sessions.items():
            if 'player' in osession and osession['player']:
                user_list.append(osession['player'].name)
        message = "Online users: " + ", ".join(user_list)
        await utils.send_message(sio, sid, message)
        return True
    elif cmd.lower() == "help":
        help_text = (
            "Commands:\n"
            "  shout <message>       - Broadcasts a global shout.\n"
            "  shout                 - Prompts for a global shout message.\n"
            "  \"<message>           - Sends a message to everyone in your current room.\n"
            "  <recipient> <msg>     - Sends a private message to a specific player. (If no message is provided, you'll be prompted.)\n"
            "  users                 - Lists online users.\n"
            "  HELP                  - Displays this help information.\n"
            "  INFO                  - Provides information about the game and its objectives.\n"
            "  go <direction>        - Move in a specific direction (n, s, e, w, north, south, east, west, etc).\n"
            "  look                  - Describes your current location.\n"
            "  get <item>            - Pick up an item (also: pickup, g).\n"
            "  drop <item>           - Drop an item from your inventory (also: dr).\n"
            "  inventory or i        - Lists items in your inventory.\n"
            "  quit                  - Exit the game.\n"
        )
        await utils.send_message(sio, sid, help_text)
        return True
    elif cmd.lower() == "info":
        info_text = (
            "AI MUD: A text-based multiplayer adventure where you explore, solve puzzles, "
            "and earn treasure.\n"
            "Objective: Gain points by swamping treasure, solving puzzles, and leveling up your character.\n"
            "Explore the village, discover mysterious doors to AI-generated zones, and face various challenges.\n"
            "Player progress (levels and points) persists across weekly resets, while the world resets.\n"
        )
        await utils.send_message(sio, sid, info_text)
        return True

    return False
