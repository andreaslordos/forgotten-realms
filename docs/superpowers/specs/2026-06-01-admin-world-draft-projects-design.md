# Admin World Draft Projects Design

## Goal

Let the admin world builder manage multiple independent draft worlds while the live game world remains available and unchanged until an admin explicitly applies or publishes a selected draft.

## Current State

The admin builder currently loads and saves one file: `backend/storage/world_builder/draft_world.json`. The frontend treats that file as "the draft" and toolbar actions operate on the currently loaded world. This is simple, but it prevents safe branching: creating a new world overwrites the only authoring slot, and there is no way to work on an experimental map while keeping another draft or the live world intact.

## Alternatives Considered

Recommended: manifest-backed draft projects. Store each draft as its own JSON document and track lightweight metadata in a manifest. This keeps the current JSON world model, makes the UI easy to reason about, and avoids involving Git until Publish.

Rejected for now: Git-branch drafts. This would make publish history explicit, but it would require branch management, conflict handling, remote pushes, and admin UI around Git state before the core editor is reliable.

Rejected for now: one scratch draft plus "duplicate live" only. This is quicker, but it does not satisfy the requirement to create and work on multiple draft worlds independently.

## Data Model

Draft storage lives under `backend/storage/world_builder/`:

- `draft_world.json`: legacy compatibility path for the current primary draft.
- `drafts/manifest.json`: ordered draft project metadata.
- `drafts/<draft_id>.json`: the full world JSON for each draft project.

Draft IDs are URL-safe slugs generated from the requested name with a short suffix when needed. They are not editable after creation; display names are editable. Draft files keep the same world JSON shape already used by the editor: `version`, `spawn_room_id`, `metadata`, `regions`, `layers`, `tags`, `layout`, `rooms`, `mobs`, and `scripts`.

The manifest shape is:

```json
{
  "version": 1,
  "active_draft_id": "barovia-main",
  "drafts": [
    {
      "id": "barovia-main",
      "name": "Barovia Main",
      "source": "legacy_draft",
      "created_at": "2026-06-01T20:00:00Z",
      "updated_at": "2026-06-01T20:30:00Z",
      "room_count": 24,
      "description": "Primary production candidate"
    }
  ]
}
```

The first load migrates existing `draft_world.json` into a manifest entry named `Current Draft` if no manifest exists. If neither manifest nor legacy draft exists, the server creates an implicit `Live Baseline` draft from `export_current()`.

## Backend API

Existing endpoints keep working against the active draft for compatibility:

- `GET /admin/api/world`
- `POST /admin/api/world`
- `POST /admin/api/world/validate`
- `POST /admin/api/world/apply`
- `POST /admin/api/world/reset`
- `POST /admin/api/world/publish`

New endpoints manage projects:

- `GET /admin/api/world/drafts`: returns manifest plus active draft summary.
- `POST /admin/api/world/drafts`: creates a draft from one of `live`, `active`, or an existing `draft_id`.
- `GET /admin/api/world/drafts/{draft_id}`: loads a draft world.
- `POST /admin/api/world/drafts/{draft_id}`: validates and saves a draft world.
- `PATCH /admin/api/world/drafts/{draft_id}`: renames or updates draft description.
- `DELETE /admin/api/world/drafts/{draft_id}`: deletes a non-active draft or deletes active draft and selects a fallback.
- `POST /admin/api/world/drafts/{draft_id}/activate`: marks a draft as active for compatibility endpoints.
- `POST /admin/api/world/drafts/{draft_id}/apply`: validates, saves, and applies that draft to live runtime.
- `POST /admin/api/world/drafts/{draft_id}/publish`: validates, saves, writes/publishes that draft through the existing Git publish path.

The `WorldBuilder` facade gains a draft repository object responsible for manifest IO, path safety, draft metadata updates, and legacy migration. Validation and apply logic remain shared.

## UI

The admin toolbar gets a compact project switcher above the map controls:

- Draft selector with name, room count, and updated time.
- `New Draft` button.
- `Clone Live` button.
- `Duplicate Draft` button.
- Rename/delete actions in a small menu.
- Clear active status text: `Editing Draft: <name>` and `Live changes only after Apply Live`.

`Load World`, `Save Draft`, `Validate`, `Apply Live`, and `Publish Git` operate on the selected draft. Loading a different draft prompts only if the current draft has unsaved changes. Creating a new draft opens a small modal with draft name, optional description, and source choice.

The visual style should stay in the dungeon-crawler admin tone already established, but this feature should remain utilitarian. The switcher should feel like a ledger of arcane map folios, not a marketing card.

## Runtime Semantics

Saving a draft writes only that draft file and manifest metadata. It does not alter runtime rooms.

Applying a draft validates and saves the selected draft, then replaces runtime `GameState.rooms` and `MobManager.mobs` using the existing apply path.

Publishing a draft validates and saves the selected draft, then writes the selected draft to the canonical publish path used by Git publishing. It does not publish every draft. Other drafts remain local authoring artifacts unless explicitly published later.

Reset Baseline creates or overwrites a draft from the generated live baseline; it does not delete other drafts.

## Error Handling

All draft IDs are validated against the manifest and resolved under `backend/storage/world_builder/drafts/`; path traversal is rejected.

Saving a draft with validation errors returns the existing validation response shape. Missing drafts return `404`. A malformed manifest is treated as an admin-visible server error and does not delete files.

Deleting the final draft is not allowed. Deleting the active draft automatically activates the most recently updated remaining draft.

## Testing

Backend tests cover:

- Manifest creation from legacy `draft_world.json`.
- Creating drafts from live, active draft, and another draft.
- Loading, saving, renaming, activating, deleting, applying, and publishing draft IDs.
- Path traversal and missing draft errors.
- Compatibility endpoints operating on the active draft.

Frontend tests cover:

- Loading manifest and selected draft.
- Creating a new draft from live or current draft.
- Switching drafts without overwriting the previous draft.
- Saving one draft while another draft remains unchanged.
- Apply and Publish targeting the selected draft.
- Unsaved-change prompt when switching drafts.

## Out of Scope

This feature does not add collaborative editing, remote draft sharing, Git branch management, rollback history, or per-draft permissions. The admin gate remains hardcoded to `stupidgem`.
