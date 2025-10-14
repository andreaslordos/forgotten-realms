# AI MUD

AI MUD is a text-based multiplayer online role-playing game (MMORPG) that uses AI to generate content.

## Features

- Character creation, strict-levelling progression
- Exploration
- Combat with other players
- Inventory system
- NPCs that move around -- no need for interaction
- Game is mostly based on puzzles that when solved, will give you treasure and maybe points. The treasure can be "swamped" for points.
- As AI generates the world, that world becomes **permanent** and interactable by other players. Rooms don't tend to mutate much by AI - the AI creates the rooms, generates the rules and NPCs associated, and items, and then the room is there for other players to interact with as well
- The world will fully reset every week, starting back to an original "village" state - this village state will be defined by me
- The world that the AI generates must be internally consistent, and the AI must be able to generate believable content, and try and keep a consistent tone and storyline.

## Local Development

- **Backend**: From the `backend/` directory, install deps with `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`. Start the Socket.IO server in test mode (no SSL) with `python3 socket_server.py -test` (listens on http://localhost:8080).
- **Frontend**: From the `frontend/` directory, install deps with `npm install` and launch the React dev server with `npm start` (serves on http://localhost:3000 and proxies API traffic to the backend on 8080).

## Testing

### Running Tests

Run all backend tests with coverage:
```bash
./scripts/run_backend_tests.sh
```

Run specific test files:
```bash
python3 -m unittest backend.managers.tests.test_player -v
python3 -m unittest backend.commands.tests.test_auth -v
```

### Coverage Requirements

- **Minimum Coverage**: 80% for all files
- **Exceptions**: `socket_server.py` and `event_handlers.py` (excluded from coverage requirements)
- The pre-commit hook enforces 80% coverage and blocks commits if this threshold is not met

To check coverage manually:
```bash
python3 -m coverage erase
python3 -m coverage run --source=backend --omit='*/tests/*' -m unittest discover -s backend -p 'test_*.py'
python3 -m coverage report --fail-under=80 --sort=cover
```

### Type Checking

Run mypy for static type checking:
```bash
python3 -m mypy --ignore-missing-imports --strict . --exclude 'tests' --exclude 'venv'
```

### Test Structure

Tests follow a consistent structure:
- Each Python module has a corresponding test file: `foo.py` → `tests/test_foo.py`
- Tests are located in `tests/` subdirectories within each module (e.g., `backend/commands/tests/`, `backend/models/tests/`)
- Test functions follow the naming convention: `test_{function_name}_{description_of_test}`
- Example: `test_handle_password_validates_old_password_success`

### Pre-commit Hooks

Install developer tooling:
```bash
pip install pre-commit coverage mypy
pre-commit install
```

Pre-commit hooks will automatically run on each commit:
- **Black**: Code formatting
- **Ruff**: Linting
- **Coverage**: Ensures 80% minimum coverage
- **Test Execution**: All tests must pass

If tests fail or coverage drops below 80%, the commit will be blocked.
