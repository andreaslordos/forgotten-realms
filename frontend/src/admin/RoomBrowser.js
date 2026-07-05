import React, { useMemo, useState } from 'react';
import {
  exitEntries,
  roomHasPuzzle,
  roomHasStrippedLogic,
  roomLayerId,
} from './worldUtils';

const FLAG_FILTERS = [
  { id: 'dark', label: 'Dark', matches: (room) => Boolean(room.is_dark) },
  { id: 'outdoor', label: 'Outdoor', matches: (room) => Boolean(room.is_outdoor) },
  { id: 'items', label: 'Items', matches: (room) => (room.items || []).length > 0 },
  { id: 'mobs', label: 'Mobs', matches: (room) => (room.mobs || []).length > 0 },
  { id: 'puzzle', label: 'Puzzle', matches: (room) => roomHasPuzzle(room) },
  { id: 'logic', label: 'Py logic', matches: (room) => roomHasStrippedLogic(room) },
  { id: 'noexits', label: 'No exits', matches: (room) => exitEntries(room.exits).length === 0 },
];

export default function RoomBrowser({
  rooms,
  world,
  selectedRoomIds,
  onSelectRoom,
}) {
  const [query, setQuery] = useState('');
  const [regionFilter, setRegionFilter] = useState('');
  const [activeFlags, setActiveFlags] = useState([]);

  const selectedRoomIdSet = useMemo(() => new Set(selectedRoomIds), [selectedRoomIds]);

  const filteredRooms = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const flags = FLAG_FILTERS.filter((flag) => activeFlags.includes(flag.id));
    return rooms.filter((room) => {
      if (regionFilter && room.region_id !== regionFilter) {
        return false;
      }
      if (flags.some((flag) => !flag.matches(room))) {
        return false;
      }
      if (!needle) {
        return true;
      }
      return (
        room.id.toLowerCase().includes(needle)
        || (room.name || '').toLowerCase().includes(needle)
        || (room.description || '').toLowerCase().includes(needle)
      );
    });
  }, [rooms, query, regionFilter, activeFlags]);

  function toggleFlag(flagId) {
    setActiveFlags((current) => (
      current.includes(flagId)
        ? current.filter((id) => id !== flagId)
        : [...current, flagId]
    ));
  }

  const regions = world.regions || [];
  const showRegionFilter = regions.length > 1;

  return (
    <div className="room-browser" role="region" aria-label="Room browser">
      <div className="room-browser__controls">
        <input
          type="search"
          className="room-browser__search"
          placeholder="Search rooms…"
          aria-label="Search rooms"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        {showRegionFilter ? (
          <select
            aria-label="Filter by region"
            value={regionFilter}
            onChange={(event) => setRegionFilter(event.target.value)}
          >
            <option value="">All regions</option>
            {regions.map((region) => (
              <option key={region.id} value={region.id}>{region.name}</option>
            ))}
          </select>
        ) : null}
        <div className="room-browser__flags" role="group" aria-label="Room filters">
          {FLAG_FILTERS.map((flag) => (
            <button
              key={flag.id}
              type="button"
              className={activeFlags.includes(flag.id)
                ? 'filter-chip filter-chip--active'
                : 'filter-chip'}
              aria-pressed={activeFlags.includes(flag.id)}
              onClick={() => toggleFlag(flag.id)}
            >
              {flag.label}
            </button>
          ))}
        </div>
        <div className="room-browser__count" aria-live="polite">
          {filteredRooms.length} / {rooms.length} rooms
        </div>
      </div>

      <div className="room-list">
        {filteredRooms.length === 0 ? (
          <p className="admin-empty">{rooms.length === 0 ? 'No rooms loaded.' : 'No rooms match.'}</p>
        ) : null}
        {filteredRooms.map((room) => (
          <button
            type="button"
            key={room.id}
            className={selectedRoomIdSet.has(room.id)
              ? 'room-list__item room-list__item--selected'
              : 'room-list__item'}
            onClick={(event) => {
              const additive = Boolean(event.metaKey || event.ctrlKey || event.shiftKey);
              onSelectRoom(room.id, additive, !additive);
            }}
          >
            <strong>{room.name}</strong>
            <span>{room.id}</span>
            <small>
              {room.region_id} / {roomLayerId(room, world)} / {exitEntries(room.exits).length} exits
              {room.is_dark ? ' · dark' : ''}
              {roomHasPuzzle(room) ? ' · ⚙' : ''}
              {roomHasStrippedLogic(room) ? ' · ƒ' : ''}
            </small>
          </button>
        ))}
      </div>
    </div>
  );
}
