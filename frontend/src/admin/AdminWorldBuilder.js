import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getBackendUrl } from '../config';
import WorldGraph from './WorldGraph';
import RoomBrowser from './RoomBrowser';
import Inspector from './Inspector';
import {
  CELL_HEIGHT,
  CELL_WIDTH,
  DEFAULT_LAYER_ID,
  DEFAULT_REGION_ID,
  DIRECTION_VECTORS,
  OPPOSITE_DIRECTIONS,
  autoLayoutRooms,
  buildApiWorld,
  cellKey,
  directionBetween,
  effectiveSpawnRoomId,
  emptyWorld,
  finiteNumber,
  firstFreeDirection,
  getRoomPosition,
  makeRoom,
  nearestFreeCell,
  normalizeWorld,
  positionToCell,
  roomIdFollowsName,
  roomLayerId,
  roomsNeedLayout,
  setRoomPosition,
  slugify,
  snapValue,
  uniqueRoomId,
} from './worldUtils';

const HISTORY_LIMIT = 50;
const DIG_DIRECTIONS = ['northwest', 'north', 'northeast', 'west', 'east', 'southwest', 'south', 'southeast', 'up', 'down'];
const DIG_LABELS = {
  northwest: 'NW', north: 'N', northeast: 'NE', west: 'W', east: 'E',
  southwest: 'SW', south: 'S', southeast: 'SE', up: 'U', down: 'D',
};

function summarizePayload(payload) {
  if (payload.publish) {
    if (payload.publish.ok === false) {
      return `Publish failed: ${payload.publish.error || payload.publish.step || 'unknown error'}`;
    }
    const commit = payload.publish.commit ? ` (${payload.publish.commit})` : '';
    return `Publish complete${commit}`;
  }
  if (payload.applied) {
    return `Applied live: ${payload.applied.rooms ?? 0} rooms, ${payload.applied.mobs ?? 0} mobs`;
  }
  if (payload.saved) {
    return 'Save complete';
  }
  if (payload.validation) {
    return payload.validation.ok ? 'Validation complete' : 'Validation found issues';
  }
  if (payload.world) {
    return 'World loaded';
  }
  return 'Action complete';
}

function formatDraftOption(draft) {
  const roomCount = Number.isFinite(Number(draft.room_count))
    ? `${Number(draft.room_count)} rooms`
    : 'unknown rooms';
  const updatedAt = draft.updated_at ? ` - ${String(draft.updated_at).slice(0, 10)}` : '';
  return `${draft.name} - ${roomCount}${updatedAt}`;
}

function renameRoomEverywhere(world, previousRoomId, nextRoomId) {
  const renameId = (roomId) => (roomId === previousRoomId ? nextRoomId : roomId);
  const renamePatrol = (mob) => {
    if (!Array.isArray(mob.patrol_rooms) || !mob.patrol_rooms.includes(previousRoomId)) {
      return mob;
    }
    return { ...mob, patrol_rooms: mob.patrol_rooms.map(renameId) };
  };

  return {
    ...world,
    spawn_room_id: renameId(world.spawn_room_id),
    rooms: world.rooms.map((room) => {
      const referencesOldId = Object.values(room.exits || {}).includes(previousRoomId)
        || (room.mobs || []).some((mob) => Array.isArray(mob.patrol_rooms) && mob.patrol_rooms.includes(previousRoomId));
      if (room.id !== previousRoomId && !referencesOldId) {
        return room;
      }
      const exits = Object.fromEntries(
        Object.entries(room.exits || {}).map(([direction, targetRoomId]) => [direction, renameId(targetRoomId)])
      );
      if (room.id !== previousRoomId) {
        return { ...room, exits, mobs: (room.mobs || []).map(renamePatrol) };
      }
      return {
        ...room,
        id: nextRoomId,
        exits,
        mobs: (room.mobs || []).map((mob) => renamePatrol({ ...mob, current_room: nextRoomId })),
        scripts: (room.scripts || []).map((script) => ({ ...script, room_id: nextRoomId })),
      };
    }),
    mobs: (world.mobs || []).map((mob) => renamePatrol(
      mob.current_room === previousRoomId ? { ...mob, current_room: nextRoomId } : mob
    )),
    scripts: (world.scripts || []).map((script) => (
      script.room_id === previousRoomId ? { ...script, room_id: nextRoomId } : script
    )),
  };
}

function occupiedCells(rooms) {
  const occupied = new Map();
  rooms.forEach((room, index) => {
    const [col, row] = positionToCell(getRoomPosition(room, index));
    occupied.set(cellKey(col, row), room.id);
  });
  return occupied;
}

export default function AdminWorldBuilder({ adminToken, onAdminTokenInvalid }) {
  const [world, setWorldState] = useState(emptyWorld());
  const worldRef = useRef(world);
  const historyRef = useRef({ past: [], future: [] });
  const lastCoalesceKeyRef = useRef(null);

  const [selectedRoomIds, setSelectedRoomIds] = useState([]);
  const [visibleLayerIds, setVisibleLayerIds] = useState([DEFAULT_LAYER_ID]);
  const [bulkRegionId, setBulkRegionId] = useState(DEFAULT_REGION_ID);
  const [bulkLayerId, setBulkLayerId] = useState(DEFAULT_LAYER_ID);
  const [validation, setValidation] = useState({ ok: true, errors: [], warnings: [] });
  const [apiStatus, setApiStatus] = useState(adminToken ? 'Ready' : 'Waiting for stupidgem admin token.');
  const [apiError, setApiError] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const [drafts, setDrafts] = useState([]);
  const [activeDraftId, setActiveDraftId] = useState('');
  const [selectedDraftId, setSelectedDraftId] = useState('');
  const [currentDraft, setCurrentDraft] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const [draftDialog, setDraftDialog] = useState(null);
  const [mobDefinitions, setMobDefinitions] = useState([]);
  const [levels, setLevels] = useState([]);
  const [fitViewToken, setFitViewToken] = useState(0);
  const [focusRequest, setFocusRequest] = useState(null);
  const [focusNameToken, setFocusNameToken] = useState(0);

  const setWorld = useCallback((nextWorld) => {
    worldRef.current = nextWorld;
    setWorldState(nextWorld);
  }, []);

  // options.coalesceKey groups a burst of edits to the same field into ONE
  // undo entry: only the first change of a burst snapshots the world, so ⌘Z
  // reverts the whole burst instead of one keystroke.
  const applyWorldChange = useCallback((updater, options = {}) => {
    const current = worldRef.current;
    const next = typeof updater === 'function' ? updater(current) : updater;
    if (!next || next === current) {
      return;
    }
    const coalesceKey = options.coalesceKey || null;
    const coalesced = coalesceKey && coalesceKey === lastCoalesceKeyRef.current;
    if (!coalesced) {
      historyRef.current.past.push(current);
      if (historyRef.current.past.length > HISTORY_LIMIT) {
        historyRef.current.past.shift();
      }
      historyRef.current.future = [];
    }
    lastCoalesceKeyRef.current = coalesceKey;
    setWorld(next);
    setIsDirty(true);
  }, [setWorld]);

  const undo = useCallback(() => {
    const { past, future } = historyRef.current;
    if (past.length === 0) {
      return;
    }
    const previous = past.pop();
    future.push(worldRef.current);
    lastCoalesceKeyRef.current = null;
    setWorld(previous);
    setIsDirty(true);
  }, [setWorld]);

  const redo = useCallback(() => {
    const { past, future } = historyRef.current;
    if (future.length === 0) {
      return;
    }
    const next = future.pop();
    past.push(worldRef.current);
    lastCoalesceKeyRef.current = null;
    setWorld(next);
    setIsDirty(true);
  }, [setWorld]);

  const canUndo = historyRef.current.past.length > 0;
  const canRedo = historyRef.current.future.length > 0;

  const apiRequest = useCallback(async (path, options = {}) => {
    if (!adminToken) {
      throw new Error('Waiting for stupidgem admin token.');
    }
    const method = options.method || 'GET';
    const headers = { Authorization: `Bearer ${adminToken}` };
    const requestOptions = { method, headers };
    if (method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      if (options.body) {
        requestOptions.body = JSON.stringify(options.body);
      }
    }
    const response = await fetch(`${getBackendUrl()}${path}`, requestOptions);
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      payload = {};
    }
    if (!response.ok) {
      const message = payload.message || payload.error || `Admin API failed with ${response.status}`;
      if (response.status === 401) {
        onAdminTokenInvalid?.();
      }
      const failure = new Error(message);
      failure.status = response.status;
      failure.payload = payload;
      throw failure;
    }
    return payload;
  }, [adminToken, onAdminTokenInvalid]);

  const applyManifestPayload = useCallback((payload) => {
    const manifest = payload.manifest || payload;
    if (Array.isArray(manifest.drafts)) {
      setDrafts(manifest.drafts);
    }
    if (manifest.active_draft_id) {
      setActiveDraftId(manifest.active_draft_id);
    }
  }, []);

  const applyLoadedWorld = useCallback((payload, fallbackDraftId = '') => {
    let nextWorld = normalizeWorld(payload.world);
    // Worlds that were never placed on the map get an exit-aware layout, but
    // rooms with authored positions are left untouched.
    const autoLaidOut = roomsNeedLayout(nextWorld.rooms);
    if (autoLaidOut) {
      nextWorld = { ...nextWorld, rooms: autoLayoutRooms(nextWorld, { onlyUnplaced: true }) };
    }
    const nextSelectedRoomId = nextWorld.rooms[0]?.id || '';
    const nextVisibleLayerIds = nextWorld.layers.filter((layer) => layer.visible !== false).map((layer) => layer.id);
    const payloadDrafts = payload.drafts || payload.manifest?.drafts || [];
    const payloadActiveDraftId = payload.active_draft_id || payload.manifest?.active_draft_id || '';
    const payloadDraft = payload.draft
      || payloadDrafts.find((draft) => draft.id === fallbackDraftId)
      || payloadDrafts.find((draft) => draft.id === payloadActiveDraftId)
      || null;

    historyRef.current = { past: [], future: [] };
    lastCoalesceKeyRef.current = null;
    setWorld(nextWorld);
    setSelectedRoomIds(nextSelectedRoomId ? [nextSelectedRoomId] : []);
    setVisibleLayerIds(nextVisibleLayerIds.length ? nextVisibleLayerIds : nextWorld.layers.map((layer) => layer.id));
    setBulkRegionId(nextWorld.regions[0]?.id || DEFAULT_REGION_ID);
    setBulkLayerId(nextWorld.layout?.default_layer_id || nextWorld.layers[0]?.id || DEFAULT_LAYER_ID);
    applyManifestPayload(payload);
    setCurrentDraft((previousDraft) => (
      payloadDraft || (fallbackDraftId && previousDraft?.id === fallbackDraftId ? previousDraft : null)
    ));
    setSelectedDraftId(payloadDraft?.id || fallbackDraftId || payloadActiveDraftId || '');
    // Auto-layout on load produces positions the draft doesn't have yet — be
    // honest about that instead of showing a clean state.
    setIsDirty(autoLaidOut);
    setFitViewToken((token) => token + 1);
  }, [applyManifestPayload, setWorld]);

  const loadWorld = useCallback(async () => {
    if (!adminToken) {
      setApiStatus('Waiting for stupidgem admin token.');
      return;
    }
    setIsBusy(true);
    setApiError('');
    setApiStatus('Loading world...');
    try {
      const payload = await apiRequest('/admin/api/world');
      applyLoadedWorld(payload);
      if (payload.validation) {
        setValidation(payload.validation);
      }
      setApiStatus(summarizePayload(payload));
    } catch (error) {
      setApiError(error.message);
      setApiStatus('Load failed');
    } finally {
      setIsBusy(false);
    }
  }, [adminToken, apiRequest, applyLoadedWorld]);

  useEffect(() => {
    if (adminToken) {
      loadWorld();
    } else {
      setApiStatus('Waiting for stupidgem admin token.');
    }
  }, [adminToken, loadWorld]);

  useEffect(() => {
    if (!adminToken) {
      return;
    }
    apiRequest('/admin/api/world/mob-definitions')
      .then((payload) => {
        setMobDefinitions(payload.mob_definitions || []);
        setLevels(payload.levels || []);
      })
      .catch(() => {
        setMobDefinitions([]);
        setLevels([]);
      });
  }, [adminToken, apiRequest]);

  // Selection --------------------------------------------------------------

  const selectedRoom = world.rooms.find((room) => room.id === selectedRoomIds[0]) || null;
  const selectedCount = selectedRoomIds.length;

  useEffect(() => {
    const roomIds = new Set(world.rooms.map((room) => room.id));
    setSelectedRoomIds((current) => {
      const filtered = current.filter((roomId) => roomIds.has(roomId));
      return filtered.length === current.length ? current : filtered;
    });
  }, [world.rooms]);

  useEffect(() => {
    const layerIds = world.layers.map((layer) => layer.id);
    const regionIds = world.regions.map((region) => region.id);
    setVisibleLayerIds((current) => {
      const filtered = current.filter((layerId) => layerIds.includes(layerId));
      if (filtered.length > 0 || layerIds.length === 0) {
        return filtered;
      }
      const defaultVisible = world.layers.filter((layer) => layer.visible !== false).map((layer) => layer.id);
      return defaultVisible.length ? defaultVisible : layerIds;
    });
    setBulkLayerId((current) => (
      layerIds.includes(current) ? current : (world.layout?.default_layer_id || layerIds[0] || DEFAULT_LAYER_ID)
    ));
    setBulkRegionId((current) => (
      regionIds.includes(current) ? current : (regionIds[0] || DEFAULT_REGION_ID)
    ));
  }, [world.layers, world.layout?.default_layer_id, world.regions]);

  const handleSelectRoom = useCallback((roomId, additive = false, focus = false) => {
    setSelectedRoomIds((current) => {
      if (!additive) {
        return current.length === 1 && current[0] === roomId ? current : [roomId];
      }
      if (current.includes(roomId)) {
        return current.filter((id) => id !== roomId);
      }
      return [...current, roomId];
    });
    if (focus && !additive) {
      setFocusRequest({ roomId });
    }
    lastCoalesceKeyRef.current = null;
  }, []);

  const handleGraphSelection = useCallback((roomIds) => {
    setSelectedRoomIds((current) => {
      if (current.length === roomIds.length && current.every((id, index) => id === roomIds[index])) {
        return current;
      }
      return roomIds;
    });
  }, []);

  // Room mutations -----------------------------------------------------------

  function updateRoom(roomId, updater, options = {}) {
    applyWorldChange((current) => ({
      ...current,
      rooms: current.rooms.map((room) => (room.id === roomId ? updater(room) : room)),
    }), options);
  }

  function updateRooms(roomIds, updater) {
    const roomIdSet = new Set(roomIds);
    applyWorldChange((current) => ({
      ...current,
      rooms: current.rooms.map((room, index) => (roomIdSet.has(room.id) ? updater(room, index) : room)),
    }));
  }

  const handleMoveRooms = useCallback((moves) => {
    const moveByRoomId = new Map(moves.map((move) => [move.roomId, move]));
    applyWorldChange((current) => {
      let didChange = false;
      const rooms = current.rooms.map((room) => {
        const move = moveByRoomId.get(room.id);
        if (!move) {
          return room;
        }
        const position = getRoomPosition(room, 0);
        if (position.x === move.x && position.y === move.y) {
          return room;
        }
        didChange = true;
        return setRoomPosition(room, move.x, move.y);
      });
      return didChange ? { ...current, rooms } : current;
    });
  }, [applyWorldChange]);

  const handleConnectRooms = useCallback((sourceId, targetId, anchorDirection = null) => {
    const current = worldRef.current;
    const source = current.rooms.find((room) => room.id === sourceId);
    const target = current.rooms.find((room) => room.id === targetId);
    if (!source || !target) {
      return;
    }
    const taken = new Set(Object.keys(source.exits || {}));
    if (anchorDirection && taken.has(anchorDirection)) {
      setApiError(`'${sourceId}' already has a ${anchorDirection} exit.`);
      return;
    }
    // The anchor the user dragged from names the direction; geometry is the
    // fallback for connections without one (e.g. tests, older flows).
    const direction = anchorDirection
      || directionBetween(getRoomPosition(source, 0), getRoomPosition(target, 0), taken);
    if (!direction) {
      setApiError(`No free direction left on '${sourceId}'.`);
      return;
    }
    setApiError('');
    const opposite = OPPOSITE_DIRECTIONS[direction];
    const reverseFree = opposite && !(target.exits || {})[opposite];
    applyWorldChange((currentWorld) => ({
      ...currentWorld,
      rooms: currentWorld.rooms.map((room) => {
        if (room.id === sourceId) {
          return { ...room, exits: { ...(room.exits || {}), [direction]: targetId } };
        }
        if (room.id === targetId && reverseFree) {
          return { ...room, exits: { ...(room.exits || {}), [opposite]: sourceId } };
        }
        return room;
      }),
    }));
    setApiStatus(`Connected ${sourceId} ${direction} → ${targetId}${reverseFree ? ` (reverse ${opposite} added)` : ' (one-way)'}`);
  }, [applyWorldChange]);

  const digRoom = useCallback((direction) => {
    const current = worldRef.current;
    const source = current.rooms.find((room) => room.id === selectedRoomIds[0]);
    if (!source) {
      return;
    }
    if ((source.exits || {})[direction]) {
      setApiError(`'${source.id}' already has a ${direction} exit.`);
      return;
    }
    const [sourceCol, sourceRow] = positionToCell(getRoomPosition(source, 0));
    const vector = DIRECTION_VECTORS[direction];
    const occupied = occupiedCells(current.rooms);
    const targetCell = vector
      ? (occupied.has(cellKey(sourceCol + vector[0], sourceRow + vector[1]))
        ? nearestFreeCell(occupied, sourceCol + vector[0], sourceRow + vector[1])
        : [sourceCol + vector[0], sourceRow + vector[1]])
      : nearestFreeCell(occupied, sourceCol, sourceRow + 1);

    const layerId = roomLayerId(source, current);
    const newRoom = makeRoom(current, {
      x: targetCell[0] * CELL_WIDTH,
      y: targetCell[1] * CELL_HEIGHT,
      region_id: source.region_id || DEFAULT_REGION_ID,
      exits: { [OPPOSITE_DIRECTIONS[direction]]: source.id },
    });
    newRoom.layout.layer_id = layerId;
    newRoom.is_outdoor = Boolean(source.is_outdoor);

    applyWorldChange((currentWorld) => ({
      ...currentWorld,
      rooms: [
        ...currentWorld.rooms.map((room) => (
          room.id === source.id
            ? { ...room, exits: { ...(room.exits || {}), [direction]: newRoom.id } }
            : room
        )),
        newRoom,
      ],
    }));
    setSelectedRoomIds([newRoom.id]);
    setFocusRequest({ roomId: newRoom.id });
    setFocusNameToken((token) => token + 1);
    setApiStatus(`Dug ${direction} from ${source.id} → ${newRoom.id} (both exits wired).`);
    setApiError('');
  }, [applyWorldChange, selectedRoomIds]);

  function addRoom() {
    const current = worldRef.current;
    const occupied = occupiedCells(current.rooms);
    const anchor = selectedRoom ? getRoomPosition(selectedRoom, 0) : { x: 80, y: 80 };
    const [anchorCol, anchorRow] = positionToCell(anchor);
    const cell = nearestFreeCell(occupied, anchorCol, anchorRow);
    const nextRoom = makeRoom(current, { x: cell[0] * CELL_WIDTH, y: cell[1] * CELL_HEIGHT });
    applyWorldChange((currentWorld) => ({ ...currentWorld, rooms: [...currentWorld.rooms, nextRoom] }));
    setSelectedRoomIds([nextRoom.id]);
    setFocusRequest({ roomId: nextRoom.id });
    setFocusNameToken((token) => token + 1);
  }

  const deleteSelectedRooms = useCallback(() => {
    if (selectedRoomIds.length === 0) {
      return;
    }
    const names = selectedRoomIds.slice(0, 5).join(', ');
    const suffix = selectedRoomIds.length > 5 ? ` and ${selectedRoomIds.length - 5} more` : '';
    if (!window.confirm(`Delete ${selectedRoomIds.length} room(s): ${names}${suffix}? Exits pointing at them will be removed too.`)) {
      return;
    }
    const roomIdsToDelete = new Set(selectedRoomIds);
    applyWorldChange((current) => ({
      ...current,
      spawn_room_id: roomIdsToDelete.has(current.spawn_room_id) ? undefined : current.spawn_room_id,
      rooms: current.rooms
        .filter((room) => !roomIdsToDelete.has(room.id))
        .map((room) => {
          const exits = Object.fromEntries(
            Object.entries(room.exits || {}).filter(([, target]) => !roomIdsToDelete.has(target))
          );
          return {
            ...room,
            exits,
            mobs: (room.mobs || []).map((mob) => (
              Array.isArray(mob.patrol_rooms) && mob.patrol_rooms.some((roomId) => roomIdsToDelete.has(roomId))
                ? { ...mob, patrol_rooms: mob.patrol_rooms.filter((roomId) => !roomIdsToDelete.has(roomId)) }
                : mob
            )),
          };
        }),
      mobs: (current.mobs || []).filter((mob) => !roomIdsToDelete.has(mob.current_room)),
      scripts: (current.scripts || []).filter((script) => !roomIdsToDelete.has(script.room_id)),
    }));
    setSelectedRoomIds([]);
  }, [applyWorldChange, selectedRoomIds]);

  function handleRoomField(field, value) {
    if (!selectedRoom) {
      return;
    }
    if (field === 'id') {
      const nextId = value.trim();
      if (!nextId) {
        return;
      }
      if (worldRef.current.rooms.some((room) => room.id === nextId && room.id !== selectedRoom.id)) {
        setApiError(`Room id '${nextId}' is already taken.`);
        return;
      }
      setApiError('');
      const previousId = selectedRoom.id;
      applyWorldChange((current) => renameRoomEverywhere(current, previousId, nextId));
      setSelectedRoomIds((current) => current.map((roomId) => (roomId === previousId ? nextId : roomId)));
      return;
    }

    if (field === 'name' && roomIdFollowsName(selectedRoom)) {
      const previousId = selectedRoom.id;
      const slug = slugify(value);
      if (slug && slug !== previousId) {
        const existingIds = new Set(worldRef.current.rooms.map((room) => room.id));
        existingIds.delete(previousId);
        const nextId = uniqueRoomId(slug, existingIds);
        applyWorldChange((current) => {
          const renamed = renameRoomEverywhere(current, previousId, nextId);
          return {
            ...renamed,
            rooms: renamed.rooms.map((room) => (room.id === nextId ? { ...room, name: value } : room)),
          };
        }, { coalesceKey: 'room-name-slug' });
        setSelectedRoomIds((current) => current.map((roomId) => (roomId === previousId ? nextId : roomId)));
        return;
      }
    }

    const coalesceKey = field === 'name' || field === 'description'
      ? `${selectedRoom.id}:${field}`
      : undefined;
    updateRoom(selectedRoom.id, (room) => ({ ...room, [field]: value }), { coalesceKey });
  }

  function handleRoomLayerChange(layerId) {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      layout: { ...(room.layout || {}), layer_id: layerId },
    }));
  }

  function handleRoomTagsChange(tags) {
    if (!selectedRoom) {
      return;
    }
    const roomId = selectedRoom.id;
    // Auto-declare unknown tags in world.tags — the backend rejects rooms
    // referencing undeclared tags, and there is no separate tags editor.
    applyWorldChange((current) => {
      const knownTagIds = new Set((current.tags || []).map((tag) => tag.id));
      const newTagDefs = tags
        .filter((tag) => !knownTagIds.has(tag))
        .map((tag) => ({ id: tag, label: tag, color: '#6f7782', scope: ['room'] }));
      return {
        ...current,
        tags: newTagDefs.length ? [...(current.tags || []), ...newTagDefs] : current.tags,
        rooms: current.rooms.map((room) => (room.id === roomId ? { ...room, tags } : room)),
      };
    });
  }

  function handleJsonFieldCommit(field, parsed) {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => ({ ...room, [field]: parsed }));
  }

  // Exits ---------------------------------------------------------------------

  function addExit() {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      exits: { ...(room.exits || {}), [firstFreeDirection(room.exits)]: '' },
    }));
  }

  function handleExitDirectionChange(previousDirection, nextDirection) {
    if (!selectedRoom || !nextDirection || previousDirection === nextDirection) {
      return;
    }
    if ((selectedRoom.exits || {})[nextDirection] !== undefined) {
      setApiError(`'${selectedRoom.id}' already has a ${nextDirection} exit.`);
      return;
    }
    setApiError('');
    updateRoom(selectedRoom.id, (room) => {
      const exits = { ...(room.exits || {}) };
      const target = exits[previousDirection];
      delete exits[previousDirection];
      exits[nextDirection] = target || '';
      return { ...room, exits };
    });
  }

  function handleExitTargetChange(direction, targetRoomId) {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      exits: { ...(room.exits || {}), [direction]: targetRoomId },
    }));
  }

  function handleDeleteExit(direction) {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => {
      const exits = { ...(room.exits || {}) };
      delete exits[direction];
      return { ...room, exits };
    });
  }

  function handleAddReverseExit(direction) {
    if (!selectedRoom) {
      return;
    }
    const opposite = OPPOSITE_DIRECTIONS[direction];
    const targetRoomId = (selectedRoom.exits || {})[direction];
    if (!opposite || !targetRoomId) {
      return;
    }
    const sourceId = selectedRoom.id;
    updateRoom(targetRoomId, (room) => ({
      ...room,
      exits: { ...(room.exits || {}), [opposite]: sourceId },
    }));
  }

  // Items / mobs / scripts ------------------------------------------------------

  function nextCollectionId(room, field, prefix) {
    const existing = new Set((room[field] || []).map((entry) => entry.id));
    let counter = (room[field] || []).length + 1;
    while (existing.has(`${room.id}_${prefix}_${counter}`)) {
      counter += 1;
    }
    return `${room.id}_${prefix}_${counter}`;
  }

  function addItem() {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      items: [...(room.items || []), {
        id: nextCollectionId(room, 'items', 'item'),
        name: 'new item',
        description: '',
        type: 'item',
        weight: 1,
        value: 0,
        takeable: true,
      }],
    }));
  }

  function addMob(definition) {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => {
      const base = definition
        ? {
          name: definition.name,
          description: definition.description,
          strength: definition.strength,
          dexterity: definition.dexterity,
          max_stamina: definition.max_stamina,
          damage: definition.damage,
          aggressive: definition.aggressive,
          aggro_delay_min: definition.aggro_delay_min,
          aggro_delay_max: definition.aggro_delay_max,
          movement_interval: definition.movement_interval,
          // Template patrol routes reference live-world rooms; keep only the
          // ones that exist in this draft so validation stays green.
          patrol_rooms: (definition.patrol_rooms || []).filter(
            (roomId) => worldRef.current.rooms.some((candidate) => candidate.id === roomId)
          ),
          point_value: definition.point_value,
          pronouns: definition.pronouns,
          instant_death: definition.instant_death,
          loot_table: definition.loot_table || [],
        }
        : {
          name: 'new mob',
          description: '',
          strength: 10,
          dexterity: 10,
          max_stamina: 20,
          damage: 1,
          aggressive: false,
          movement_interval: 0,
          patrol_rooms: [],
          point_value: 0,
          pronouns: 'it',
          loot_table: [],
        };
      const idBase = definition ? definition.id : 'mob';
      const existing = new Set((room.mobs || []).map((mob) => mob.id));
      let counter = 1;
      while (existing.has(`${idBase}_${room.id}_${counter}`)) {
        counter += 1;
      }
      return {
        ...room,
        mobs: [...(room.mobs || []), {
          ...base,
          id: `${idBase}_${room.id}_${counter}`,
          type: 'mobile',
          current_room: room.id,
        }],
      };
    });
  }

  function addScript() {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      scripts: [...(room.scripts || []), {
        id: nextCollectionId(room, 'scripts', 'script'),
        path: `backend/world_scripts/${room.id}_script.py`,
        trigger: 'interact',
        content: 'def run(context):\n    return None\n',
      }],
    }));
  }

  function handleCollectionChange(field) {
    return (index, itemField, value) => {
      if (!selectedRoom) {
        return;
      }
      updateRoom(selectedRoom.id, (room) => ({
        ...room,
        [field]: (room[field] || []).map((entry, entryIndex) => (
          entryIndex === index ? { ...entry, [itemField]: value } : entry
        )),
      }), { coalesceKey: `${selectedRoom.id}:${field}:${index}:${itemField}` });
    };
  }

  function handleCollectionDelete(field) {
    return (index) => {
      if (!selectedRoom) {
        return;
      }
      updateRoom(selectedRoom.id, (room) => ({
        ...room,
        [field]: (room[field] || []).filter((entry, entryIndex) => entryIndex !== index),
      }));
    };
  }

  // Layout tools ---------------------------------------------------------------

  function runAutoLayout() {
    applyWorldChange((current) => ({ ...current, rooms: autoLayoutRooms(current) }));
    setFitViewToken((token) => token + 1);
    setApiStatus('Auto layout applied from exit directions.');
  }

  function snapSelectedToGrid() {
    const gridSize = finiteNumber(world.layout?.grid_size, 24) || 24;
    const targetRoomIds = selectedRoomIds.length ? selectedRoomIds : world.rooms.map((room) => room.id);
    updateRooms(targetRoomIds, (room) => {
      const position = getRoomPosition(room, 0);
      return setRoomPosition(room, snapValue(position.x, gridSize), snapValue(position.y, gridSize));
    });
  }

  function alignSelected(axis) {
    if (selectedRoomIds.length < 2 || !selectedRoom) {
      return;
    }
    const anchor = getRoomPosition(selectedRoom, 0);
    updateRooms(selectedRoomIds, (room) => {
      const position = getRoomPosition(room, 0);
      return setRoomPosition(
        room,
        axis === 'x' ? anchor.x : position.x,
        axis === 'y' ? anchor.y : position.y
      );
    });
  }

  function distributeSelected(axis) {
    if (selectedRoomIds.length < 3) {
      return;
    }
    const selectedRooms = world.rooms
      .filter((room) => selectedRoomIds.includes(room.id))
      .sort((left, right) => getRoomPosition(left, 0)[axis] - getRoomPosition(right, 0)[axis]);
    const first = getRoomPosition(selectedRooms[0], 0)[axis];
    const last = getRoomPosition(selectedRooms[selectedRooms.length - 1], 0)[axis];
    const gap = (last - first) / Math.max(selectedRooms.length - 1, 1);
    const positions = new Map(selectedRooms.map((room, index) => [room.id, first + gap * index]));
    updateRooms(selectedRoomIds, (room) => {
      const position = getRoomPosition(room, 0);
      return setRoomPosition(
        room,
        axis === 'x' ? positions.get(room.id) : position.x,
        axis === 'y' ? positions.get(room.id) : position.y
      );
    });
  }

  function applyBulkMetadata() {
    if (selectedRoomIds.length === 0) {
      return;
    }
    updateRooms(selectedRoomIds, (room) => ({
      ...room,
      region_id: bulkRegionId || room.region_id,
      layout: {
        ...(room.layout || {}),
        layer_id: bulkLayerId || roomLayerId(room, world),
      },
    }));
  }

  function toggleLayerVisibility(layerId) {
    setVisibleLayerIds((current) => (
      current.includes(layerId)
        ? current.filter((visibleLayerId) => visibleLayerId !== layerId)
        : [...current, layerId]
    ));
  }

  // Keyboard shortcuts -----------------------------------------------------------

  // Read through refs so the window listener and in-flight guards never run
  // stale closures (runWorldAction captures adminToken/selectedDraftId).
  const runWorldActionRef = useRef(null);
  runWorldActionRef.current = runWorldAction;
  const busyRef = useRef(false);
  busyRef.current = isBusy;

  useEffect(() => {
    function onKeyDown(event) {
      const isMeta = event.metaKey || event.ctrlKey;
      const inField = ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target?.tagName);
      if (isMeta && event.key.toLowerCase() === 's') {
        event.preventDefault();
        // Blur-commit editors (JSON, numbers, lists) flush on blur; give that
        // commit a tick to land before serializing the world.
        if (inField && typeof event.target.blur === 'function') {
          event.target.blur();
        }
        setTimeout(() => runWorldActionRef.current?.('save'), 0);
        return;
      }
      if (inField) {
        return;
      }
      if (isMeta && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        if (event.shiftKey) {
          redo();
        } else {
          undo();
        }
        return;
      }
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedRoomIds.length > 0) {
        event.preventDefault();
        deleteSelectedRooms();
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [undo, redo, deleteSelectedRooms, selectedRoomIds]);

  // Drafts ------------------------------------------------------------------------

  async function handleDraftSelect(nextDraftId, options = {}) {
    if (!nextDraftId || nextDraftId === selectedDraftId) {
      return;
    }
    if (!options.force && isDirty && !window.confirm('Switch drafts and discard unsaved changes?')) {
      return;
    }
    setIsBusy(true);
    setApiError('');
    setApiStatus('Loading draft...');
    try {
      const payload = await apiRequest(`/admin/api/world/drafts/${encodeURIComponent(nextDraftId)}`);
      applyLoadedWorld(payload, nextDraftId);
      setApiStatus('World loaded');
    } catch (error) {
      setApiError(error.message);
      setApiStatus('Draft load failed');
    } finally {
      setIsBusy(false);
    }
  }

  function openDraftDialog(mode, source = 'active') {
    if (mode === 'rename' && !selectedDraftId) {
      return;
    }
    const defaultName = source === 'live'
      ? 'Live Clone'
      : source === 'draft'
        ? `${currentDraft?.name || 'Draft'} Copy`
        : 'New Draft';
    setDraftDialog({
      mode,
      source,
      name: mode === 'rename' ? currentDraft?.name || 'Draft' : defaultName,
      description: mode === 'rename' ? currentDraft?.description || '' : '',
    });
  }

  function updateDraftDialog(field, value) {
    setDraftDialog((currentDialog) => (
      currentDialog ? { ...currentDialog, [field]: value } : currentDialog
    ));
  }

  async function submitDraftDialog(event) {
    event.preventDefault();
    if (!draftDialog) {
      return;
    }
    const name = draftDialog.name.trim();
    if (!name) {
      setApiError('Draft name is required.');
      return;
    }
    if (draftDialog.mode === 'create' && isDirty && !window.confirm('Create draft and discard unsaved changes?')) {
      return;
    }
    setIsBusy(true);
    setApiError('');
    setApiStatus(draftDialog.mode === 'rename' ? 'Renaming draft...' : 'Creating draft...');
    try {
      if (draftDialog.mode === 'rename') {
        const payload = await apiRequest(`/admin/api/world/drafts/${encodeURIComponent(selectedDraftId)}`, {
          method: 'PATCH',
          body: { name, description: draftDialog.description },
        });
        applyManifestPayload(payload);
        setCurrentDraft(payload.draft || currentDraft);
        setApiStatus('Draft renamed');
      } else {
        const payload = await apiRequest('/admin/api/world/drafts', {
          method: 'POST',
          body: {
            name,
            description: draftDialog.description,
            source: draftDialog.source,
            source_draft_id: draftDialog.source === 'draft' ? selectedDraftId : undefined,
          },
        });
        applyLoadedWorld(payload, payload.draft?.id || '');
        setApiStatus('Draft created');
      }
      setDraftDialog(null);
    } catch (error) {
      setApiError(error.message);
      setApiStatus(draftDialog.mode === 'rename' ? 'Draft rename failed' : 'Draft create failed');
    } finally {
      setIsBusy(false);
    }
  }

  async function deleteDraft() {
    if (!selectedDraftId || !window.confirm('Delete this draft project?')) {
      return;
    }
    setIsBusy(true);
    setApiError('');
    setApiStatus('Deleting draft...');
    try {
      const payload = await apiRequest(`/admin/api/world/drafts/${encodeURIComponent(selectedDraftId)}`, {
        method: 'DELETE',
      });
      applyManifestPayload(payload);
      const fallbackDraftId = payload.active_draft_id || payload.drafts?.[0]?.id || '';
      if (fallbackDraftId) {
        await handleDraftSelect(fallbackDraftId, { force: true });
      } else {
        setSelectedDraftId('');
        setCurrentDraft(null);
      }
      setApiStatus('Draft deleted');
    } catch (error) {
      setApiError(error.message);
      setApiStatus('Draft delete failed');
    } finally {
      setIsBusy(false);
    }
  }

  async function runWorldAction(action) {
    if (busyRef.current) {
      return;
    }
    const draftPath = selectedDraftId ? `/admin/api/world/drafts/${encodeURIComponent(selectedDraftId)}` : '/admin/api/world';
    const sentWorld = worldRef.current;
    const configs = {
      save: { path: draftPath, method: 'POST', body: { world: buildApiWorld(sentWorld) }, busy: 'Saving draft...' },
      validate: { path: '/admin/api/world/validate', method: 'POST', body: { world: buildApiWorld(sentWorld) }, busy: 'Validating world...' },
      apply: { path: selectedDraftId ? `${draftPath}/apply` : '/admin/api/world/apply', method: 'POST', body: { world: buildApiWorld(sentWorld) }, busy: 'Applying live world...' },
      reset: { path: selectedDraftId ? `${draftPath}/reset` : '/admin/api/world/reset', method: 'POST', busy: 'Resetting from baseline...' },
      publish: { path: selectedDraftId ? `${draftPath}/publish` : '/admin/api/world/publish', method: 'POST', body: { world: buildApiWorld(sentWorld) }, busy: 'Publishing through Git...' },
    };
    const config = configs[action];
    if (!config) {
      return;
    }
    if (action === 'apply' && !window.confirm('Apply this draft to the LIVE world? Connected players will see the change immediately.')) {
      return;
    }
    if (action === 'reset' && !window.confirm('Reset this draft to the generated baseline? The draft file on disk is overwritten and this cannot be undone.')) {
      return;
    }

    setIsBusy(true);
    setApiError('');
    setApiStatus(config.busy);
    try {
      const payload = await apiRequest(config.path, config);
      // Edits made while the request was in flight must survive: never
      // overwrite the local world or clear the dirty flag for a stale send.
      const worldUnchanged = worldRef.current === sentWorld;
      if (payload.world && (worldUnchanged || action === 'reset')) {
        applyLoadedWorld(payload, selectedDraftId);
      }
      if (payload.saved?.manifest) {
        applyManifestPayload(payload.saved.manifest);
      }
      if (payload.validation) {
        setValidation(payload.validation);
      }
      if (action !== 'validate' && worldUnchanged) {
        setIsDirty(false);
      }
      setApiStatus(summarizePayload(payload));
    } catch (error) {
      if (error.payload?.validation) {
        setValidation(error.payload.validation);
      }
      setApiError(error.message);
      setApiStatus(`${action} failed`);
    } finally {
      setIsBusy(false);
    }
  }

  function handleValidationIssueClick(issue) {
    const roomId = issue.room_id;
    if (roomId && world.rooms.some((room) => room.id === roomId)) {
      handleSelectRoom(roomId, false, true);
    }
  }

  // Render -------------------------------------------------------------------------

  const roomCount = world.rooms.length;
  const itemCount = world.rooms.reduce((count, room) => count + (room.items || []).length, 0);
  const mobCount = world.rooms.reduce((count, room) => count + (room.mobs || []).length, 0);
  const scriptCount = world.rooms.reduce((count, room) => count + (room.scripts || []).length, 0);
  // Stable identity matters: WorldGraph rebuilds its node set when this
  // array's identity changes.
  const visibleRooms = useMemo(() => {
    const visibleLayerIdSet = new Set(visibleLayerIds);
    return world.rooms.filter((room) => visibleLayerIdSet.has(roomLayerId(room, world)));
  }, [world, visibleLayerIds]);
  const spawnRoomId = effectiveSpawnRoomId(world);
  const errorCount = (validation.errors || []).length;
  const warningCount = (validation.warnings || []).length;

  return (
    <main className="admin-builder">
      <header className="admin-builder__topbar">
        <div>
          <h1>Admin World Builder</h1>
          <p>{adminToken ? 'Authenticated as stupidgem admin session.' : 'Waiting for stupidgem admin token.'}</p>
        </div>
        <div className="admin-builder__stats" aria-label="World summary">
          <span>{roomCount} rooms</span>
          <span>{itemCount} items</span>
          <span>{mobCount} mobs</span>
          <span>{scriptCount} scripts</span>
        </div>
        <div className="admin-builder__history">
          <button type="button" onClick={undo} disabled={!canUndo} title="Undo (⌘Z)">↶ Undo</button>
          <button type="button" onClick={redo} disabled={!canRedo} title="Redo (⇧⌘Z)">↷ Redo</button>
        </div>
      </header>

      <section className="draft-switcher" aria-label="Draft projects">
        <label className="draft-switcher__select">
          Draft project
          <select
            value={selectedDraftId}
            onChange={(event) => handleDraftSelect(event.target.value)}
            disabled={!adminToken || isBusy || drafts.length === 0}
          >
            {drafts.length === 0 ? <option value="">Legacy world</option> : null}
            {drafts.map((draft) => (
              <option key={draft.id} value={draft.id}>{formatDraftOption(draft)}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => openDraftDialog('create', 'active')} disabled={!adminToken || isBusy}>New Draft</button>
        <button type="button" onClick={() => openDraftDialog('create', 'draft')} disabled={!adminToken || isBusy || !selectedDraftId}>Duplicate Draft</button>
        <button type="button" onClick={() => openDraftDialog('create', 'live')} disabled={!adminToken || isBusy}>Clone Live</button>
        <button type="button" onClick={() => openDraftDialog('rename')} disabled={!adminToken || isBusy || !selectedDraftId}>Rename</button>
        <button type="button" onClick={deleteDraft} disabled={!adminToken || isBusy || drafts.length <= 1}>Delete</button>
        <div className="draft-switcher__status">
          <strong>{currentDraft ? `Editing Draft: ${currentDraft.name}` : 'Editing Legacy World'}</strong>
          <span>{activeDraftId && selectedDraftId === activeDraftId ? 'Active compatibility draft' : 'Live changes only after Apply Live'}</span>
          {isDirty ? <span className="draft-switcher__dirty">Unsaved changes</span> : null}
        </div>
        <div className="admin-builder__actions">
          <button type="button" onClick={loadWorld} disabled={!adminToken || isBusy}>Load World</button>
          <button type="button" onClick={() => runWorldAction('save')} disabled={!adminToken || isBusy || roomCount === 0}>Save Draft</button>
          <button type="button" onClick={() => runWorldAction('validate')} disabled={!adminToken || isBusy}>Validate</button>
          <button type="button" onClick={() => runWorldAction('apply')} disabled={!adminToken || isBusy}>Apply Live</button>
          <button type="button" onClick={() => runWorldAction('reset')} disabled={!adminToken || isBusy}>Reset Baseline</button>
          <button type="button" onClick={() => runWorldAction('publish')} disabled={!adminToken || isBusy}>Publish Git</button>
        </div>
      </section>

      {draftDialog ? (
        <div className="draft-dialog-backdrop">
          <form
            className="draft-dialog"
            role="dialog"
            aria-modal="true"
            aria-label={draftDialog.mode === 'rename' ? 'Rename draft project' : 'Create draft project'}
            onSubmit={submitDraftDialog}
          >
            <div className="draft-dialog__header">
              <h2>{draftDialog.mode === 'rename' ? 'Rename Draft' : 'New Draft Project'}</h2>
              <button type="button" onClick={() => setDraftDialog(null)} disabled={isBusy}>Close</button>
            </div>
            <label>
              Draft name
              <input
                value={draftDialog.name}
                onChange={(event) => updateDraftDialog('name', event.target.value)}
                disabled={isBusy}
              />
            </label>
            <label>
              Description
              <textarea
                value={draftDialog.description}
                onChange={(event) => updateDraftDialog('description', event.target.value)}
                disabled={isBusy}
                rows={3}
              />
            </label>
            {draftDialog.mode === 'create' ? (
              <label>
                Draft source
                <select
                  value={draftDialog.source}
                  onChange={(event) => updateDraftDialog('source', event.target.value)}
                  disabled={isBusy}
                >
                  <option value="active">Active draft</option>
                  <option value="draft" disabled={!selectedDraftId}>Selected draft</option>
                  <option value="live">Live baseline</option>
                </select>
              </label>
            ) : null}
            <div className="draft-dialog__actions">
              <button type="button" onClick={() => setDraftDialog(null)} disabled={isBusy}>Cancel</button>
              <button type="submit" disabled={isBusy || !draftDialog.name.trim()}>
                {draftDialog.mode === 'rename' ? 'Rename Draft' : 'Create Draft'}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      <section className="admin-builder__status" aria-live="polite">
        <strong>API status:</strong> {apiStatus}
        {apiError ? <div className="admin-builder__error" role="alert">{apiError}</div> : null}
      </section>

      <div className="admin-builder__workspace">
        <section className="admin-panel admin-panel--browser">
          <div className="admin-panel__header">
            <h2>Rooms</h2>
            <span>{roomCount}</span>
          </div>
          <RoomBrowser
            rooms={world.rooms}
            world={world}
            selectedRoomIds={selectedRoomIds}
            onSelectRoom={handleSelectRoom}
          />
        </section>

        <section className="admin-panel admin-panel--map">
          <div className="admin-panel__header">
            <h2>Map</h2>
            <div className="map-tools">
              <span className="dig-compass" role="group" aria-label="Dig new room">
                <span className="dig-compass__label">Dig</span>
                {DIG_DIRECTIONS.map((direction) => (
                  <button
                    key={direction}
                    type="button"
                    title={`Dig ${direction} from ${selectedRoom?.id || 'selected room'}`}
                    aria-label={`Dig ${direction}`}
                    disabled={!selectedRoom || Boolean((selectedRoom.exits || {})[direction])}
                    onClick={() => digRoom(direction)}
                  >
                    {DIG_LABELS[direction]}
                  </button>
                ))}
              </span>
              <button type="button" onClick={addRoom}>Add Room</button>
              <button type="button" onClick={runAutoLayout} disabled={roomCount === 0}>Auto Layout</button>
              <button type="button" onClick={snapSelectedToGrid} disabled={roomCount === 0}>Snap</button>
              <button type="button" onClick={() => alignSelected('x')} disabled={selectedCount < 2}>Align X</button>
              <button type="button" onClick={() => alignSelected('y')} disabled={selectedCount < 2}>Align Y</button>
              <button type="button" onClick={() => distributeSelected('x')} disabled={selectedCount < 3}>Dist X</button>
              <button type="button" onClick={() => distributeSelected('y')} disabled={selectedCount < 3}>Dist Y</button>
            </div>
          </div>
          {world.layers.length > 1 ? (
            <section className="layer-controls" aria-label="Map layers">
              {world.layers.map((layer) => (
                <label key={layer.id} className="layer-controls__item">
                  <input
                    type="checkbox"
                    aria-label={`Show ${(layer.name || layer.id).toLowerCase()} layer`}
                    checked={visibleLayerIds.includes(layer.id)}
                    onChange={() => toggleLayerVisibility(layer.id)}
                  />
                  <span>{layer.name || layer.id}</span>
                  <small>z {finiteNumber(layer.z, 0)}</small>
                </label>
              ))}
            </section>
          ) : null}
          <WorldGraph
            rooms={visibleRooms}
            world={world}
            selectedRoomIds={selectedRoomIds}
            spawnRoomId={spawnRoomId}
            fitViewToken={fitViewToken}
            focusRequest={focusRequest}
            onSelectRoom={handleSelectRoom}
            onSelectionChange={handleGraphSelection}
            onMoveRooms={handleMoveRooms}
            onConnectRooms={handleConnectRooms}
          />
        </section>

        <section className="admin-panel admin-panel--inspector">
          <div className="admin-panel__header">
            <h2>Inspector</h2>
            <button type="button" onClick={deleteSelectedRooms} disabled={selectedCount === 0}>
              Delete {selectedCount > 1 ? `${selectedCount} Rooms` : 'Room'}
            </button>
          </div>
          <Inspector
            room={selectedRoom}
            rooms={world.rooms}
            regions={world.regions}
            layers={world.layers}
            tags={world.tags}
            world={world}
            selectedCount={selectedCount}
            mobDefinitions={mobDefinitions}
            levels={levels}
            focusNameToken={focusNameToken}
            bulkRegionId={bulkRegionId}
            bulkLayerId={bulkLayerId}
            onBulkRegionChange={setBulkRegionId}
            onBulkLayerChange={setBulkLayerId}
            onApplyBulkMetadata={applyBulkMetadata}
            onFieldChange={handleRoomField}
            onLayerChange={handleRoomLayerChange}
            onTagsChange={handleRoomTagsChange}
            onJsonFieldCommit={handleJsonFieldCommit}
            onAddExit={addExit}
            onExitDirectionChange={handleExitDirectionChange}
            onExitTargetChange={handleExitTargetChange}
            onDeleteExit={handleDeleteExit}
            onAddReverseExit={handleAddReverseExit}
            onAddItem={addItem}
            onItemChange={handleCollectionChange('items')}
            onDeleteItem={handleCollectionDelete('items')}
            onAddMob={addMob}
            onMobChange={handleCollectionChange('mobs')}
            onDeleteMob={handleCollectionDelete('mobs')}
            onAddScript={addScript}
            onScriptChange={handleCollectionChange('scripts')}
            onDeleteScript={handleCollectionDelete('scripts')}
          />
        </section>
      </div>

      <details className="validation-drawer" open={errorCount > 0}>
        <summary>
          <span className={validation.ok ? 'admin-pill admin-pill--ok' : 'admin-pill admin-pill--bad'}>
            {validation.ok ? 'OK' : 'Blocked'}
          </span>
          Validation — {errorCount} errors, {warningCount} warnings
        </summary>
        <div className="validation-list">
          {errorCount === 0 && warningCount === 0 ? (
            <p className="admin-empty">No validation issues reported.</p>
          ) : null}
          {(validation.errors || []).map((issue, index) => (
            <button
              type="button"
              key={`error-${index}`}
              className="validation-list__item validation-list__item--error"
              onClick={() => handleValidationIssueClick(issue)}
            >
              <strong>{issue.code || 'error'}</strong>
              <span>{issue.message || String(issue)}</span>
            </button>
          ))}
          {(validation.warnings || []).map((issue, index) => (
            <button
              type="button"
              key={`warning-${index}`}
              className="validation-list__item validation-list__item--warning"
              onClick={() => handleValidationIssueClick(issue)}
            >
              <strong>{issue.code || 'warning'}</strong>
              <span>{issue.message || String(issue)}</span>
            </button>
          ))}
        </div>
      </details>
    </main>
  );
}
