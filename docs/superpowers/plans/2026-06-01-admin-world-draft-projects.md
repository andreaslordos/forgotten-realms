# Admin World Draft Projects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manifest-backed draft projects to the admin world builder so admins can create, switch, save, apply, and publish independent draft worlds while live runtime remains unchanged until Apply Live.

**Architecture:** Add a focused draft-project store inside `backend/admin/world_builder.py` and expose it through `WorldBuilder` plus admin routes. The frontend keeps a selected `draftId`, loads the manifest, and routes Save/Validate/Apply/Publish to the selected draft while preserving legacy `/admin/api/world` compatibility through the active draft.

**Tech Stack:** Python 3.11/aiohttp/unittest backend, React 19/CRA/Jest/React Testing Library frontend, existing JSON world model.

---

## File Map

- Modify `backend/admin/world_builder.py`: add `DraftWorldStore`, draft metadata helpers, WorldBuilder draft methods, and active-draft compatibility.
- Modify `backend/admin/tests/test_world_builder.py`: add storage/facade tests for migration, create/load/save/rename/delete/activate/apply/publish.
- Modify `backend/admin/routes.py`: add draft endpoints and controller handlers.
- Modify `backend/admin/tests/test_routes.py`: add draft API tests against `FakeWorldBuilder`.
- Modify `frontend/src/App.js`: add draft manifest state, project switcher controls, unsaved-change tracking, and draft-targeted actions.
- Modify `frontend/src/App.test.js`: add frontend tests for manifest loading, creating/switching/saving drafts, and selected-draft apply/publish.
- Modify `frontend/src/App.css`: add compact draft switcher styling.

## Task 1: Backend Draft Store

**Files:**
- Modify: `backend/admin/world_builder.py`
- Test: `backend/admin/tests/test_world_builder.py`

- [ ] **Step 1: Write failing tests for migration and CRUD**

Add tests like:

```python
def test_draft_store_migrates_legacy_draft_and_saves_independent_drafts(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "world_builder"
        legacy_path = root / "draft_world.json"
        save_world_data({"version": 1, "rooms": [{"id": "legacy"}], "mobs": []}, legacy_path)

        builder = WorldBuilder(
            game_state=GameState(),
            mob_manager=MobManager(),
            data_path=legacy_path,
            repo_path=tmpdir,
            spawn_room_id="legacy",
        )

        manifest = builder.list_drafts()
        self.assertEqual(manifest["active_draft_id"], "current-draft")
        self.assertEqual(manifest["drafts"][0]["name"], "Current Draft")
        self.assertEqual(builder.load_draft("current-draft")["rooms"][0]["id"], "legacy")

        created = builder.create_draft(name="Experiment", source="active")
        builder.save_draft(created["draft"]["id"], {"version": 1, "rooms": [{"id": "experiment"}], "mobs": []})

        self.assertEqual(builder.load_draft("current-draft")["rooms"][0]["id"], "legacy")
        self.assertEqual(builder.load_draft(created["draft"]["id"])["rooms"][0]["id"], "experiment")
```

Add a path-safety test:

```python
def test_draft_store_rejects_unknown_or_unsafe_draft_ids(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        builder = WorldBuilder(
            game_state=GameState(),
            mob_manager=MobManager(),
            data_path=Path(tmpdir) / "world_builder" / "draft_world.json",
            repo_path=tmpdir,
            spawn_room_id="square",
        )
        with self.assertRaises(KeyError):
            builder.load_draft("../bad")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=backend python3 -m unittest backend.admin.tests.test_world_builder.WorldBuilderFacadeTests -v`

Expected: failures because `WorldBuilder.list_drafts`, `create_draft`, `load_draft`, and `save_draft` do not exist.

- [ ] **Step 3: Implement draft storage**

Add:

```python
DRAFT_MANIFEST_VERSION = 1

@dataclass
class DraftSummary:
    id: str
    name: str
    source: str
    created_at: str
    updated_at: str
    room_count: int = 0
    description: str = ""

class DraftWorldStore:
    def __init__(self, *, data_path: PathLike, export_current: Callable[[], JsonDict]) -> None:
        self.legacy_path = Path(data_path)
        self.root = self.legacy_path.parent
        self.drafts_dir = self.root / "drafts"
        self.manifest_path = self.drafts_dir / "manifest.json"
        self.export_current = export_current
```

Implement methods with these responsibilities:

- `list()` returns the persisted manifest after migration/initialization.
- `ensure_manifest()` creates `drafts/manifest.json` from `draft_world.json` or `export_current()`.
- `load(draft_id=None)` loads the requested draft, or the active draft when `draft_id` is absent.
- `create(name, source, source_draft_id, description)` writes a new draft copied from live/current/source draft and returns `{"draft": summary, "world": world_data, "manifest": manifest}`.
- `save(draft_id, world_data)` writes the draft JSON, updates `updated_at` and `room_count`, mirrors active saves to `draft_world.json`, and returns `{"path": str(path), "draft": summary, "manifest": manifest}`.
- `rename(draft_id, name, description)` updates manifest metadata only.
- `delete(draft_id)` removes the draft file, refuses to delete the final draft, and activates the most recently updated remaining draft if needed.
- `activate(draft_id)` sets `active_draft_id` and mirrors that draft to `draft_world.json`.

Use `datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")` for timestamps. Generate slugs with lowercase alphanumerics and hyphens; append `-2`, `-3`, and so on for collisions. Resolve draft file paths only from manifest IDs.

- [ ] **Step 4: Wire WorldBuilder facade**

Add:

```python
self.drafts = DraftWorldStore(data_path=self.data_path, export_current=self.export_current)
```

Update compatibility methods:

```python
def load_or_export(self) -> JsonDict:
    return self.drafts.load()

def save(self, world_data: Mapping[str, Any]) -> JsonDict:
    result = self.drafts.save(None, world_data)
    script_paths = save_script_files(world_data, self.repo_path)
    return {**result, "scripts": [str(path) for path in script_paths]}
```

Add draft-specific methods:

```python
def list_drafts(self) -> JsonDict: return self.drafts.list()
def create_draft(self, *, name: str, source: str = "active", source_draft_id: Optional[str] = None, description: str = "") -> JsonDict:
    return self.drafts.create(name=name, source=source, source_draft_id=source_draft_id, description=description)
def load_draft(self, draft_id: str) -> JsonDict:
    return self.drafts.load(draft_id)
def save_draft(self, draft_id: str, world_data: Mapping[str, Any]) -> JsonDict:
    return self.drafts.save(draft_id, world_data)
def rename_draft(self, draft_id: str, *, name: Optional[str] = None, description: Optional[str] = None) -> JsonDict:
    return self.drafts.rename(draft_id, name=name, description=description)
def delete_draft(self, draft_id: str) -> JsonDict:
    return self.drafts.delete(draft_id)
def activate_draft(self, draft_id: str) -> JsonDict:
    return self.drafts.activate(draft_id)
def apply_draft(self, draft_id: str, world_data: Mapping[str, Any]) -> ValidationResult:
    self.drafts.save(draft_id, world_data)
    return self.apply(world_data)
def publish_draft(self, draft_id: str, world_data: Mapping[str, Any], *, checks=None, message=None) -> PublishResult:
    self.drafts.save(draft_id, world_data)
    return self.publish(world_data, checks=checks, message=message)
```

- [ ] **Step 5: Run backend facade tests**

Run: `PYTHONPATH=backend python3 -m unittest backend.admin.tests.test_world_builder.WorldBuilderFacadeTests -v`

Expected: all facade tests pass.

## Task 2: Backend Draft Routes

**Files:**
- Modify: `backend/admin/routes.py`
- Test: `backend/admin/tests/test_routes.py`

- [ ] **Step 1: Write failing route tests**

Extend `FakeWorldBuilder` with draft methods and add tests like:

```python
async def test_draft_routes_create_load_save_and_activate(self):
    response = await self.controller.list_world_drafts(self.request())
    self.assertEqual(response.status, 200)

    create = await self.controller.create_world_draft(self.request({
        "name": "Experiment",
        "source": "active",
    }))
    self.assertEqual(create.status, 200)
    draft_id = self.decode(create)["draft"]["id"]

    save = await self.controller.save_world_draft(self.request({
        "world": {"version": 1, "rooms": [{"id": "experiment"}], "mobs": []}
    }), draft_id)
    self.assertEqual(save.status, 200)

    activate = await self.controller.activate_world_draft(self.request(), draft_id)
    self.assertEqual(activate.status, 200)
```

Add error coverage:

```python
async def test_draft_routes_return_404_for_missing_draft(self):
    self.builder.load_draft = Mock(side_effect=KeyError("missing"))
    response = await self.controller.get_world_draft(self.request(), "missing")
    self.assertEqual(response.status, 404)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=backend python3 -m unittest backend.admin.tests.test_routes.AdminRouteControllerTest -v`

Expected: failures because draft route handlers do not exist.

- [ ] **Step 3: Add controller handlers**

Add handler methods named `list_world_drafts`, `create_world_draft`, `get_world_draft`, `save_world_draft`, `update_world_draft`, `delete_world_draft`, `activate_world_draft`, `apply_world_draft`, and `publish_world_draft`.

Each handler starts with `_require_admin`. Save/apply/publish handlers call `_read_world`, validate with `world_builder.validate`, and return the same validation error shape as existing endpoints. Wrap `KeyError` in `{"error": "draft_not_found"}` with `404`; wrap `ValueError` in `{"error": "invalid_draft"}` with `400`.

- [ ] **Step 4: Register explicit draft routes**

Add aiohttp routes before or after the existing route map:

```python
app.router.add_route("GET", "/admin/api/world/drafts", controller.list_world_drafts)
app.router.add_route("POST", "/admin/api/world/drafts", controller.create_world_draft)
app.router.add_route("GET", "/admin/api/world/drafts/{draft_id}", controller.get_world_draft)
app.router.add_route("POST", "/admin/api/world/drafts/{draft_id}", controller.save_world_draft)
app.router.add_route("PATCH", "/admin/api/world/drafts/{draft_id}", controller.update_world_draft)
app.router.add_route("DELETE", "/admin/api/world/drafts/{draft_id}", controller.delete_world_draft)
app.router.add_route("POST", "/admin/api/world/drafts/{draft_id}/activate", controller.activate_world_draft)
app.router.add_route("POST", "/admin/api/world/drafts/{draft_id}/apply", controller.apply_world_draft)
app.router.add_route("POST", "/admin/api/world/drafts/{draft_id}/publish", controller.publish_world_draft)
```

- [ ] **Step 5: Run route tests**

Run: `PYTHONPATH=backend python3 -m unittest backend.admin.tests.test_routes -v`

Expected: route tests pass.

## Task 3: Frontend Draft Switcher

**Files:**
- Modify: `frontend/src/App.js`
- Modify: `frontend/src/App.css`
- Test: `frontend/src/App.test.js`

- [ ] **Step 1: Write failing frontend tests**

Add tests:

```javascript
test('loads draft manifest and switches between independent draft worlds', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({
      active_draft_id: 'main',
      drafts: [
        { id: 'main', name: 'Main Draft', room_count: 2, updated_at: '2026-06-01T20:00:00Z' },
        { id: 'experiment', name: 'Experiment', room_count: 1, updated_at: '2026-06-01T20:10:00Z' },
      ],
    }))
    .mockImplementationOnce(() => okJson({ world: sampleWorld, draft: { id: 'main', name: 'Main Draft' } }))
    .mockImplementationOnce(() => okJson({ world: { ...sampleWorld, rooms: [{ ...sampleWorld.rooms[0], id: 'crypt', name: 'Crypt' }] }, draft: { id: 'experiment', name: 'Experiment' } }));

  render(<App />);
  await screen.findAllByText('Village Square');
  fireEvent.change(screen.getByLabelText('Draft project'), { target: { value: 'experiment' } });
  expect(await screen.findByText('Crypt')).toBeInTheDocument();
});
```

Add:

```javascript
test('creates a new draft from the active draft and saves only the selected draft', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  window.prompt = jest.fn(() => 'Experiment');
  global.fetch
    .mockImplementationOnce(() => okJson({ active_draft_id: 'main', drafts: [{ id: 'main', name: 'Main Draft' }] }))
    .mockImplementationOnce(() => okJson({ world: sampleWorld, draft: { id: 'main', name: 'Main Draft' } }))
    .mockImplementationOnce(() => okJson({ draft: { id: 'experiment', name: 'Experiment' }, world: sampleWorld, manifest: { active_draft_id: 'main', drafts: [{ id: 'main', name: 'Main Draft' }, { id: 'experiment', name: 'Experiment' }] } }))
    .mockImplementationOnce(() => okJson({ validation: { ok: true, errors: [], warnings: [] }, saved: { path: 'drafts/experiment.json' } }));

  render(<App />);
  await screen.findAllByText('Village Square');
  fireEvent.click(screen.getByRole('button', { name: /new draft/i }));
  await screen.findByText(/Editing Draft: Experiment/i);
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(4));
  expect(global.fetch.mock.calls[2][0]).toBe('http://localhost:8080/admin/api/world/drafts');
  expect(global.fetch.mock.calls[3][0]).toBe('http://localhost:8080/admin/api/world/drafts/experiment');
});
```

Add:

```javascript
test('apply and publish target the selected draft project', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({ active_draft_id: 'experiment', drafts: [{ id: 'experiment', name: 'Experiment' }] }))
    .mockImplementationOnce(() => okJson({ world: sampleWorld, draft: { id: 'experiment', name: 'Experiment' } }))
    .mockImplementationOnce(() => okJson({ applied: { rooms: 2, mobs: 1 }, validation: { ok: true, errors: [], warnings: [] } }))
    .mockImplementationOnce(() => okJson({ publish: { ok: true, step: 'push' } }));

  render(<App />);
  await screen.findAllByText('Village Square');
  fireEvent.click(screen.getByRole('button', { name: /apply live/i }));
  fireEvent.click(screen.getByRole('button', { name: /publish git/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(4));
  expect(global.fetch.mock.calls[2][0]).toBe('http://localhost:8080/admin/api/world/drafts/experiment/apply');
  expect(global.fetch.mock.calls[3][0]).toBe('http://localhost:8080/admin/api/world/drafts/experiment/publish');
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- --watchAll=false --runInBand src/App.test.js --testNamePattern="draft"`

Expected: failures because draft controls and API calls do not exist.

- [ ] **Step 3: Implement draft state and API helpers**

Inside `AdminWorldBuilder`, add state:

```javascript
const [drafts, setDrafts] = useState([]);
const [activeDraftId, setActiveDraftId] = useState('');
const [selectedDraftId, setSelectedDraftId] = useState('');
const [currentDraft, setCurrentDraft] = useState(null);
const [isDirty, setIsDirty] = useState(false);
```

Add helpers:

```javascript
const loadDraftManifest = useCallback(async () => {
  const payload = await apiRequest('/admin/api/world/drafts');
  setDrafts(payload.drafts || []);
  setActiveDraftId(payload.active_draft_id || '');
  return payload;
}, [apiRequest]);

const loadDraft = useCallback(async (draftId) => {
  const payload = await apiRequest(`/admin/api/world/drafts/${encodeURIComponent(draftId)}`);
  const nextWorld = normalizeWorld(payload.world);
  setWorld(nextWorld);
  setCurrentDraft(payload.draft || null);
  setSelectedDraftId(draftId);
  setIsDirty(false);
}, [apiRequest]);
```

Wrap mutating `setWorld` calls in a helper that marks dirty:

```javascript
function updateWorld(nextWorld) {
  setWorld(nextWorld);
  setIsDirty(true);
}
```

- [ ] **Step 4: Add project switcher UI**

Add a compact section near the admin toolbar:

```jsx
<section className="draft-switcher" aria-label="Draft projects">
  <label>
    Draft project
    <select value={selectedDraftId} onChange={(event) => handleDraftSelect(event.target.value)}>
      {drafts.map((draft) => <option key={draft.id} value={draft.id}>{draft.name}</option>)}
    </select>
  </label>
  <button type="button" onClick={() => createDraft('active')}>New Draft</button>
  <button type="button" onClick={() => createDraft('live')}>Clone Live</button>
  <button type="button" onClick={renameDraft}>Rename</button>
  <button type="button" onClick={deleteDraft}>Delete</button>
  <span>{currentDraft ? `Editing Draft: ${currentDraft.name}` : 'No draft selected'}</span>
  <small>Live changes only after Apply Live.</small>
</section>
```

Use `window.prompt` for name/description in this iteration, with clear default names: `New Draft` and `Live Clone`.

- [ ] **Step 5: Route actions to selected draft**

Change `runWorldAction` paths:

```javascript
const draftPath = selectedDraftId ? `/admin/api/world/drafts/${encodeURIComponent(selectedDraftId)}` : '/admin/api/world';
const configs = {
  save: { path: draftPath, method: 'POST', body: { world: buildApiWorld(world) }, busy: 'Saving draft...' },
  validate: { path: '/admin/api/world/validate', method: 'POST', body: { world: buildApiWorld(world) }, busy: 'Validating world...' },
  apply: { path: `${draftPath}/apply`, method: 'POST', body: { world: buildApiWorld(world) }, busy: 'Applying live world...' },
  publish: { path: `${draftPath}/publish`, method: 'POST', body: { world: buildApiWorld(world) }, busy: 'Publishing through Git...' },
};
```

After save/apply/publish, refresh manifest and clear dirty. Keep legacy `/admin/api/world` fallback when no selected draft exists.

- [ ] **Step 6: Add draft styling**

In `frontend/src/App.css`, add stable compact layout:

```css
.draft-switcher {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) repeat(4, auto);
  gap: 8px;
  align-items: end;
  border: 1px solid rgba(185, 146, 84, 0.35);
  background: rgba(26, 18, 15, 0.78);
  padding: 10px;
}
```

- [ ] **Step 7: Run frontend draft tests**

Run: `npm test -- --watchAll=false --runInBand src/App.test.js --testNamePattern="draft"`

Expected: draft tests pass.

## Task 4: Verification and Deploy

**Files:**
- All touched implementation/test files.

- [ ] **Step 1: Run backend tests**

Run: `PYTHONPATH=backend python3 -m unittest backend.admin.tests.test_world_builder backend.admin.tests.test_routes -v`

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

Run: `npm test -- --watchAll=false --runInBand src/App.test.js` from `frontend/`

Expected: all tests pass.

- [ ] **Step 3: Build frontend**

Run: `npm run build` from `frontend/`

Expected: optimized production build succeeds.

- [ ] **Step 4: Hygiene check**

Run: `git diff --check`

Expected: no output and exit code 0.

- [ ] **Step 5: Commit implementation**

```bash
git add backend/admin/world_builder.py backend/admin/tests/test_world_builder.py backend/admin/routes.py backend/admin/tests/test_routes.py frontend/src/App.js frontend/src/App.css frontend/src/App.test.js docs/superpowers/plans/2026-06-01-admin-world-draft-projects.md
git commit -m "Add admin world draft projects"
```

- [ ] **Step 6: Push and deploy**

Run: `git push origin HEAD:main`

Expected: backend deploy workflow succeeds. If frontend workflow fails for service-account access, run `npx firebase-tools deploy --only hosting --project forgottenrealms-fb` from `frontend/` and verify the custom domain serves the new bundle.
