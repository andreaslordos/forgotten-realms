# Admin World Builder Implementation Plan

> **For agentic workers:** Use Codex parallel agents when implementation slices have disjoint write sets. Do not use the Superpowers subagent execution workflow for this plan because the user requested Codex parallel agents specifically.

**Goal:** Build the admin-gated world builder, runtime controls, and git publish flow inside the existing Forgotten Realms app.

**Architecture:** Add a backend admin package for structured world data, validation, apply/reset/publish APIs, and admin token checks. Add a React admin route for graph visualization, editors, validation, runtime controls, and publish actions. Keep the first data model JSON-based and compatible with current `Room`, `Item`, `Weapon`, and `Mobile` objects.

**Tech Stack:** Python aiohttp + Socket.IO backend, unittest backend tests, React 19 / react-scripts frontend, Jest/React Testing Library frontend tests, git CLI for publish.

---

## File Map

- Create `backend/admin/__init__.py`: admin package marker.
- Create `backend/admin/world_builder.py`: world JSON schema helpers, live export, validation, save/load, apply, reset snapshot, git publish.
- Create `backend/admin/routes.py`: aiohttp routes, CORS, bearer-token admin auth, request/response helpers.
- Modify `backend/event_handlers.py`: emit an `adminToken` event after `stupidgem` login.
- Modify `backend/socket_server.py`: register admin routes with `game_state`, `mob_manager`, `online_sessions`, and the world generator.
- Create `backend/admin/tests/test_world_builder.py`: serializer, validation, apply, and publish command tests.
- Create `backend/admin/tests/test_routes.py`: auth and route behavior tests.
- Modify `frontend/src/App.js`: route to game terminal or admin builder based on pathname, capture admin token, render admin GUI.
- Modify `frontend/src/App.css`: admin builder layout and controls.
- Modify `frontend/src/App.test.js`: admin route smoke and interaction tests.

## Backend Tasks

1. Add failing backend tests for world export, validation, save/load, and apply in `backend/admin/tests/test_world_builder.py`.
2. Implement `backend/admin/world_builder.py` with `WorldBuilder`, `ValidationIssue`, `validate_world_data`, `export_live_world`, `apply_world_data`, and persistence helpers.
3. Add failing backend route tests for unauthorized access, authorized read, validation, save, apply, reset, and publish command construction in `backend/admin/tests/test_routes.py`.
4. Implement `backend/admin/routes.py` with CORS-aware JSON endpoints and admin-token checking.
5. Modify `backend/event_handlers.py` to emit `adminToken` only for `stupidgem`.
6. Modify `backend/socket_server.py` to register admin routes.

## Frontend Tasks

1. Add failing frontend tests in `frontend/src/App.test.js` for `/admin/world-builder`, world loading, room editing, validation, and runtime button actions.
2. Refactor `frontend/src/App.js` so the existing terminal remains unchanged for normal paths and the admin builder renders only on `/admin/world-builder`.
3. Implement admin token capture from Socket.IO, API helper functions, world state loading/saving, validation, apply, reset, and publish actions.
4. Implement the SVG graph canvas, room list, selected-room inspector, room/exits/items/mobs/scripts editors, validation panel, and runtime controls.
5. Add CSS in `frontend/src/App.css` for a dense admin tool layout with stable sizing.

## Verification Tasks

1. Run targeted backend tests:
   `PYTHONPATH=backend python3 -m unittest backend.admin.tests.test_world_builder backend.admin.tests.test_routes -v`
2. Run the full backend suite if targeted tests pass:
   `./scripts/run_backend_tests.sh`
3. Run frontend tests:
   `cd frontend && npm test -- --watchAll=false`
4. Run frontend build:
   `cd frontend && npm run build`
5. Inspect `git diff --check`.

## Parallelization

- Agent A can own `backend/admin/world_builder.py` and `backend/admin/tests/test_world_builder.py`.
- Agent B can own `frontend/src/App.js`, `frontend/src/App.css`, and `frontend/src/App.test.js`.
- The main thread can own route integration in `backend/admin/routes.py`, `backend/event_handlers.py`, `backend/socket_server.py`, docs, and final integration.

These write sets are intentionally disjoint except for integration points reviewed by the main thread.
