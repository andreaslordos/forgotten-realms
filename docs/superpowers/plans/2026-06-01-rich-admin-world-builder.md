# Rich Admin World Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use focused TDD for each task. Use Codex parallel agents for disjoint backend/frontend slices. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add rich map and entity-authoring controls to the admin-gated world builder.

**Architecture:** Use `@xyflow/react` for map interaction while keeping the existing JSON world model and admin API flow. Add backend validation for authoring metadata and split frontend helpers/components where practical without destabilizing the current route.

**Tech Stack:** Python aiohttp/unittest backend, React 19 / CRA frontend, `@xyflow/react`, Jest/React Testing Library.

---

## File Map

- Modify `backend/admin/world_builder.py`: metadata validation and publish check parsing.
- Modify `backend/admin/tests/test_world_builder.py`: backend validation and publish parsing tests.
- Modify `backend/admin/routes.py` and `backend/admin/tests/test_routes.py`: route validation coverage if needed.
- Modify `backend/socket_server.py`: publish check default if needed.
- Modify `frontend/package.json` and `frontend/package-lock.json`: add `@xyflow/react`.
- Modify `frontend/src/App.js`: React Flow map, selection model, typed editors, regions/layers/layout actions.
- Modify `frontend/src/App.css`: rich builder layout and React Flow node styling.
- Modify `frontend/src/App.test.js`: frontend behavior tests.

## Tasks

### Task 1: Backend Metadata Validation

- [ ] Add failing tests for regions/layers/tags/layout metadata.
- [ ] Implement stable validation errors and compatibility warnings.
- [ ] Add failing test for env-assignment publish checks.
- [ ] Fix publish check execution.
- [ ] Run backend admin tests.

### Task 2: React Flow Dependency

- [ ] Install `@xyflow/react`.
- [ ] Import React Flow CSS in the frontend entry surface.
- [ ] Verify build resolves the dependency.

### Task 3: Frontend Rich Map Tests

- [ ] Add failing tests for React Flow canvas rendering loaded rooms.
- [ ] Add failing tests for dragging/moving a room and saving updated coordinates.
- [ ] Add failing tests for multi-select and bulk region/layer edit.
- [ ] Add failing tests for layer filtering and layout actions.

### Task 4: Frontend Map Implementation

- [ ] Replace static SVG graph with React Flow nodes/edges.
- [ ] Store `selectedRoomIds` with a primary selected room.
- [ ] Wire node drag stop to update `room.layout.x/y` and legacy `room.x/y`.
- [ ] Add minimap, controls, background, pan/zoom, and selection.
- [ ] Add layout action toolbar.

### Task 5: Frontend Rich Editors

- [ ] Add region/layer/tag management controls.
- [ ] Replace room section JSON blobs with typed exits/items/mobs/scripts editors.
- [ ] Keep raw JSON fallback editors.
- [ ] Preserve unknown backend-authored fields through normalize/edit/save.

### Task 6: Verification

- [ ] Run focused backend admin tests.
- [ ] Run full backend test suite.
- [ ] Run frontend tests.
- [ ] Run frontend build.
- [ ] Run compile/import/diff hygiene checks.
- [ ] Inspect final git status and report changed files.
