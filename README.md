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
- **Tests**: Run the deterministic tick service tests with `python3 -m unittest -v backend.tests.test_tick_service`. Additional Python tests can be discovered with `python3 -m unittest` from the repo root.
- **Tooling**: Install developer tooling with `pip install pre-commit coverage` and enable hooks via `pre-commit install`. Commits will run formatting (Black), linting (Ruff), and block if backend coverage from `scripts/run_backend_tests.sh` drops below 80% or if any tests fail.
test change
