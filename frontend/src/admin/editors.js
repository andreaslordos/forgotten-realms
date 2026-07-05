import React, { useEffect, useState } from 'react';
import {
  CANONICAL_DIRECTIONS,
  exitEntries,
  itemHasStrippedLogic,
  reverseExitStatus,
} from './worldUtils';

export function ExitsEditor({
  room,
  rooms,
  onAddExit,
  onDirectionChange,
  onTargetChange,
  onDeleteExit,
  onAddReverse,
}) {
  const entries = exitEntries(room.exits);
  const roomById = new Map(rooms.map((candidate) => [candidate.id, candidate]));

  return (
    <section className="rich-editor">
      <div className="rich-editor__header">
        <h3>Exits</h3>
        <button type="button" onClick={onAddExit}>Add Exit</button>
      </div>
      {entries.length === 0 ? <p className="admin-empty">No exits. Use the dig compass on the map to carve one.</p> : null}
      {entries.map(([direction, targetRoomId]) => {
        const targetRoom = roomById.get(targetRoomId);
        const reverse = reverseExitStatus(room, direction, targetRoom);
        const directionOptions = CANONICAL_DIRECTIONS.includes(direction)
          ? CANONICAL_DIRECTIONS
          : [direction, ...CANONICAL_DIRECTIONS];
        return (
          <div key={direction} className="exit-row">
            <select
              aria-label={`Exit ${direction} direction`}
              value={direction}
              onChange={(event) => onDirectionChange(direction, event.target.value)}
            >
              {directionOptions.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>
            <select
              aria-label={`Exit ${direction} target`}
              value={targetRoomId}
              onChange={(event) => onTargetChange(direction, event.target.value)}
            >
              <option value="">— target —</option>
              {rooms.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.name} ({candidate.id})
                </option>
              ))}
            </select>
            {reverse.state === 'linked' || reverse.state === 'linked-other' ? (
              <span className="exit-row__reverse exit-row__reverse--ok" title="Reverse exit exists">⇄</span>
            ) : null}
            {reverse.state === 'missing' ? (
              <button
                type="button"
                className="exit-row__reverse"
                title={`Add ${reverse.opposite} exit from ${targetRoomId} back to ${room.id}`}
                onClick={() => onAddReverse(direction)}
              >
                + reverse
              </button>
            ) : null}
            {reverse.state === 'blocked' ? (
              <span className="exit-row__reverse exit-row__reverse--blocked" title={`${targetRoomId} already has a ${reverse.opposite} exit elsewhere`}>⇢</span>
            ) : null}
            <button
              type="button"
              className="row-delete"
              aria-label={`Delete exit ${direction}`}
              title="Delete exit"
              onClick={() => onDeleteExit(direction)}
            >
              ✕
            </button>
          </div>
        );
      })}
    </section>
  );
}

const ITEM_TYPES = [
  { value: 'item', label: 'Item' },
  { value: 'weapon', label: 'Weapon' },
  { value: 'stateful_item', label: 'Stateful' },
  { value: 'container_item', label: 'Container' },
];

// Numeric and list inputs commit on blur: committing per keystroke makes
// mid-edit values (a cleared field, a trailing comma) live before the user
// finished typing.
function NumberField({ label, value, onChange }) {
  const [draft, setDraft] = useState(value ?? '');

  useEffect(() => {
    setDraft(value ?? '');
  }, [value]);

  function commit() {
    const parsed = draft === '' ? 0 : Number(draft);
    onChange(Number.isFinite(parsed) ? parsed : (value ?? 0));
  }

  return (
    <label>
      {label}
      <input
        type="number"
        aria-label={label}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
      />
    </label>
  );
}

/**
 * Chip list for multi-value fields. With `options` the entry control is a
 * dropdown restricted to valid values (e.g. patrol rooms must reference real
 * rooms); with `allowCustom` it is a text input committing on Enter/blur
 * (e.g. tags, an open vocabulary).
 */
export function ChipListInput({ label, values, onChange, options, allowCustom = false, datalistId }) {
  const [draft, setDraft] = useState('');
  const currentValues = values || [];

  function addValue(value) {
    const trimmed = value.trim();
    if (trimmed && !currentValues.includes(trimmed)) {
      onChange([...currentValues, trimmed]);
    }
    setDraft('');
  }

  const availableOptions = (options || []).filter((option) => !currentValues.includes(option.value));

  return (
    <div className="chip-list form-grid__wide">
      <span className="chip-list__label">{label}</span>
      <div className="chip-list__chips">
        {currentValues.map((value) => (
          <span key={value} className="chip">
            {value}
            <button
              type="button"
              aria-label={`Remove ${value} from ${label.toLowerCase()}`}
              onClick={() => onChange(currentValues.filter((candidate) => candidate !== value))}
            >
              ✕
            </button>
          </span>
        ))}
        {options ? (
          <select
            aria-label={`Add to ${label.toLowerCase()}`}
            value=""
            disabled={availableOptions.length === 0}
            onChange={(event) => addValue(event.target.value)}
          >
            <option value="">+ add…</option>
            {availableOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        ) : null}
        {allowCustom ? (
          <input
            aria-label={`Add to ${label.toLowerCase()}`}
            placeholder="+ add…"
            list={datalistId}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onBlur={() => addValue(draft)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                addValue(draft);
              }
            }}
          />
        ) : null}
      </div>
    </div>
  );
}

export function ItemsEditor({ items, levels, onAdd, onChange, onDelete }) {
  return (
    <section className="rich-editor">
      <div className="rich-editor__header">
        <h3>Items</h3>
        <button type="button" onClick={onAdd}>Add Item</button>
      </div>
      {items.length === 0 ? <p className="admin-empty">No items.</p> : null}
      {items.map((item, index) => {
        const type = item.type || 'item';
        const hasLogic = itemHasStrippedLogic(item);
        return (
          <details key={item.id || index} className="collection-card">
            <summary>
              <strong>{item.name || item.id || `Item ${index + 1}`}</strong>
              <span className="collection-card__type">{type}</span>
              {hasLogic ? (
                <span className="collection-card__logic" title="This item carries Python-only logic (conditions/effects) that this editor cannot modify. Editing and applying may strip it.">ƒ</span>
              ) : null}
              <button
                type="button"
                className="row-delete"
                aria-label={`Delete item ${item.id || index + 1}`}
                onClick={(event) => {
                  event.preventDefault();
                  onDelete(index);
                }}
              >
                ✕
              </button>
            </summary>
            <div className="collection-card__body form-grid">
              <label>
                Id
                <input aria-label={`Item ${index + 1} id`} value={item.id || ''} onChange={(event) => onChange(index, 'id', event.target.value)} />
              </label>
              <label>
                Name
                <input aria-label={`Item ${index + 1} name`} value={item.name || ''} onChange={(event) => onChange(index, 'name', event.target.value)} />
              </label>
              <label>
                Type
                <select aria-label={`Item ${index + 1} type`} value={type} onChange={(event) => onChange(index, 'type', event.target.value)}>
                  {ITEM_TYPES.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label className="form-grid__wide">
                Description
                <textarea aria-label={`Item ${index + 1} description`} rows={2} value={item.description || ''} onChange={(event) => onChange(index, 'description', event.target.value)} />
              </label>
              <NumberField label="Weight" value={item.weight} onChange={(value) => onChange(index, 'weight', value)} />
              <NumberField label="Value" value={item.value} onChange={(value) => onChange(index, 'value', value)} />
              <label className="checkbox-field">
                <input type="checkbox" checked={item.takeable !== false} onChange={(event) => onChange(index, 'takeable', event.target.checked)} />
                Takeable
              </label>
              <label className="checkbox-field">
                <input type="checkbox" checked={Boolean(item.emits_light)} onChange={(event) => onChange(index, 'emits_light', event.target.checked)} />
                Emits light
              </label>
              {type === 'weapon' ? (
                <>
                  <NumberField label="Damage" value={item.damage} onChange={(value) => onChange(index, 'damage', value)} />
                  <NumberField label="Min strength" value={item.min_strength} onChange={(value) => onChange(index, 'min_strength', value)} />
                  <NumberField label="Min dexterity" value={item.min_dexterity} onChange={(value) => onChange(index, 'min_dexterity', value)} />
                  <label>
                    Min level
                    <select aria-label="Min level" value={item.min_level || ''} onChange={(event) => onChange(index, 'min_level', event.target.value)}>
                      <option value="">— none —</option>
                      {(item.min_level && !(levels || []).includes(item.min_level)) ? (
                        <option value={item.min_level}>{item.min_level}</option>
                      ) : null}
                      {(levels || []).map((levelName) => (
                        <option key={levelName} value={levelName}>{levelName}</option>
                      ))}
                    </select>
                  </label>
                </>
              ) : null}
              {type === 'container_item' ? (
                <>
                  <NumberField label="Capacity (items)" value={item.capacity_limit} onChange={(value) => onChange(index, 'capacity_limit', value)} />
                  <NumberField label="Capacity (weight)" value={item.capacity_weight} onChange={(value) => onChange(index, 'capacity_weight', value)} />
                </>
              ) : null}
              {type === 'stateful_item' || type === 'container_item' ? (
                <label>
                  State
                  <input aria-label={`Item ${index + 1} state`} value={item.state || ''} onChange={(event) => onChange(index, 'state', event.target.value)} />
                </label>
              ) : null}
              {type === 'stateful_item' ? (
                <p className="field-hint form-grid__wide">State descriptions and interactions are editable in Raw JSON below.</p>
              ) : null}
            </div>
          </details>
        );
      })}
    </section>
  );
}

const PRONOUN_OPTIONS = ['he', 'she', 'it', 'they'];

export function MobsEditor({ mobs, mobDefinitions, rooms, onAdd, onChange, onDelete }) {
  const [pendingDefinition, setPendingDefinition] = useState('');

  return (
    <section className="rich-editor">
      <div className="rich-editor__header">
        <h3>Mobs</h3>
        <span className="mob-palette">
          <select
            aria-label="Mob template"
            value={pendingDefinition}
            onChange={(event) => setPendingDefinition(event.target.value)}
          >
            <option value="">Blank mob</option>
            {mobDefinitions.map((definition) => (
              <option key={definition.id} value={definition.id}>
                {definition.name} ({definition.id})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => onAdd(mobDefinitions.find((definition) => definition.id === pendingDefinition) || null)}
          >
            Add Mob
          </button>
        </span>
      </div>
      {mobs.length === 0 ? <p className="admin-empty">No mobs.</p> : null}
      {mobs.map((mob, index) => (
        <details key={mob.id || index} className="collection-card">
          <summary>
            <strong>{mob.name || mob.id || `Mob ${index + 1}`}</strong>
            <span className="collection-card__type">{mob.aggressive ? 'aggressive' : 'passive'}</span>
            <button
              type="button"
              className="row-delete"
              aria-label={`Delete mob ${mob.id || index + 1}`}
              onClick={(event) => {
                event.preventDefault();
                onDelete(index);
              }}
            >
              ✕
            </button>
          </summary>
          <div className="collection-card__body form-grid">
            <label>
              Id
              <input aria-label={`Mob ${index + 1} id`} value={mob.id || ''} onChange={(event) => onChange(index, 'id', event.target.value)} />
            </label>
            <label>
              Name
              <input aria-label={`Mob ${index + 1} name`} value={mob.name || ''} onChange={(event) => onChange(index, 'name', event.target.value)} />
            </label>
            <label className="form-grid__wide">
              Description
              <textarea aria-label={`Mob ${index + 1} description`} rows={2} value={mob.description || ''} onChange={(event) => onChange(index, 'description', event.target.value)} />
            </label>
            <NumberField label="Strength" value={mob.strength} onChange={(value) => onChange(index, 'strength', value)} />
            <NumberField label="Dexterity" value={mob.dexterity} onChange={(value) => onChange(index, 'dexterity', value)} />
            <NumberField label="Max stamina" value={mob.max_stamina} onChange={(value) => onChange(index, 'max_stamina', value)} />
            <NumberField label="Damage" value={mob.damage} onChange={(value) => onChange(index, 'damage', value)} />
            <NumberField label="Move interval" value={mob.movement_interval} onChange={(value) => onChange(index, 'movement_interval', value)} />
            <NumberField label="Point value" value={mob.point_value} onChange={(value) => onChange(index, 'point_value', value)} />
            <label>
              Pronouns
              <select aria-label={`Mob ${index + 1} pronouns`} value={mob.pronouns || 'it'} onChange={(event) => onChange(index, 'pronouns', event.target.value)}>
                {PRONOUN_OPTIONS.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
            <label className="checkbox-field">
              <input type="checkbox" checked={Boolean(mob.aggressive)} onChange={(event) => onChange(index, 'aggressive', event.target.checked)} />
              Aggressive
            </label>
            <ChipListInput
              label={`Mob ${index + 1} patrol rooms`}
              values={Array.isArray(mob.patrol_rooms) ? mob.patrol_rooms : []}
              options={rooms.map((room) => ({ value: room.id, label: `${room.name} (${room.id})` }))}
              onChange={(patrolRooms) => onChange(index, 'patrol_rooms', patrolRooms)}
            />
          </div>
        </details>
      ))}
    </section>
  );
}

const SCRIPT_PATH_PREFIX = 'backend/world_scripts/';
const SCRIPT_TRIGGER_SUGGESTIONS = ['interact', 'enter'];

export function ScriptsEditor({ scripts, onAdd, onChange, onDelete }) {
  return (
    <section className="rich-editor">
      <div className="rich-editor__header">
        <h3>Scripts</h3>
        <button type="button" onClick={onAdd}>Add Script</button>
      </div>
      <datalist id="script-trigger-suggestions">
        {SCRIPT_TRIGGER_SUGGESTIONS.map((trigger) => (
          <option key={trigger} value={trigger} />
        ))}
      </datalist>
      {scripts.length === 0 ? <p className="admin-empty">No scripts.</p> : null}
      {scripts.map((script, index) => (
        <details key={script.id || index} className="collection-card">
          <summary>
            <strong>{script.id || `Script ${index + 1}`}</strong>
            <span className="collection-card__type">{script.trigger || 'interact'}</span>
            <button
              type="button"
              className="row-delete"
              aria-label={`Delete script ${script.id || index + 1}`}
              onClick={(event) => {
                event.preventDefault();
                onDelete(index);
              }}
            >
              ✕
            </button>
          </summary>
          <div className="collection-card__body form-grid">
            <label>
              Id
              <input aria-label={`Script ${index + 1} id`} value={script.id || ''} onChange={(event) => onChange(index, 'id', event.target.value)} />
            </label>
            <label>
              Trigger
              <input
                aria-label={`Script ${index + 1} trigger`}
                list="script-trigger-suggestions"
                value={script.trigger || ''}
                onChange={(event) => onChange(index, 'trigger', event.target.value)}
              />
            </label>
            <label className="form-grid__wide">
              File (in {SCRIPT_PATH_PREFIX})
              <input
                aria-label={`Script ${index + 1} filename`}
                value={(script.path || '').startsWith(SCRIPT_PATH_PREFIX)
                  ? (script.path || '').slice(SCRIPT_PATH_PREFIX.length)
                  : (script.path || '')}
                onChange={(event) => {
                  // Scripts must live under world_scripts/ — anything else is
                  // rejected by validation, so the prefix is not editable.
                  const filename = event.target.value.replace(/[/\\]/g, '');
                  onChange(index, 'path', `${SCRIPT_PATH_PREFIX}${filename}`);
                }}
              />
            </label>
            <label className="form-grid__wide">
              Content
              <textarea aria-label={`Script ${index + 1} content`} rows={6} value={script.content || ''} onChange={(event) => onChange(index, 'content', event.target.value)} />
            </label>
          </div>
        </details>
      ))}
    </section>
  );
}

export function JsonEditor({ label, value, help, onCommit }) {
  const [draft, setDraft] = useState(value);
  const [error, setError] = useState('');

  useEffect(() => {
    setDraft(value);
    setError('');
  }, [value]);

  function commit() {
    if (draft === value) {
      return;
    }
    try {
      const parsed = JSON.parse(draft);
      setError('');
      onCommit(parsed);
    } catch (parseError) {
      setError(parseError.message);
    }
  }

  return (
    <div className="json-editor">
      <span>{label}</span>
      <textarea
        aria-label={label}
        value={draft}
        rows={6}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={commit}
      />
      {error ? <small className="json-editor__error" role="alert">Invalid JSON: {error}</small> : null}
      {help && !error ? <small>{help}</small> : null}
    </div>
  );
}
