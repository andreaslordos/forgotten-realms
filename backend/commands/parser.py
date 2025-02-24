def parse_command(command_str):
    """
    Parses a movement command and returns a canonical direction if recognized.
    E.g., "n", "go north", "south" all return "north" or "south".
    Returns None if not a movement command.
    """
    command_str = command_str.strip().lower()
    tokens = command_str.split()
    movement_aliases = {
        "n": "north",
        "north": "north",
        "s": "south",
        "south": "south",
        "e": "east",
        "east": "east",
        "w": "west",
        "west": "west",
        "u": "up",
        "up": "up",
        "d": "down",
        "down": "down",
        "ne": "northeast",
        "northeast": "northeast",
        "nw": "northwest",
        "northwest": "northwest",
        "se": "southeast",
        "southeast": "southeast",
        "sw": "southwest",
        "southwest": "southwest",
        "in": "in",
        "out": "out"
    }
    
    # Remove "go" if it's the first token.
    if tokens and tokens[0] == "go":
        tokens = tokens[1:]
    if tokens and tokens[0] in movement_aliases:
        return movement_aliases[tokens[0]]
    return None

def parse_item_command(command_str):
    """
    Parses an item-related command.
    Returns a tuple (action, item_name) where:
      - 'action' is 'take' or 'drop'
      - 'item_name' is the name of the item (or special cases: 'all', 'treasure')
    Recognized formats:
      - "get [item]", "g [item]", "pickup [item]" → ('take', 'item')
      - "get all", "g all" → ('take', 'all')
      - "get t", "g t", "get treasure" → ('take', 'treasure')
      - "drop [item]", "dr [item]" → ('drop', 'item')
      - "drop all", "dr all" → ('drop', 'all')
      - "drop t", "dr t", "drop treasure" → ('drop', 'treasure')
    """
    command_str = command_str.strip().lower()
    tokens = command_str.split()

    if not tokens:
        return None, None

    if tokens[0] in ("get", "g", "pickup"):
        if len(tokens) == 1:
            return "take", None  # Missing item name
        item_name = " ".join(tokens[1:])
        if item_name in ("all", "everything"):
            return "take", "all"
        if item_name in ("t", "treasure"):
            return "take", "treasure"
        return "take", item_name
    elif tokens[0] in ("drop", "dr"):
        if len(tokens) == 1:
            return "drop", None  # Missing item name
        item_name = " ".join(tokens[1:])
        if item_name in ("all", "everything"):
            return "drop", "all"
        if item_name in ("t", "treasure"):
            return "drop", "treasure"
        return "drop", item_name

    return None, None
