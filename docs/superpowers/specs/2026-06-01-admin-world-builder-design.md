# Admin World Builder Design

## Goal

Build an admin-gated world and map builder inside the existing Forgotten Realms web app. The builder lets the hardcoded admin account `stupidgem` inspect, edit, validate, apply, reset, script, commit, and push world changes through a GUI instead of changing the world entirely through Python generator code.

## Decisions

- The source of truth moves toward structured world data stored in JSON files under backend storage.
- The admin GUI lives in the existing React app at `/admin/world-builder`.
- Backend admin APIs live on the existing aiohttp Socket.IO server.
- Admin access is tied to a successful game login as `stupidgem`; the server issues an admin token only for that account.
- Map layout is hybrid: rooms can store pinned x/y/z coordinates, while the GUI can auto-place rooms without coordinates.
- The first implementation supports full-builder controls: editing rooms, exits, items, mobs, scripts, runtime apply/reset, validation, and git publish.
- GUI-authored scripts are saved as repo files and become active through normal git publish/deploy flow, not live arbitrary Python execution.

## Architecture

The backend gains a focused `backend/admin` package:

- `world_builder.py` owns the structured JSON format, serialization from live `GameState`, validation, applying JSON back to `GameState`, and file persistence.
- `routes.py` owns HTTP endpoints, CORS, admin-token checks, reset/apply/publish orchestration, and git command execution.

The existing Socket.IO login flow emits an `adminToken` event only after `stupidgem` authenticates. The React app stores this token in memory/local storage and uses it as a bearer token for admin API calls. Non-admin users can still use the game normally but cannot access admin data or actions.

The frontend gains an admin route inside `App.js`. The admin UI has a graph canvas, entity inspector, room/item/mob/script editors, validation panel, runtime controls, and publish panel. It intentionally uses simple React state and SVG/HTML controls so the feature works without adding new dependencies.

## Data Flow

1. The server starts by generating the existing Python world as it does today.
2. The admin opens `/admin/world-builder` after logging in as `stupidgem`.
3. The frontend calls `GET /admin/api/world` with the admin token.
4. The backend returns the saved draft JSON if present; otherwise it exports the live `GameState`.
5. The admin edits JSON-backed entities in the GUI.
6. `POST /admin/api/world/validate` returns blocking errors and warnings.
7. `POST /admin/api/world` saves the draft data.
8. `POST /admin/api/world/apply` validates and replaces the live room/mob state.
9. `POST /admin/api/world/reset` regenerates the Python baseline and saves/returns that snapshot.
10. `POST /admin/api/world/publish` validates, writes the draft, runs configured checks, commits, and pushes to Git.

## Runtime Controls

Runtime controls are intentionally limited to world-builder operations:

- Validate draft world.
- Save draft.
- Apply draft to live server memory.
- Reset draft/live state from the Python baseline generator.
- Publish draft to Git after validation and checks.

The GUI does not run arbitrary Python in the live process. Script editing writes files and references them from structured data so changes are reviewable and deploy through Git.

## Error Handling

Admin APIs return structured JSON errors with stable `error` strings and human-readable `message` fields. Validation returns all known errors instead of failing on the first one. Publish fails closed: if validation, tests, commit, or push fails, the response includes the failed step and captured output.

## Testing

Backend tests cover:

- Admin detection and token checks.
- Exporting a live world into structured data.
- Validating duplicate rooms, broken exits, bad item/mob references, and unreachable rooms.
- Applying structured world data back into `GameState` and `MobManager`.
- Route-level auth rejection and success paths.

Frontend tests cover:

- Rendering the game route versus admin route.
- Admin token handling.
- Loading world data.
- Editing a room and triggering save/validate/apply/publish actions.

## Scope Notes

The first implementation does not need to convert every existing custom Python puzzle into data-authored behavior. Existing custom behavior can be represented as script metadata or omitted from the structured draft until migrated. The important contract is that newly authored content has a stable JSON representation and can be validated, applied, and published.
