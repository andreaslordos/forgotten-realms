import React, { useEffect, useRef, useState } from 'react';
import {
  DEFAULT_REGION_ID,
  formatJson,
  roomHasStrippedLogic,
  roomLayerId,
} from './worldUtils';
import {
  ChipListInput,
  ExitsEditor,
  ItemsEditor,
  JsonEditor,
  MobsEditor,
  ScriptsEditor,
} from './editors';

// Room ids cascade through exits/mobs/scripts on every change, so the id
// field commits on blur — typing through a value that transiently collides
// with another room id must not fire rename attempts per keystroke.
function RoomIdInput({ roomId, onCommit }) {
  const [draft, setDraft] = useState(roomId);

  useEffect(() => {
    setDraft(roomId);
  }, [roomId]);

  return (
    <label>
      Room id
      <input
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => {
          if (draft.trim() && draft !== roomId) {
            onCommit(draft.trim());
          } else {
            setDraft(roomId);
          }
        }}
      />
    </label>
  );
}

export default function Inspector({
  room,
  rooms,
  regions,
  layers,
  tags,
  world,
  selectedCount,
  mobDefinitions,
  levels,
  focusNameToken,
  bulkRegionId,
  bulkLayerId,
  onBulkRegionChange,
  onBulkLayerChange,
  onApplyBulkMetadata,
  onFieldChange,
  onLayerChange,
  onTagsChange,
  onJsonFieldCommit,
  onAddExit,
  onExitDirectionChange,
  onExitTargetChange,
  onDeleteExit,
  onAddReverseExit,
  onAddItem,
  onItemChange,
  onDeleteItem,
  onAddMob,
  onMobChange,
  onDeleteMob,
  onAddScript,
  onScriptChange,
  onDeleteScript,
}) {
  const nameInputRef = useRef(null);

  useEffect(() => {
    if (focusNameToken > 0 && nameInputRef.current) {
      nameInputRef.current.focus();
      nameInputRef.current.select();
    }
  }, [focusNameToken]);

  if (!room) {
    return <p className="admin-empty">Select a room on the map or in the browser to edit it.</p>;
  }

  if (selectedCount > 1) {
    return (
      <div className="room-inspector">
        <div className="bulk-editor">
          <p>{selectedCount} rooms selected</p>
          <label>
            Bulk region
            <select aria-label="Bulk region" value={bulkRegionId} onChange={(event) => onBulkRegionChange(event.target.value)}>
              {regions.map((region) => (
                <option key={region.id} value={region.id}>{region.name}</option>
              ))}
            </select>
          </label>
          <label>
            Bulk layer
            <select aria-label="Bulk layer" value={bulkLayerId} onChange={(event) => onBulkLayerChange(event.target.value)}>
              {layers.map((layer) => (
                <option key={layer.id} value={layer.id}>{layer.name}</option>
              ))}
            </select>
          </label>
          <button type="button" onClick={onApplyBulkMetadata}>Apply Bulk Metadata</button>
          <p className="field-hint">Tip: drag on empty canvas for box select; ⌘-click adds to the selection.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="room-inspector">
      {roomHasStrippedLogic(room) ? (
        <div className="logic-warning" role="note">
          ƒ This room carries Python-only logic (hidden items, speech triggers, or
          scripted conditions). It is preserved in the draft but will be lost if
          this draft is applied live. Edit those behaviours in the level code.
        </div>
      ) : null}

      <div className="form-grid">
        <RoomIdInput roomId={room.id} onCommit={(value) => onFieldChange('id', value)} />
        <label>
          Room name
          <input
            ref={nameInputRef}
            value={room.name}
            onChange={(event) => onFieldChange('name', event.target.value)}
          />
        </label>
        <label className="form-grid__wide">
          Room description
          <textarea value={room.description} onChange={(event) => onFieldChange('description', event.target.value)} rows={4} />
        </label>
        <label>
          Region
          <select value={room.region_id || regions[0]?.id || DEFAULT_REGION_ID} onChange={(event) => onFieldChange('region_id', event.target.value)}>
            {regions.map((region) => (
              <option key={region.id} value={region.id}>{region.name}</option>
            ))}
          </select>
        </label>
        <label>
          Layer
          <select value={roomLayerId(room, world)} onChange={(event) => onLayerChange(event.target.value)}>
            {layers.map((layer) => (
              <option key={layer.id} value={layer.id}>{layer.name}</option>
            ))}
          </select>
        </label>
        <ChipListInput
          label="Tags"
          datalistId="world-builder-tags"
          allowCustom
          values={room.tags || []}
          onChange={onTagsChange}
        />
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={Boolean(room.is_dark)}
            onChange={(event) => onFieldChange('is_dark', event.target.checked)}
          />
          Dark
        </label>
        <label className="checkbox-field">
          <input
            type="checkbox"
            checked={Boolean(room.is_outdoor)}
            onChange={(event) => onFieldChange('is_outdoor', event.target.checked)}
          />
          Outdoor
        </label>
      </div>

      <datalist id="world-builder-tags">
        {tags.map((tag) => (
          <option key={tag.id} value={tag.id}>{tag.label}</option>
        ))}
      </datalist>

      <ExitsEditor
        room={room}
        rooms={rooms}
        onAddExit={onAddExit}
        onDirectionChange={onExitDirectionChange}
        onTargetChange={onExitTargetChange}
        onDeleteExit={onDeleteExit}
        onAddReverse={onAddReverseExit}
      />
      <ItemsEditor
        items={room.items || []}
        levels={levels}
        onAdd={onAddItem}
        onChange={onItemChange}
        onDelete={onDeleteItem}
      />
      <MobsEditor
        mobs={room.mobs || []}
        mobDefinitions={mobDefinitions}
        rooms={rooms}
        onAdd={onAddMob}
        onChange={onMobChange}
        onDelete={onDeleteMob}
      />
      <ScriptsEditor
        scripts={room.scripts || []}
        onAdd={onAddScript}
        onChange={onScriptChange}
        onDelete={onDeleteScript}
      />

      <details className="raw-json-editors">
        <summary>Raw JSON</summary>
        <div className="editor-tabs">
          <JsonEditor
            label="Exits JSON"
            value={formatJson(room.exits || {})}
            help={`Known rooms: ${rooms.map((item) => item.id).join(', ') || 'none'}`}
            onCommit={(parsed) => onJsonFieldCommit('exits', parsed)}
          />
          <JsonEditor
            label="Items JSON"
            value={formatJson(room.items || [])}
            onCommit={(parsed) => onJsonFieldCommit('items', parsed)}
          />
          <JsonEditor
            label="Mobs JSON"
            value={formatJson(room.mobs || [])}
            onCommit={(parsed) => onJsonFieldCommit('mobs', parsed)}
          />
          <JsonEditor
            label="Scripts JSON"
            value={formatJson(room.scripts || [])}
            onCommit={(parsed) => onJsonFieldCommit('scripts', parsed)}
          />
        </div>
      </details>
    </div>
  );
}
