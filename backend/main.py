from managers.auth import AuthManager
from managers.player import PlayerManager
from managers.game_state import GameState
from managers.map_generator import generate_3x3_grid
from commands.executor import execute_command
from models.item import Item

def main():
    # Initialize managers
    auth_manager = AuthManager()
    player_manager = PlayerManager(spawn_room="room_1_1")
    game_state = GameState()

    # Generate the map if no rooms exist in storage.
    if not game_state.rooms:
        new_rooms = generate_3x3_grid()
        for room in new_rooms.values():
            game_state.add_room(room)
        # Add items to rooms
        game_state.rooms["room_0_1"].add_item(Item("Sword", "A sharp steel sword.", weight=5))
        game_state.rooms["room_2_2"].add_item(Item("Shield", "A sturdy wooden shield.", weight=8))
        game_state.rooms["room_1_1"].add_item(Item("Golden Coin", "A valuable ancient coin.", weight=0.1, value=50))
        game_state.rooms["room_1_0"].add_item(Item("Emerald Gem", "A rare emerald.", weight=0.2, value=100))
        game_state.save_rooms()

    # Simplified login/registration
    username = input("Enter your username: ").strip()
    player = player_manager.login(username)
    if player:
        password = input("Enter your password: ").strip()
        try:
            auth_manager.login(username, password)
        except Exception as e:
            print("Login error:", e)
            return
        print(f"Welcome back, {username}!")
    else:
        print("No existing player found. Creating a new account.")
        password = input("Create a password: ").strip()
        email = input("Enter your email (optional): ").strip()
        try:
            auth_manager.register(username, password)
            print("Registration successful.")
        except Exception as e:
            print("Registration error:", e)
            return
        player = player_manager.register(username, email=email)

    player.set_current_room(player_manager.spawn_room)
    player_manager.save_players()

    # Display initial room details
    visited = set()
    current_room = game_state.get_room(player.current_room)
    print("\n" + current_room.name)
    print(current_room.description)
    for item in current_room.items:
        print(item.description)

    print("\nCommands:")
    print(" - Movement: 'n', 'go east', etc.")
    print(" - Look: 'look'")
    print(" - Exits: 'x' or 'exits'")
    print(" - Inventory: 'inv', 'i', 'inventory'")
    print(" - Take items: 'get [item]', 'g all', 'g treasure'")
    print(" - Drop items: 'drop [item]', 'dr all', 'dr t'")
    print(" - Quit: 'quit' or 'exit'")

    # Game loop
    while True:
        command = input("\nEnter command: ").strip()
        result = execute_command(command, player, game_state, player_manager, visited)
        if result == "quit":
            break

if __name__ == "__main__":
    main()
