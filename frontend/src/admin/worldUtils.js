export const DEFAULT_LAYER_ID = 'surface';
export const DEFAULT_REGION_ID = 'world';
export const DEFAULT_REGION_COLOR = '#4f8fba';

export const CANONICAL_DIRECTIONS = [
  'north', 'northeast', 'east', 'southeast',
  'south', 'southwest', 'west', 'northwest',
  'up', 'down', 'in', 'out',
];

export const OPPOSITE_DIRECTIONS = {
  north: 'south',
  south: 'north',
  east: 'west',
  west: 'east',
  northeast: 'southwest',
  southwest: 'northeast',
  northwest: 'southeast',
  southeast: 'northwest',
  up: 'down',
  down: 'up',
  in: 'out',
  out: 'in',
};

// Planar unit vectors for map layout. up/down/in/out are non-planar: null
// means "place near the source at the nearest free cell".
export const DIRECTION_VECTORS = {
  north: [0, -1],
  south: [0, 1],
  east: [1, 0],
  west: [-1, 0],
  northeast: [1, -1],
  northwest: [-1, -1],
  southeast: [1, 1],
  southwest: [-1, 1],
  up: null,
  down: null,
  in: null,
  out: null,
};

export const CELL_WIDTH = 200;
export const CELL_HEIGHT = 150;

export function finiteNumber(value, fallback = null) {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function slugify(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 48);
}

export function isAutoRoomId(roomId) {
  return /^(new-)?room[-_]\d+$/.test(roomId || '');
}

/**
 * A room id is "auto-managed" (safe to re-slug when the name changes) while it
 * is still a generated placeholder OR still tracks the slug of the current
 * name — i.e. the user has never set an id of their own.
 */
export function roomIdFollowsName(room) {
  return isAutoRoomId(room.id) || (Boolean(slugify(room.name)) && room.id === slugify(room.name));
}

export function uniqueRoomId(baseId, existingIds) {
  const base = baseId || 'room';
  if (!existingIds.has(base)) {
    return base;
  }
  let counter = 2;
  while (existingIds.has(`${base}_${counter}`)) {
    counter += 1;
  }
  return `${base}_${counter}`;
}

export function exitEntries(exits) {
  if (Array.isArray(exits)) {
    return exits
      .map((exit) => [exit.direction || exit.name || 'exit', exit.to || exit.target || exit.room || ''])
      .filter(([, target]) => target);
  }
  return Object.entries(exits || {});
}

export function firstFreeDirection(exits) {
  const taken = new Set(Object.keys(exits || {}));
  return CANONICAL_DIRECTIONS.find((direction) => !taken.has(direction)) || 'north';
}

export function reverseExitStatus(room, direction, targetRoom) {
  const opposite = OPPOSITE_DIRECTIONS[direction];
  if (!targetRoom) {
    return { state: 'none' };
  }
  const targetExits = targetRoom.exits || {};
  if (opposite && targetExits[opposite] === room.id) {
    return { state: 'linked', opposite };
  }
  if (exitEntries(targetExits).some(([, backTarget]) => backTarget === room.id)) {
    return { state: 'linked-other' };
  }
  if (!opposite) {
    return { state: 'no-opposite' };
  }
  if (targetExits[opposite]) {
    return { state: 'blocked', opposite };
  }
  return { state: 'missing', opposite };
}

// Item/room helpers -----------------------------------------------------------

const UNSERIALIZABLE = (value) => Boolean(value && typeof value === 'object' && value.unserializable);

export function itemHasStrippedLogic(item) {
  const interactionLists = Object.values(item?.interactions || {});
  return interactionLists.some((list) => (Array.isArray(list) ? list : []).some(
    (entry) => UNSERIALIZABLE(entry?.conditional_fn) || UNSERIALIZABLE(entry?.effect_fn)
  ));
}

export function roomHasStrippedLogic(room) {
  if ((room?.items || []).some(itemHasStrippedLogic)) {
    return true;
  }
  if ((room?.hidden_items || []).length > 0) {
    return true;
  }
  const triggers = room?.speech_triggers;
  return Boolean(triggers && Object.keys(triggers).length > 0);
}

export function roomHasPuzzle(room) {
  return (room?.items || []).some(
    (item) => item.type === 'stateful_item' || item.type === 'container_item'
  );
}

// Normalization ---------------------------------------------------------------

export function emptyWorld() {
  return {
    version: 1,
    metadata: {},
    regions: [{ id: DEFAULT_REGION_ID, name: 'World', color: DEFAULT_REGION_COLOR }],
    layers: [{ id: DEFAULT_LAYER_ID, name: 'Surface', z: 0, visible: true }],
    tags: [],
    layout: { grid_size: 24, snap_to_grid: true, default_layer_id: DEFAULT_LAYER_ID },
    rooms: [],
  };
}

export function normalizeRegions(regions) {
  const normalized = Array.isArray(regions) ? regions : [];
  if (normalized.length === 0) {
    return [{ id: DEFAULT_REGION_ID, name: 'World', color: DEFAULT_REGION_COLOR }];
  }
  return normalized.map((region, index) => ({
    color: DEFAULT_REGION_COLOR,
    ...region,
    id: region.id || `region-${index + 1}`,
    name: region.name || region.id || `Region ${index + 1}`,
  }));
}

export function normalizeLayers(layers) {
  const normalized = Array.isArray(layers) ? layers : [];
  if (normalized.length === 0) {
    return [{ id: DEFAULT_LAYER_ID, name: 'Surface', z: 0, visible: true }];
  }
  return normalized.map((layer, index) => ({
    ...layer,
    id: layer.id || `layer-${index + 1}`,
    name: layer.name || layer.id || `Layer ${index + 1}`,
    z: finiteNumber(layer.z, 0),
    visible: layer.visible !== false,
  }));
}

export function normalizeTags(tags) {
  return (Array.isArray(tags) ? tags : []).map((tag, index) => ({
    color: '#6f7782',
    scope: ['room'],
    ...tag,
    id: tag.id || `tag-${index + 1}`,
    label: tag.label || tag.name || tag.id || `Tag ${index + 1}`,
  }));
}

export function normalizeRoom(room, index) {
  const legacyX = finiteNumber(room.x);
  const legacyY = finiteNumber(room.y);
  const legacyZ = finiteNumber(room.z, 0);
  const sourceLayout = room.layout || {};
  const layoutX = finiteNumber(sourceLayout.x, legacyX);
  const layoutY = finiteNumber(sourceLayout.y, legacyY);
  const layoutLayerId = sourceLayout.layer_id || room.layer_id || DEFAULT_LAYER_ID;
  const nextLayout = {
    ...sourceLayout,
    x: layoutX,
    y: layoutY,
    layer_id: layoutLayerId,
    pinned: sourceLayout.pinned ?? (layoutX !== null && layoutY !== null),
  };

  return {
    ...room,
    id: room.id || `room-${index + 1}`,
    name: room.name || room.title || room.id || `Room ${index + 1}`,
    description: room.description || '',
    x: layoutX,
    y: layoutY,
    z: legacyZ,
    region_id: room.region_id || DEFAULT_REGION_ID,
    tags: Array.isArray(room.tags) ? room.tags : [],
    layout: nextLayout,
    exits: room.exits || {},
    items: Array.isArray(room.items) ? room.items : [],
    mobs: Array.isArray(room.mobs) ? room.mobs : [],
    scripts: Array.isArray(room.scripts) ? room.scripts : [],
  };
}

export function normalizeWorld(world) {
  const source = world || emptyWorld();
  const sourceMobs = Array.isArray(source.mobs) ? source.mobs : [];
  const sourceScripts = Array.isArray(source.scripts) ? source.scripts : [];
  const regions = normalizeRegions(source.regions);
  const layers = normalizeLayers(source.layers);
  const tags = normalizeTags(source.tags);
  const layout = {
    grid_size: 24,
    snap_to_grid: true,
    default_layer_id: layers[0]?.id || DEFAULT_LAYER_ID,
    ...(source.layout || {}),
  };
  const rooms = Array.isArray(source.rooms)
    ? source.rooms.map(normalizeRoom)
    : Object.entries(source.rooms || {}).map(([id, room], index) => normalizeRoom({ id, ...room }, index));
  return {
    ...source,
    version: source.version || 1,
    metadata: source.metadata || {},
    regions,
    layers,
    tags,
    layout,
    rooms: rooms.map((room) => ({
      ...room,
      region_id: room.region_id || regions[0]?.id || DEFAULT_REGION_ID,
      layout: {
        ...room.layout,
        layer_id: room.layout?.layer_id || layout.default_layer_id || layers[0]?.id || DEFAULT_LAYER_ID,
      },
      mobs: [
        ...(room.mobs || []),
        ...sourceMobs.filter((mob) => mob.current_room === room.id),
      ],
      scripts: [
        ...(room.scripts || []),
        ...sourceScripts.filter((script) => script.room_id === room.id),
      ],
    })),
  };
}

export function buildApiWorld(world) {
  const roomIds = new Set((world.rooms || []).map((room) => room.id));
  const roomMobs = [];
  const roomScripts = [];
  const rooms = (world.rooms || []).map((room) => {
    const { mobs = [], scripts = [], ...roomData } = room;
    const layout = roomData.layout || {};
    mobs.forEach((mob) => {
      roomMobs.push({ ...mob, current_room: room.id });
    });
    scripts.forEach((script) => {
      roomScripts.push({ ...script, room_id: room.id });
    });
    const x = finiteNumber(layout.x, roomData.x);
    const y = finiteNumber(layout.y, roomData.y);
    const apiRoom = {
      ...roomData,
      z: finiteNumber(roomData.z, 0),
      layout: {
        ...layout,
        layer_id: layout.layer_id || roomData.layer_id || world.layout?.default_layer_id || DEFAULT_LAYER_ID,
      },
    };
    // Unplaced rooms omit coordinates entirely — a null coordinate is not a
    // position, and the backend rejects non-finite values.
    if (x === null) {
      delete apiRoom.x;
      delete apiRoom.layout.x;
    } else {
      apiRoom.x = x;
      apiRoom.layout.x = x;
    }
    if (y === null) {
      delete apiRoom.y;
      delete apiRoom.layout.y;
    } else {
      apiRoom.y = y;
      apiRoom.layout.y = y;
    }
    return apiRoom;
  });

  const unassignedMobs = (world.mobs || []).filter((mob) => !roomIds.has(mob.current_room));
  const unassignedScripts = (world.scripts || []).filter((script) => !roomIds.has(script.room_id));

  return {
    ...world,
    rooms,
    mobs: [...unassignedMobs, ...roomMobs],
    scripts: [...unassignedScripts, ...roomScripts],
  };
}

// Positioning -----------------------------------------------------------------

export function getRoomPosition(room, index = 0) {
  const x = finiteNumber(room.layout?.x, finiteNumber(room.x, 120 + (index % 5) * CELL_WIDTH));
  const y = finiteNumber(room.layout?.y, finiteNumber(room.y, 110 + Math.floor(index / 5) * CELL_HEIGHT));
  return { x, y };
}

export function roomLayerId(room, world) {
  return room.layout?.layer_id || world.layout?.default_layer_id || world.layers?.[0]?.id || DEFAULT_LAYER_ID;
}

export function setRoomPosition(room, x, y) {
  return {
    ...room,
    x,
    y,
    layout: {
      ...(room.layout || {}),
      x,
      y,
      pinned: true,
    },
  };
}

export function snapValue(value, gridSize) {
  return Math.round(Number(value || 0) / gridSize) * gridSize;
}

export function roomsNeedLayout(rooms) {
  if (!rooms.length) {
    return false;
  }
  const unplaced = rooms.filter((room) => finiteNumber(room.layout?.x, finiteNumber(room.x)) === null);
  return unplaced.length >= Math.ceil(rooms.length / 2);
}

export function cellKey(col, row) {
  return `${col},${row}`;
}

export function positionToCell(position) {
  return [Math.round(position.x / CELL_WIDTH), Math.round(position.y / CELL_HEIGHT)];
}

// Deterministic outward spiral used to resolve grid-cell collisions.
function* spiralOffsets() {
  yield [0, 0];
  for (let radius = 1; radius < 24; radius += 1) {
    for (let dx = -radius; dx <= radius; dx += 1) {
      yield [dx, -radius];
    }
    for (let dy = -radius + 1; dy <= radius; dy += 1) {
      yield [radius, dy];
    }
    for (let dx = radius - 1; dx >= -radius; dx -= 1) {
      yield [dx, radius];
    }
    for (let dy = radius - 1; dy >= -radius + 1; dy -= 1) {
      yield [-radius, dy];
    }
  }
}

export function nearestFreeCell(occupied, col, row) {
  for (const [dx, dy] of spiralOffsets()) {
    const candidate = [col + dx, row + dy];
    if (!occupied.has(cellKey(candidate[0], candidate[1]))) {
      return candidate;
    }
  }
  return [col, row];
}

export function effectiveSpawnRoomId(world) {
  const rooms = world.rooms || [];
  if (world.spawn_room_id && rooms.some((room) => room.id === world.spawn_room_id)) {
    return world.spawn_room_id;
  }
  if (rooms.some((room) => room.id === 'square')) {
    return 'square';
  }
  return rooms[0]?.id || null;
}

/**
 * Lay rooms out on a grid using exit direction semantics (north above, east
 * right, ...). BFS from the spawn room; up/down/in/out neighbours land on the
 * nearest free cell. Disconnected components stack below the previous one.
 * With onlyUnplaced, rooms that already have coordinates keep them and act as
 * fixed anchors for the rest.
 */
export function autoLayoutRooms(world, { onlyUnplaced = false } = {}) {
  const rooms = world.rooms || [];
  if (rooms.length === 0) {
    return rooms;
  }

  const roomById = new Map(rooms.map((room) => [room.id, room]));
  const occupied = new Map();
  const cellByRoomId = new Map();
  const keepPosition = new Set();

  const place = (roomId, col, row) => {
    const [freeCol, freeRow] = occupied.has(cellKey(col, row))
      ? nearestFreeCell(occupied, col, row)
      : [col, row];
    occupied.set(cellKey(freeCol, freeRow), roomId);
    cellByRoomId.set(roomId, [freeCol, freeRow]);
  };

  if (onlyUnplaced) {
    rooms.forEach((room) => {
      const x = finiteNumber(room.layout?.x, finiteNumber(room.x));
      const y = finiteNumber(room.layout?.y, finiteNumber(room.y));
      if (x !== null && y !== null) {
        const [col, row] = positionToCell({ x, y });
        occupied.set(cellKey(col, row), room.id);
        cellByRoomId.set(room.id, [col, row]);
        keepPosition.add(room.id);
      }
    });
  }

  const bfsFrom = (startRoomId, startCol, startRow) => {
    place(startRoomId, startCol, startRow);
    const queue = [startRoomId];
    while (queue.length > 0) {
      const currentId = queue.shift();
      const current = roomById.get(currentId);
      const [col, row] = cellByRoomId.get(currentId);
      for (const [direction, targetId] of exitEntries(current?.exits)) {
        if (!roomById.has(targetId) || cellByRoomId.has(targetId)) {
          continue;
        }
        const vector = DIRECTION_VECTORS[direction];
        const target = vector
          ? [col + vector[0], row + vector[1]]
          : nearestFreeCell(occupied, col, row + 1);
        place(targetId, target[0], target[1]);
        queue.push(targetId);
      }
    }
  };

  const spawnId = effectiveSpawnRoomId(world);
  let nextComponentRow = 0;
  const componentSeeds = [spawnId, ...rooms.map((room) => room.id)].filter(Boolean);
  for (const seedId of componentSeeds) {
    if (cellByRoomId.has(seedId)) {
      continue;
    }
    bfsFrom(seedId, 0, nextComponentRow);
    const maxRow = Math.max(...Array.from(cellByRoomId.values()).map(([, row]) => row));
    nextComponentRow = maxRow + 2;
  }

  const cols = Array.from(cellByRoomId.values()).map(([col]) => col);
  const rows = Array.from(cellByRoomId.values()).map(([, row]) => row);
  const minCol = Math.min(...cols);
  const minRow = Math.min(...rows);

  // When anchored to existing positions, keep the established coordinate
  // frame instead of re-normalizing to the top-left.
  const originCol = keepPosition.size > 0 ? 0 : minCol;
  const originRow = keepPosition.size > 0 ? 0 : minRow;
  const originOffset = keepPosition.size > 0 ? 0 : 80;

  return rooms.map((room) => {
    const cell = cellByRoomId.get(room.id);
    if (!cell || keepPosition.has(room.id)) {
      return room;
    }
    const x = originOffset + (cell[0] - originCol) * CELL_WIDTH;
    const y = originOffset + (cell[1] - originRow) * CELL_HEIGHT;
    return setRoomPosition(room, x, y);
  });
}

/**
 * Infer a compass direction from the relative position of two rooms,
 * preferring a direction that is still free on the source room.
 */
export function directionBetween(sourcePosition, targetPosition, takenDirections = new Set()) {
  const dx = targetPosition.x - sourcePosition.x;
  const dy = targetPosition.y - sourcePosition.y;
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
  const compass = ['east', 'southeast', 'south', 'southwest', 'west', 'northwest', 'north', 'northeast'];
  const index = Math.round(((angle + 360) % 360) / 45) % 8;
  const ordered = [];
  for (let offset = 0; offset < 8; offset += 1) {
    const clockwise = compass[(index + offset) % 8];
    const counter = compass[(index - offset + 8) % 8];
    [clockwise, counter].forEach((direction) => {
      if (!ordered.includes(direction)) {
        ordered.push(direction);
      }
    });
  }
  return ordered.find((direction) => !takenDirections.has(direction)) || null;
}

export function makeRoom(world, overrides = {}) {
  const rooms = world.rooms || [];
  const existingIds = new Set(rooms.map((room) => room.id));
  let roomNumber = rooms.length + 1;
  while (existingIds.has(`room_${roomNumber}`)) {
    roomNumber += 1;
  }
  const defaultLayerId = world.layout?.default_layer_id || world.layers?.[0]?.id || DEFAULT_LAYER_ID;
  const x = overrides.x ?? 80;
  const y = overrides.y ?? 80;
  return {
    id: `room_${roomNumber}`,
    name: 'New Room',
    description: '',
    z: 0,
    region_id: world.regions?.[0]?.id || DEFAULT_REGION_ID,
    tags: [],
    exits: {},
    items: [],
    mobs: [],
    scripts: [],
    ...overrides,
    x,
    y,
    layout: { x, y, layer_id: overrides.layout?.layer_id || defaultLayerId, pinned: true },
  };
}

export function formatJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}
