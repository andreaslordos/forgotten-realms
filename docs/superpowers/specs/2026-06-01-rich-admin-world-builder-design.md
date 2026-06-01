# Rich Admin World Builder Design

## Goal

Extend the existing admin-gated world builder into a real authoring workstation: rich entity editors, a professional graph canvas, drag/drop room placement, zoom/pan, multi-select, regions, layers, and layout tools.

## Decisions

- Use `@xyflow/react` for the graphical map editor instead of expanding the hand-rolled SVG graph.
- Keep the admin surface at `/admin/world-builder`.
- Preserve the existing JSON world source of truth and admin publish flow.
- Add structured metadata for `regions`, `layers`, `tags`, and `layout`.
- Keep raw JSON fallback editors for escape hatches, but make normal room/exits/items/mobs/scripts editing form-driven.
- Keep script execution safe: scripts are authored as files and activated through Git publish/deploy, not live arbitrary Python execution.

## Data Model

World data gains optional top-level authoring metadata:

```json
{
  "regions": [{ "id": "village", "name": "Village", "color": "#4f8fba", "parent_region_id": null }],
  "layers": [{ "id": "surface", "name": "Surface", "z": 0, "visible": true, "region_id": "village" }],
  "tags": [{ "id": "safe", "label": "Safe", "color": "#4f8fba", "scope": ["room"] }],
  "layout": { "grid_size": 24, "snap_to_grid": true, "default_layer_id": "surface" },
  "rooms": [{
    "id": "square",
    "region_id": "village",
    "tags": ["safe"],
    "layout": { "x": 120, "y": 160, "layer_id": "surface", "pinned": true }
  }]
}
```

Legacy room `x`, `y`, and `z` remain accepted for compatibility. The frontend writes both legacy coordinates and `room.layout` during the transition so existing backend and drafts keep working.

## UI

The map panel becomes a React Flow canvas with draggable room nodes, visible exit edges, minimap/controls/background, pan/zoom, box selection, and multi-select. Moving a node updates that room's `layout.x/y` and legacy `x/y`.

The builder gains a left control rail for layers, regions, filters, and layout actions. The inspector handles:

- Single room editing: identity, description, region, layer, tags, coordinates, exits, items, mobs, scripts.
- Multi-room editing: bulk region/layer/tags, align, distribute, snap, and delete selected.
- Raw JSON fallback for room sections.

Layout tools are deterministic and local:

- Fit view.
- Snap selected to grid.
- Auto grid all visible rooms.
- Arrange by region.
- Align left/top.
- Distribute selected horizontally/vertically.

## Backend

Backend validation adds stable errors and warnings for metadata:

- Duplicate region/layer/tag ids.
- Missing room `region_id`, `layout.layer_id`, or tag references.
- Invalid region parent references or cycles.
- Invalid color values.
- Invalid default layer references.
- Invalid finite numeric coordinates in `room.layout`.
- Warnings for conflicting legacy `x/y/z` versus `room.layout`.

Save/publish preserve all metadata. Apply continues to construct runtime `Room` and `Mobile` objects; authoring metadata is persisted in JSON, not applied to runtime model objects.

## Testing

Backend tests cover metadata validation, legacy coordinate compatibility, and publish check parsing.

Frontend tests cover React Flow-backed room rendering, drag persistence, multi-select/bulk edit, layer filtering, layout actions, typed exits/items/mobs/scripts editing, and raw JSON fallback.
