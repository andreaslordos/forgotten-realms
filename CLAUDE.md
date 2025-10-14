# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Forgotten Realms is a text-based multiplayer MUD (Multi-User Dungeon) with AI-generated content. Players explore rooms, engage in combat, solve puzzles, and interact with NPCs and other players in real-time. The game world is persistent and shared across all connected players, with weekly resets to a base village state.

## Development Commands

### Running the Server

**Backend (Socket.IO server):**
```bash
cd backend
python3 socket_server.py -test    # Test mode (no SSL, http://localhost:8080)
python3 socket_server.py          # Production mode (with SSL)
```

**Frontend (React dev server):**
```bash
cd frontend
npm start                          # Serves on http://localhost:3000
```

### Testing

**Run all tests with coverage:**
```bash
./scripts/run_backend_tests.sh
```

**Run specific test file:**
```bash
python3 -m unittest backend.commands.tests.test_auth -v
python3 -m unittest backend.managers.tests.test_player -v
```

**Manual coverage check:**
```bash
python3 -m coverage erase
python3 -m coverage run --source=backend --omit='*/tests/*' -m unittest discover -s backend -p 'test_*.py'
python3 -m coverage report --fail-under=80 --sort=cover
```

### Type Checking

**Run mypy strict type checking:**
```bash
python3 -m mypy --ignore-missing-imports --strict . --exclude 'tests' --exclude 'venv'
```

### Code Quality

Pre-commit hooks enforce:
- Black (formatting)
- Ruff (linting)
- 80% minimum test coverage
- All tests must pass

## Architecture Overview

### Core Architecture Pattern

The game uses a **Socket.IO event-driven architecture** with a centralized tick service for real-time coordination:

```
Client (WebSocket) <--> Socket.IO Server <--> Event Handlers
                                                    |
                                                    v
                                    Tick Service (Background Loop)
                                                    |
                    +-------------------------------+-------------------------+
                    |                               |                         |
            Command Parser                   Combat System            Mob AI Manager
                    |                               |                         |
            Command Registry                 Combat Tick               Mob Movement
                    |                        (3s intervals)           & Interactions
            Command Handlers
        (auth, combat, communication,
         interaction, standard, etc.)
                    |
            +-------+-------+
            |               |
      Game State       Player Manager
      (Rooms)          (Players, Auth)
```

### Key Architectural Concepts

#### 1. Session-Based State Management

All connected clients have a session in `online_sessions` dict (keyed by Socket.IO `sid`):
```python
online_sessions[sid] = {
    "player": Player,              # Player object (after auth)
    "auth_state": str,             # Auth flow state
    "temp_data": dict,             # Temporary data during auth
    "command_queue": list,         # Commands awaiting processing
    "sleeping": bool,              # Player sleep state
    "pwd_change": dict,            # Password change flow state
    "pending_comm": dict,          # Pending communication state
    "converse_mode": bool,         # Auto-say mode
    "awaiting_respawn": bool,      # Death/respawn state
    "combat_death": bool,          # Whether death was from combat
    "should_disconnect": bool,     # Disconnect flag
    "last_active": float,          # Timestamp
}
```

#### 2. Tick Service (tick_service.py)

The background tick service is the **heartbeat** of the game. It runs continuously in an async loop:

- **Command Processing**: Dequeues and executes player commands from `command_queue`
- **Combat Ticks**: Processes combat actions every 3 seconds
- **Mob AI**: Updates mob positions and behaviors
- **Player States**: Handles sleeping players, stamina regeneration
- **Inactivity Detection**: Tracks player activity for potential resets

**Important**: All game actions flow through the tick service, not directly from Socket.IO event handlers.

#### 3. Command Flow

```
User Input --> Socket.IO "command" event --> Add to command_queue
                                                      |
                                                      v
                                            Tick Service dequeues
                                                      |
                                    +-----------------+-----------------+
                                    |                                   |
                            Special States?                            |
                            (sleeping, pwd_change,                     |
                            pending_comm, converse_mode)              |
                                    |                                   |
                                    v                                   v
                            Handle Special State              Parse Command
                                                                      |
                                                    +-----------------+
                                                    |
                                            Command Parser
                                    (natural_language_parser.py)
                                                    |
                                            Command Registry
                                            (registry.py)
                                                    |
                                            Command Executor
                                            (executor.py)
                                                    |
                                        Call Specific Handler
                            (auth, combat, communication, etc.)
                                                    |
                                            Return Result
                                                    |
                                        Send to Client via Socket.IO
```

#### 4. Command Registration System

Commands are registered in a global `command_registry` with:
- **Verb**: The command name (e.g., "look", "get", "attack")
- **Handler**: Async function that processes the command
- **Aliases**: Abbreviations (e.g., "l" -> "look", "n" -> "north")

Example from `commands/standard.py`:
```python
command_registry.register("look", handle_look, "Look around the current room")
command_registry.register_aliases(["l"], "look")
```

All command handlers have the signature:
```python
async def handle_command(
    cmd: Dict[str, Any],
    player: Player,
    game_state: GameState,
    player_manager: PlayerManager,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: socketio.AsyncServer,
    utils: Any,
) -> str:
```

#### 5. Game State Management

**GameState** (managers/game_state.py):
- Holds all `Room` objects in a dict (`rooms`)
- Currently persistence is disabled (commented out `save_rooms()` and `load_rooms()`)
- Rooms are generated fresh on server start via `generate_village_of_chronos()`

**PlayerManager** (managers/player.py):
- Manages player lifecycle (login, registration, save/load)
- Integrates with `AuthManager` for password handling
- Persists players to JSON files in `storage/players/`

**MobManager** (managers/mob_manager.py):
- Manages mobile NPCs (mobs) throughout the game world
- Tracks mob positions, states, and combat status
- Runs mob AI during tick service updates
- Loads mob definitions from `managers/mob_definitions.py`

#### 6. Combat System

Combat is **turn-based** with 3-second intervals:

- Initiated via `attack <target>` command or aggressive mobs
- Combat state tracked globally in `active_combat` dict
- Each combat tick (every 3s):
  - Both parties exchange attacks
  - Damage calculated based on stats and weapons
  - Combat ends on death or flee
- Death triggers respawn flow with "accept" or "disconnect" choice
- Fleeing allows escape in a random direction

See `commands/combat.py` for implementation.

#### 7. Natural Language Parser

The parser (commands/natural_language_parser.py) handles:
- Command abbreviation expansion ("l" -> "look")
- Synonym resolution ("n" -> "north")
- Multi-word parsing ("get sword from chest")
- Direct player messages ("PlayerName hello there" -> tell)
- Quoted messages ('"Hello world"' -> say)

The `VocabularyManager` maintains verbs, directions, abbreviations, and synonyms.

## Module Organization

### Backend Structure

```
backend/
├── socket_server.py           # Entry point, initializes Socket.IO server
├── event_handlers.py          # Socket.IO event handlers (connect, disconnect, command)
├── tick_service.py            # Background tick loop (command processing, combat, mob AI)
├── utils.py                   # Utility functions (send_message, send_stats_update)
├── globals.py                 # Global variables (online_sessions, version)
│
├── commands/                  # Command handlers (one file per category)
│   ├── __init__.py
│   ├── auth.py               # Password change command
│   ├── combat.py             # Attack, flee, respawn logic
│   ├── communication.py      # Say, shout, tell, yell, emote
│   ├── container.py          # Container interactions (open, close, etc.)
│   ├── executor.py           # Command execution logic
│   ├── interaction.py        # Interact with items/NPCs
│   ├── natural_language_parser.py  # Parsing and vocabulary
│   ├── parser.py             # Main parsing entry point
│   ├── player_interaction.py # Player-to-player interactions
│   ├── registry.py           # Command registration system
│   ├── rest.py               # Sleep/wake commands
│   ├── standard.py           # Look, get, drop, inventory, help, etc.
│   ├── archmage.py           # Admin/debug commands
│   └── utils.py              # Command utilities
│
├── managers/                 # Game managers
│   ├── auth.py              # Authentication (bcrypt, credentials)
│   ├── game_state.py        # Room management
│   ├── player.py            # Player lifecycle
│   ├── mob_manager.py       # Mob lifecycle and AI
│   ├── mob_definitions.py   # Mob templates
│   ├── map_generator.py     # Procedural room generation
│   └── village_generator.py # Village/spawn area generation
│
├── models/                   # Data models
│   ├── Player.py            # Player class with inventory, stats, leveling
│   ├── Room.py              # Room class with items, exits, hidden items
│   ├── Item.py              # Base item class
│   ├── ContainerItem.py     # Containers (chests, bags)
│   ├── StatefulItem.py      # Items with state (switches, levers)
│   ├── Mobile.py            # NPC/mob model
│   ├── Weapon.py            # Weapon items
│   ├── Levels.py            # Level progression tables
│   └── CombatDialogue.py    # Combat flavor text
│
└── services/                # Cross-cutting services
    ├── notifications.py     # Broadcast messages to rooms/players
    └── get_online_players.py # Query online player state
```

### Important File Relationships

- **socket_server.py** initializes everything and starts the tick service
- **event_handlers.py** handles Socket.IO events, adds commands to queue
- **tick_service.py** processes queued commands via **executor.py**
- **executor.py** routes commands to handlers in **command_registry**
- Handlers in **commands/** interact with **managers/** and **models/**

## Critical Implementation Details

### 1. Authentication Flow

Handled entirely in `event_handlers.py`:
- `auth_state` in session tracks progress: `awaiting_name` → `awaiting_password` or registration flow
- Registration: `register_sex` → `register_email` → `register_password` → `register_confirm_password`
- Password change: Multi-stage flow in `auth.py` with `pwd_change` session state
- Input type switches between `text` and `password` via `setInputType` Socket.IO event

### 2. Real-time Notifications

Use `services/notifications.py` for broadcasting:
- `broadcast_arrival(player)` - Notify room when player enters
- `broadcast_departure(room_id, player)` - Notify room when player leaves
- `broadcast_logout(player)` - Notify room when player disconnects
- `notify_room(room_id, message, exclude_player)` - Send message to all in room

### 3. Room Descriptions

Built dynamically via `build_look_description()` in `executor.py`:
- Shows room name and description (if not visited before or using "look")
- Lists visible items (from `room.get_items(game_state)`)
- Lists mobs with combat status
- Lists other players with their level and inventory summary

### 4. Hidden Items and Conditional Visibility

Rooms support hidden items that appear based on conditions:
```python
room.add_hidden_item(item, lambda game_state: some_condition(game_state))
```

Items are revealed via `room.get_items(game_state)` when condition returns True.

### 5. Player Stats and Leveling

Players level up based on points thresholds (see `models/Levels.py`):
- Gaining points triggers `player.add_points()` which checks for level-up
- Leveling updates stamina, strength, dexterity, magic, carrying capacity
- Level changes broadcast to player via Socket.IO

### 6. Mob AI and Movement

Mobs can be:
- **Stationary**: Don't move
- **Wandering**: Move randomly between connected rooms
- **Aggressive**: Attack players on sight

Mob AI runs during tick service via `mob_manager.tick_all_mobs()`.

### 7. Combat Mechanics

Combat uses:
- **Stamina** for attacks (costs stamina per attack)
- **Weapon power** for damage calculation
- **Dexterity** for hit chance
- **Combat ticks** every 3 seconds
- **Flee** command allows escape (consumes stamina)

Death results in:
- Drop all inventory in current room
- Stamina reset to 1
- Respawn prompt (accept to respawn at spawn, or disconnect to delete persona)

### 8. Special Player States

Tracked in session dict:
- **Sleeping**: Player is resting (regenerates stamina faster)
- **In Combat**: Cannot move or perform most actions
- **Awaiting Respawn**: After death, choosing to respawn or delete
- **Converse Mode**: Auto-prefixes commands with "say"
- **Password Change**: In password change flow
- **Pending Communication**: Completing a multi-stage communication command

### 9. Testing Architecture

#### Test Organization
- Each module has corresponding `tests/test_*.py` file
- Tests use `BaseCommandTest` class from `tests/test_base.py`
- Tests follow Arrange-Act-Assert pattern
- Naming: `test_{function_name}_{description_of_test}`

#### Test Class Organization

Group related tests into classes for better organization:

```python
class HandlePasswordInitializationTest(BaseCommandTest):
    """Test handle_password initialization flow."""

    async def test_handle_password_starts_password_change_flow(self):
        """Test handle_password initializes password change flow."""
        # Test implementation

    async def test_handle_password_sets_input_type_to_password(self):
        """Test handle_password sets input type to password."""
        # Test implementation


class HandlePasswordValidationTest(BaseCommandTest):
    """Test handle_password validation logic."""

    async def test_handle_password_validates_old_password_success(self):
        """Test handle_password successfully validates old password."""
        # Test implementation

    async def test_handle_password_rejects_invalid_old_password(self):
        """Test handle_password rejects invalid old password."""
        # Test implementation
```

#### Comprehensive Test Coverage

For every function, write tests covering:
1. **Happy path**: Normal operation with valid inputs
2. **Edge cases**: Boundary conditions, empty inputs, maximum values
3. **Error cases**: Invalid inputs, exceptions, error handling
4. **Integration points**: How the function interacts with other components

#### Mocking Best Practices

Use `unittest.mock` to isolate code under test:

```python
from unittest.mock import Mock, AsyncMock, patch

# Mock synchronous objects
mock_player = Mock()
mock_player.name = "TestPlayer"
mock_player.level = 5
mock_player.inventory = []

# Mock async functions
mock_sio = Mock()
mock_sio.emit = AsyncMock()
mock_utils = Mock()
mock_utils.send_message = AsyncMock()

# Patch external dependencies
with patch('commands.auth.hash_password', return_value='hashed') as mock_hash:
    result = change_password("test", "newpass")
    mock_hash.assert_called_once_with("newpass")

# Verify mock calls
mock_utils.send_message.assert_called_once()
call_args = mock_utils.send_message.call_args[0]
assert "expected text" in call_args[2]
```

#### Testing Async Functions

```python
import unittest

class AsyncTest(unittest.TestCase):
    """Test async functions."""

    async def test_async_function(self):
        """Test an async function."""
        result = await some_async_function()
        self.assertEqual(result, expected_value)
```

#### Testing Exception Handling

```python
def test_function_raises_exception_on_invalid_input(self):
    """Test function raises ValueError for invalid input."""
    with self.assertRaises(ValueError):
        function_under_test(invalid_input)

def test_function_handles_exception_gracefully(self):
    """Test function catches and handles exceptions."""
    mock_dependency = Mock()
    mock_dependency.method.side_effect = Exception("Error")

    result = function_under_test(mock_dependency)
    self.assertIn("error", result.lower())
```

#### Arrange-Act-Assert Pattern

Always structure tests clearly:

```python
async def test_handle_password_validates_old_password_success(self):
    """Test handle_password successfully validates old password."""
    # Arrange - Set up test data and mocks
    sid = "test_sid"
    self.online_sessions[sid] = {
        "player": self.player,
        "pwd_change": {
            "stage": "old_password",
            "old_password": None,
            "new_password": None,
        },
    }
    cmd = {"original": "oldpass123"}
    mock_auth = Mock()
    mock_auth.login = Mock()
    self.mock_player_manager.auth_manager = mock_auth

    # Act - Execute the function under test
    await handle_password(
        cmd,
        self.player,
        self.mock_game_state,
        self.mock_player_manager,
        self.online_sessions,
        self.mock_sio,
        self.mock_utils,
    )

    # Assert - Verify expected outcomes
    self.assertEqual(
        self.online_sessions[sid]["pwd_change"]["stage"], "new_password"
    )
    self.assertEqual(
        self.online_sessions[sid]["pwd_change"]["old_password"], "oldpass123"
    )
    mock_auth.login.assert_called_once_with(self.player.name, "oldpass123")
```

#### View Detailed Coverage

```bash
# Generate HTML coverage report
python3 -m coverage html
open htmlcov/index.html
```

### 10. Type Checking Requirements

- All functions must have type hints
- Uses `from typing import Optional, Dict, List, Any, Tuple`
- Strict mypy enforcement (except for tests and venv)
- `Any` used sparingly for complex objects (Player, Room, etc.)
- Use `Optional[T]` for nullable types
- Use `Union[T1, T2]` for multiple possible types

Example:
```python
from typing import Optional, Dict, List, Any

async def handle_command(
    cmd: Dict[str, Any],
    player: Any,
    game_state: Any,
    player_manager: Any,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    """Handle a command with proper type hints."""
    # Implementation
    return "Result"
```

## Common Development Patterns

### Adding a New Command

1. Create handler in appropriate `commands/*.py` file:
```python
async def handle_mycommand(
    cmd: Dict[str, Any],
    player: Player,
    game_state: GameState,
    player_manager: PlayerManager,
    online_sessions: Dict[str, Dict[str, Any]],
    sio: Any,
    utils: Any,
) -> str:
    # Implementation
    return "Result message"
```

2. Register in same file:
```python
from commands.registry import command_registry
command_registry.register("mycommand", handle_mycommand, "Help text")
command_registry.register_aliases(["mc"], "mycommand")
```

3. Add vocabulary if needed:
```python
from commands.natural_language_parser import vocabulary_manager
vocabulary_manager.add_verb("mycommand")
vocabulary_manager.add_synonym("mycommand", "myalias")
```

4. Write comprehensive tests in `commands/tests/test_*.py`:
```python
class HandleMyCommandTest(BaseCommandTest):
    async def test_mycommand_success(self):
        # Arrange
        cmd = {"verb": "mycommand", "subject": "test"}

        # Act
        result = await handle_mycommand(
            cmd, self.player, self.mock_game_state,
            self.mock_player_manager, self.online_sessions,
            self.mock_sio, self.mock_utils
        )

        # Assert
        self.assertIn("expected", result)
```

### Sending Messages to Players

```python
# Send to specific player
await utils.send_message(sio, sid, "Your message")

# Send stats update
await utils.send_stats_update(sio, sid, player)

# Broadcast to room (excluding player)
from services.notifications import notify_room
await notify_room(room_id, "Message", exclude_player=player.name)
```

### Accessing Player's Session

```python
# Find session ID for player
player_sid = None
for sid, session in online_sessions.items():
    if session.get("player") == player:
        player_sid = sid
        break
```

### Modifying Game State

```python
# Get current room
room = game_state.get_room(player.current_room)

# Add item to room
room.add_item(item)

# Player picks up item
success, message = player.add_item(item)
if success:
    room.remove_item(item)

# Move player to new room
old_room = game_state.get_room(player.current_room)
await broadcast_departure(old_room.room_id, player)
player.set_current_room(new_room_id)
player_manager.save_players()
await broadcast_arrival(player)
```

### Working with Mobs

```python
# Get mobs in room
mob_manager = utils.mob_manager
mobs_in_room = mob_manager.get_mobs_in_room(room_id)

# Check if mob can attack
if mob.can_attack_player():
    # Initiate combat
    from commands.combat import mob_initiate_attack
    await mob_initiate_attack(mob, player, player_sid, ...)
```

## Code Quality Standards

### Test Coverage Requirements

- **Minimum**: 80% coverage for all files
- **Exceptions**: `socket_server.py` and `event_handlers.py`
- **Enforcement**: Pre-commit hooks block commits below 80%

### Test Writing Standards

- One test file per source file: `foo.py` → `tests/test_foo.py`
- Tests in `tests/` subdirectory within each module
- Function naming: `test_{function_name}_{description}`
- Use Arrange-Act-Assert pattern
- Test happy path, edge cases, and error conditions
- Use descriptive docstrings for each test

### Type Checking Standards

- All functions must have type hints
- Use `Optional[T]` for nullable types
- Use `Dict[K, V]`, `List[T]`, `Set[T]` for collections
- Avoid `Any` except for complex game objects
- Run mypy strict mode before committing

### Pre-Commit Checklist

Before submitting any code, verify:

- [ ] All functions have complete type hints
- [ ] mypy passes with `--strict` flag
- [ ] Every function has multiple test cases covering happy path, edge cases, and error conditions
- [ ] Test names follow `test_{function_name}_{description}` convention
- [ ] Tests are in the correct `tests/` subdirectory
- [ ] Test file named `test_{source_file}.py`
- [ ] Coverage is ≥80% for all files (except `socket_server.py` and `event_handlers.py`)
- [ ] All tests pass
- [ ] Tests use Arrange-Act-Assert pattern with clear comments
- [ ] Tests have descriptive docstrings
- [ ] Pre-commit hooks are installed and passing

## Important Caveats

### Persistence is Currently Disabled

Room persistence (`save_rooms()` / `load_rooms()`) is commented out in `game_state.py`. The world is regenerated fresh on each server start. Player data **is** persisted to JSON.

### SSL Certificates are Hardcoded

Production mode expects Let's Encrypt certs at `/etc/letsencrypt/live/api.realms.lordos.tech/`. Use `-test` flag for local development.

### Global State in utils.py

`mob_manager` is attached to the `utils` module at runtime in `socket_server.py`:
```python
utils.mob_manager = mob_manager  # type: ignore[attr-defined]
```

Access it via `utils.mob_manager` or `getattr(utils, "mob_manager", None)`.

### Command Queue Processing is Sequential

Commands are processed one at a time per player during tick service. Multi-part commands (separated by "then" or ";") are re-queued for next tick.

### Combat Tick Timing is Fixed

Combat actions occur every 3 seconds (`COMBAT_TICK_INTERVAL`). This is not configurable per-combat.

## Additional Resources

- **AI Development Guide**: See `AI_DEVELOPMENT_GUIDE.md` for detailed testing and type checking instructions
- **README**: See `README.md` for setup and basic testing commands
- **Test Examples**: See `backend/commands/tests/test_auth.py` for comprehensive test patterns
