// App.js
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import io from 'socket.io-client';
import { Background, Controls, MiniMap, ReactFlow, ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './App.css';

const ADMIN_PATH = '/admin/world-builder';
const DEFAULT_LAYER_ID = 'surface';
const DEFAULT_REGION_ID = 'world';
const DEFAULT_REGION_COLOR = '#4f8fba';
const FLOW_FIT_VIEW_OPTIONS = { padding: 0.24 };
const FLOW_MULTI_SELECTION_KEYS = ['Meta', 'Control', 'Shift'];

function getBackendUrl() {
  return process.env.NODE_ENV === 'production'
    ? 'https://api.realms.lordos.tech:8080'
    : 'http://localhost:8080';
}

function emptyWorld() {
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

function finiteNumber(value, fallback = null) {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizeRegions(regions) {
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

function normalizeLayers(layers) {
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

function normalizeTags(tags) {
  return (Array.isArray(tags) ? tags : []).map((tag, index) => ({
    color: '#6f7782',
    scope: ['room'],
    ...tag,
    id: tag.id || `tag-${index + 1}`,
    label: tag.label || tag.name || tag.id || `Tag ${index + 1}`,
  }));
}

function normalizeRoom(room, index) {
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

function normalizeWorld(world) {
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

function buildApiWorld(world) {
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
    return {
      ...roomData,
      x: finiteNumber(layout.x, roomData.x),
      y: finiteNumber(layout.y, roomData.y),
      z: finiteNumber(roomData.z, 0),
      layout: {
        ...layout,
        x: finiteNumber(layout.x, roomData.x),
        y: finiteNumber(layout.y, roomData.y),
        layer_id: layout.layer_id || roomData.layer_id || world.layout?.default_layer_id || DEFAULT_LAYER_ID,
      },
    };
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

function makeDefaultRoom(index) {
  const x = 160 + (index % 5) * 120;
  const y = 140 + Math.floor(index / 5) * 90;
  return {
    id: `new-room-${index + 1}`,
    name: `New Room ${index + 1}`,
    description: '',
    x,
    y,
    z: 0,
    region_id: DEFAULT_REGION_ID,
    tags: [],
    layout: { x, y, layer_id: DEFAULT_LAYER_ID, pinned: true },
    exits: {},
    items: [],
    mobs: [],
    scripts: [],
  };
}

function makeRoomForWorld(world) {
  const existingRoomIds = new Set((world.rooms || []).map((room) => room.id));
  let roomNumber = (world.rooms || []).length + 1;
  while (existingRoomIds.has(`new-room-${roomNumber}`)) {
    roomNumber += 1;
  }

  const room = makeDefaultRoom(roomNumber - 1);
  const defaultLayerId = world.layout?.default_layer_id || world.layers?.[0]?.id || DEFAULT_LAYER_ID;
  return {
    ...room,
    region_id: world.regions?.[0]?.id || DEFAULT_REGION_ID,
    layout: {
      ...room.layout,
      layer_id: defaultLayerId,
    },
  };
}

function getRoomPosition(room, index) {
  const x = finiteNumber(room.layout?.x, finiteNumber(room.x, 120 + (index % 5) * 150));
  const y = finiteNumber(room.layout?.y, finiteNumber(room.y, 110 + Math.floor(index / 5) * 120));
  return { x, y };
}

function roomLayerId(room, world) {
  return room.layout?.layer_id || world.layout?.default_layer_id || world.layers?.[0]?.id || DEFAULT_LAYER_ID;
}

function snapValue(value, gridSize) {
  return Math.round(Number(value || 0) / gridSize) * gridSize;
}

function setRoomPosition(room, x, y) {
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

function sameStringArray(left, right) {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((value, index) => value === right[index]);
}

function exitEntries(exits) {
  if (Array.isArray(exits)) {
    return exits
      .map((exit) => [exit.direction || exit.name || 'exit', exit.to || exit.target || exit.room || ''])
      .filter(([, target]) => target);
  }
  return Object.entries(exits || {});
}

function formatJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function summarizePayload(payload) {
  if (payload.publish) {
    if (payload.publish.ok === false) {
      return `Publish failed: ${payload.publish.error || payload.publish.step || 'unknown error'}`;
    }
    const commit = payload.publish.commit ? ` (${payload.publish.commit})` : '';
    return `Publish complete${commit}`;
  }
  if (payload.applied) {
    const rooms = payload.applied.rooms ?? 0;
    const mobs = payload.applied.mobs ?? 0;
    return `Applied live: ${rooms} rooms, ${mobs} mobs`;
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
  const updatedAt = draft.updated_at ? ` - ${draft.updated_at}` : '';
  return `${draft.name} - ${roomCount}${updatedAt}`;
}

function App() {
  const isAdminRoute = window.location.pathname === ADMIN_PATH;

  // Track whether we are in 'login' or 'game' phase
  const [phase, setPhase] = useState("login");

  // Terminal text log
  const [messages, setMessages] = useState(["* "]);

  // Current command input
  const [command, setCommand] = useState("");

  // Command history
  const [commandHistory, setCommandHistory] = useState([]);
  const [historyPosition, setHistoryPosition] = useState(0);

  // Whether to show password or text
  const [inputType, setInputType] = useState("text");

  // HUD data
  const [playerName, setPlayerName] = useState("");
  const [playerScore, setPlayerScore] = useState(0);
  const [playerStamina, setPlayerStamina] = useState(0);
  const [maxStamina, setMaxStamina] = useState(0);

  // Whether the input is disabled (e.g., after connection closed)
  const [inputDisabled, setInputDisabled] = useState(false);

  const [adminToken, setAdminToken] = useState(() => localStorage.getItem('adminToken') || '');

  // Socket and refs for scrolling and input selection
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current && messagesEndRef.current.scrollIntoView) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Establish Socket.IO connection on mount
  useEffect(() => {
    const SOCKET_URL = getBackendUrl();

    socketRef.current = io(SOCKET_URL, {
      transports: ['websocket'],
      reconnection: false,   // Disable auto-reconnection
      pingInterval: 60000,   // 60 seconds (in ms)
      pingTimeout: 180000,    // 180 seconds (in ms)
    });

    // On successful connect
    socketRef.current.on('connect', () => {
      console.log('Connected to backend.');
    });

    // If the server forcibly disconnects or the connection is lost
    socketRef.current.on('disconnect', () => {
      setMessages((prev) => [...prev, "Connection lost."]);
      setInputDisabled(true);
    });

    // Listen for general messages from the server
    socketRef.current.on('message', (msg) => {
      setMessages((prev) => {
        let newMessages = [...prev];
        if (newMessages.length > 0 && newMessages[newMessages.length - 1] === "* ") {
          newMessages.pop();
        }
        return [...newMessages, msg, "* "];
      });
    });

    // Listen for input type changes (e.g., switching to password mode)
    socketRef.current.on('setInputType', (type) => {
      setInputType(type);
    });

    // Listen for stats updates (HUD)
    socketRef.current.on('statsUpdate', (data) => {
      setPlayerName(data.name);
      setPlayerScore(data.score);
      setPlayerStamina(data.stamina);
      setMaxStamina(data.max_stamina);
      setPhase("game");
    });

    socketRef.current.on('adminToken', (payload) => {
      const token = typeof payload === 'string' ? payload : payload?.token;
      if (!token) {
        return;
      }
      localStorage.setItem('adminToken', token);
      setAdminToken(token);
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  const clearAdminToken = useCallback(() => {
    localStorage.removeItem('adminToken');
    setAdminToken('');
  }, []);

  // Handle command submission
  const handleCommandSubmit = (e) => {
    e.preventDefault();
    if (inputDisabled) {
      return;
    }

    // In game phase, if blank input is entered, just add a new prompt line and do nothing else.
    if (command.trim() === "" && phase === "game") {
      setMessages((prev) => [...prev, "* "]);
      return;
    }

    // For password input, never allow blank submissions
    if (command.trim() === "" && inputType === "password") {
      return; // Simply do nothing - don't send blank passwords
    }

    // For login phase, blank input is allowed and sent to the server.
    let outputCommand = command;
    if (inputType === "password") {
      outputCommand = "*".repeat(command.length);
    }
    setMessages((prev) => {
      let newMessages = [...prev];
      if (newMessages.length > 0 && newMessages[newMessages.length - 1] === "* ") {
        newMessages.pop();
      }
      newMessages.push(`* ${outputCommand}`);
      newMessages.push("* ");
      return newMessages;
    });
    socketRef.current.emit('command', command);

    // Only clear input during auth phase, keep it in game phase
    if (phase !== "game") {
      setCommand("");
    } else {
      // Add command to history if it has content and isn't a duplicate of the last command
      if (command.trim() !== "") {
        setCommandHistory(prevHistory => {
          if (prevHistory.length === 0 || prevHistory[0] !== command) {
            return [command, ...prevHistory]; // Add to front of array
          }
          return prevHistory;
        });
      }

      // Reset history position
      setHistoryPosition(0);

      // Select all text for easy overtyping
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.select();
        }
      }, 10);
    }
  };

  // Handle up/down arrow keys for command history
  const handleKeyDown = (e) => {
    // Only process in game phase
    if (phase !== "game") {
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();

      // If we're already at the end of history, don't go further
      if (historyPosition >= commandHistory.length) {
        return;
      }

      // If we're at position 0 (current command) and it's not in history yet,
      // and it has content, add it to history
      if (historyPosition === 0 && command.trim() !== "" &&
          (commandHistory.length === 0 || commandHistory[0] !== command)) {
        setCommandHistory(prev => [command, ...prev]);
      }

      // Move to the next position in history
      const newPosition = historyPosition + 1;
      setHistoryPosition(newPosition);

      // Set command to the history item (if available)
      if (newPosition <= commandHistory.length) {
        setCommand(commandHistory[newPosition - 1]);
      }
    }
    else if (e.key === "ArrowDown") {
      e.preventDefault();

      // If we're at position 0, can't go further down
      if (historyPosition <= 0) {
        return;
      }

      // Move to previous position in history
      const newPosition = historyPosition - 1;
      setHistoryPosition(newPosition);

      // If we're back to position 0, clear command
      if (newPosition === 0) {
        setCommand("");
      } else {
        // Set command to the history item
        setCommand(commandHistory[newPosition - 1]);
      }
    }
  };

  if (isAdminRoute) {
    return (
      <AdminRouteShell
        adminToken={adminToken}
        onAdminTokenInvalid={clearAdminToken}
        messages={messages}
        messagesEndRef={messagesEndRef}
        command={command}
        setCommand={setCommand}
        inputType={inputType}
        inputDisabled={inputDisabled}
        inputRef={inputRef}
        handleCommandSubmit={handleCommandSubmit}
        handleKeyDown={handleKeyDown}
      />
    );
  }

  return (
    <GameTerminal
      playerName={playerName}
      playerScore={playerScore}
      playerStamina={playerStamina}
      maxStamina={maxStamina}
      messages={messages}
      messagesEndRef={messagesEndRef}
      command={command}
      setCommand={setCommand}
      inputType={inputType}
      inputDisabled={inputDisabled}
      inputRef={inputRef}
      handleCommandSubmit={handleCommandSubmit}
      handleKeyDown={handleKeyDown}
    />
  );
}

function AdminRouteShell({
  adminToken,
  onAdminTokenInvalid,
  messages,
  messagesEndRef,
  command,
  setCommand,
  inputType,
  inputDisabled,
  inputRef,
  handleCommandSubmit,
  handleKeyDown,
}) {
  return (
    <>
      <AdminWorldBuilder adminToken={adminToken} onAdminTokenInvalid={onAdminTokenInvalid} />
      {!adminToken ? (
        <AdminLoginPanel
          messages={messages}
          messagesEndRef={messagesEndRef}
          command={command}
          setCommand={setCommand}
          inputType={inputType}
          inputDisabled={inputDisabled}
          inputRef={inputRef}
          handleCommandSubmit={handleCommandSubmit}
          handleKeyDown={handleKeyDown}
        />
      ) : null}
    </>
  );
}

function AdminLoginPanel({
  messages,
  messagesEndRef,
  command,
  setCommand,
  inputType,
  inputDisabled,
  inputRef,
  handleCommandSubmit,
  handleKeyDown,
}) {
  return (
    <aside className="admin-login-panel" aria-label="Admin login panel">
      <div className="admin-login-panel__log">
        {messages.slice(-8).map((message, index) => (
          <pre key={`${message}-${index}`}>{message}</pre>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleCommandSubmit} className="admin-login-panel__form">
        <input
          ref={inputRef}
          type={inputType}
          placeholder={inputDisabled ? 'Connection Closed' : 'Type your admin login command...'}
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={inputDisabled}
        />
      </form>
    </aside>
  );
}

function GameTerminal({
  playerName,
  playerScore,
  playerStamina,
  maxStamina,
  messages,
  messagesEndRef,
  command,
  setCommand,
  inputType,
  inputDisabled,
  inputRef,
  handleCommandSubmit,
  handleKeyDown,
}) {
  return (
    <div style={{ fontFamily: "monospace", height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Top bar / HUD */}
      <div style={{ backgroundColor: "#fe01ff", color: "#000", padding: "0.5rem" }}>
        {playerName
          ? <strong>{playerName} | Score: {playerScore}, Stamina: {playerStamina}/{maxStamina}</strong>
          : <strong>The Forgotten Realms</strong>
        }
      </div>

      {/* Main text area (blue screen) */}
      <div
        style={{
          flex: 1,
          backgroundColor: "#02ffff",
          color: "#000000",
          padding: "0.5rem",
          overflowY: "auto"
        }}
      >
        {/* Wrap text output in a container limited to 50% width */}
        <div className="output-container">
          {messages.map((msg, index) => (
            <pre key={index}>{msg}</pre>
          ))}
        </div>
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <form onSubmit={handleCommandSubmit} style={{ backgroundColor: "#ffff00", padding: "0.5rem" }}>
        <input
          ref={inputRef}
          type={inputType}
          placeholder={inputDisabled ? "Connection Closed" : "Type your command...."}
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={inputDisabled}
          style={{
            width: "100%",
            border: "none",
            outline: "none",
            backgroundColor: "#ffff00",
            fontFamily: "monospace"
          }}
        />
      </form>
    </div>
  );
}

function AdminWorldBuilder({ adminToken, onAdminTokenInvalid }) {
  const [world, setWorld] = useState(emptyWorld());
  const [selectedRoomId, setSelectedRoomId] = useState('');
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

  const apiRequest = useCallback(async (path, options = {}) => {
    if (!adminToken) {
      throw new Error('Waiting for stupidgem admin token.');
    }

    const method = options.method || 'GET';
    const headers = {
      Authorization: `Bearer ${adminToken}`,
    };
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
      throw new Error(message);
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
    const nextWorld = normalizeWorld(payload.world);
    const nextSelectedRoomId = nextWorld.rooms[0]?.id || '';
    const nextVisibleLayerIds = nextWorld.layers.filter((layer) => layer.visible !== false).map((layer) => layer.id);
    const payloadDrafts = payload.drafts || payload.manifest?.drafts || [];
    const payloadActiveDraftId = payload.active_draft_id || payload.manifest?.active_draft_id || '';
    const payloadDraft = payload.draft
      || payloadDrafts.find((draft) => draft.id === fallbackDraftId)
      || payloadDrafts.find((draft) => draft.id === payloadActiveDraftId)
      || null;

    setWorld(nextWorld);
    setSelectedRoomId(nextSelectedRoomId);
    setSelectedRoomIds(nextSelectedRoomId ? [nextSelectedRoomId] : []);
    setVisibleLayerIds(nextVisibleLayerIds.length ? nextVisibleLayerIds : nextWorld.layers.map((layer) => layer.id));
    setBulkRegionId(nextWorld.regions[0]?.id || DEFAULT_REGION_ID);
    setBulkLayerId(nextWorld.layout?.default_layer_id || nextWorld.layers[0]?.id || DEFAULT_LAYER_ID);
    applyManifestPayload(payload);
    setCurrentDraft((previousDraft) => (
      payloadDraft || (fallbackDraftId && previousDraft?.id === fallbackDraftId ? previousDraft : null)
    ));
    setSelectedDraftId(payloadDraft?.id || fallbackDraftId || payloadActiveDraftId || '');
    setIsDirty(false);
  }, [applyManifestPayload]);

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

  const selectedRoom = world.rooms.find((room) => room.id === selectedRoomId)
    || world.rooms.find((room) => selectedRoomIds.includes(room.id))
    || world.rooms[0]
    || null;
  const selectedRoomIdSet = new Set(selectedRoomIds.filter((roomId) => world.rooms.some((room) => room.id === roomId)));
  const effectiveSelectedRoomIds = selectedRoomIdSet.size > 0
    ? Array.from(selectedRoomIdSet)
    : (selectedRoom ? [selectedRoom.id] : []);
  const selectedCount = selectedRoomIdSet.size;

  useEffect(() => {
    if (!selectedRoomId && world.rooms.length > 0) {
      setSelectedRoomId(world.rooms[0].id);
      setSelectedRoomIds([world.rooms[0].id]);
    }
  }, [selectedRoomId, world.rooms]);

  useEffect(() => {
    const roomIds = new Set(world.rooms.map((room) => room.id));
    setSelectedRoomIds((current) => {
      const nextRoomIds = current.filter((roomId) => roomIds.has(roomId));
      return sameStringArray(current, nextRoomIds) ? current : nextRoomIds;
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

    setBulkLayerId((current) => {
      if (layerIds.includes(current)) {
        return current;
      }
      return world.layout?.default_layer_id || layerIds[0] || DEFAULT_LAYER_ID;
    });

    setBulkRegionId((current) => {
      if (regionIds.includes(current)) {
        return current;
      }
      return regionIds[0] || DEFAULT_REGION_ID;
    });
  }, [world.layers, world.layout?.default_layer_id, world.regions]);

  function updateRoom(roomId, updater) {
    setIsDirty(true);
    setWorld((currentWorld) => ({
      ...currentWorld,
      rooms: currentWorld.rooms.map((room) => {
        if (room.id !== roomId) {
          return room;
        }
        return updater(room);
      }),
    }));
  }

  function updateRooms(roomIds, updater) {
    const roomIdSet = new Set(roomIds);
    setIsDirty(true);
    setWorld((currentWorld) => ({
      ...currentWorld,
      rooms: currentWorld.rooms.map((room, index) => {
        if (!roomIdSet.has(room.id)) {
          return room;
        }
        return updater(room, index);
      }),
    }));
  }

  const handleSelectRoom = useCallback((roomId, additive = false) => {
    setSelectedRoomId(roomId);
    setSelectedRoomIds((current) => {
      if (!additive) {
        const nextRoomIds = roomId ? [roomId] : [];
        return sameStringArray(current, nextRoomIds) ? current : nextRoomIds;
      }
      if (current.includes(roomId)) {
        const next = current.filter((selectedId) => selectedId !== roomId);
        const nextRoomIds = next.length ? next : [roomId];
        return sameStringArray(current, nextRoomIds) ? current : nextRoomIds;
      }
      const nextRoomIds = [...current, roomId];
      return sameStringArray(current, nextRoomIds) ? current : nextRoomIds;
    });
  }, []);

  const handleGraphSelection = useCallback((roomIds) => {
    const roomIdSet = new Set(world.rooms.map((room) => room.id));
    const nextRoomIds = roomIds.filter((roomId) => roomIdSet.has(roomId));
    setSelectedRoomIds((current) => (
      sameStringArray(current, nextRoomIds) ? current : nextRoomIds
    ));
    if (nextRoomIds.length > 0) {
      setSelectedRoomId((current) => (current === nextRoomIds[0] ? current : nextRoomIds[0]));
    }
  }, [world.rooms]);

  const handleGraphNodeChanges = useCallback((changes) => {
    const positionChanges = changes.filter((change) => (
      change.type === 'position' && change.position && change.id
    ));
    if (positionChanges.length === 0) {
      return;
    }

    setIsDirty(true);
    const positionByRoomId = new Map(positionChanges.map((change) => [change.id, change.position]));
    setWorld((currentWorld) => {
      let didChange = false;
      const rooms = currentWorld.rooms.map((room) => {
        const nextPosition = positionByRoomId.get(room.id);
        if (!nextPosition) {
          return room;
        }

        const x = finiteNumber(nextPosition.x, finiteNumber(room.layout?.x, room.x));
        const y = finiteNumber(nextPosition.y, finiteNumber(room.layout?.y, room.y));
        if (finiteNumber(room.layout?.x, room.x) === x && finiteNumber(room.layout?.y, room.y) === y) {
          return room;
        }

        didChange = true;
        return setRoomPosition(room, x, y);
      });

      return didChange ? { ...currentWorld, rooms } : currentWorld;
    });
  }, []);

  const handleMoveRoom = useCallback((roomId, position = {}) => {
    const x = finiteNumber(position.x, 0);
    const y = finiteNumber(position.y, 0);
    setIsDirty(true);
    setWorld((currentWorld) => {
      let didChange = false;
      const rooms = currentWorld.rooms.map((room) => {
        if (room.id !== roomId) {
          return room;
        }
        if (finiteNumber(room.layout?.x, room.x) === x && finiteNumber(room.layout?.y, room.y) === y) {
          return room;
        }
        didChange = true;
        return setRoomPosition(room, x, y);
      });
      return didChange ? { ...currentWorld, rooms } : currentWorld;
    });
    handleSelectRoom(roomId);
  }, [handleSelectRoom]);

  function handleRoomField(field, value) {
    if (!selectedRoom) {
      return;
    }

    if (field === 'id') {
      const previousRoomId = selectedRoom.id;
      setIsDirty(true);
      setWorld((currentWorld) => ({
        ...currentWorld,
        rooms: currentWorld.rooms.map((room) => {
          const exits = Object.fromEntries(
            Object.entries(room.exits || {}).map(([direction, targetRoomId]) => [
              direction,
              targetRoomId === previousRoomId ? value : targetRoomId,
            ])
          );
          if (room.id !== previousRoomId) {
            return { ...room, exits };
          }
          return {
            ...room,
            id: value,
            exits,
            mobs: (room.mobs || []).map((mob) => ({ ...mob, current_room: value })),
            scripts: (room.scripts || []).map((script) => ({ ...script, room_id: value })),
          };
        }),
        mobs: (currentWorld.mobs || []).map((mob) => (
          mob.current_room === previousRoomId ? { ...mob, current_room: value } : mob
        )),
        scripts: (currentWorld.scripts || []).map((script) => (
          script.room_id === previousRoomId ? { ...script, room_id: value } : script
        )),
      }));
      setSelectedRoomId(value);
      setSelectedRoomIds((current) => current.map((roomId) => (roomId === previousRoomId ? value : roomId)));
      return;
    }

    updateRoom(selectedRoom.id, (room) => {
      const nextValue = ['x', 'y', 'z'].includes(field)
        ? (value === '' ? null : Number(value))
        : value;
      if (field === 'x' || field === 'y') {
        const position = getRoomPosition(room, 0);
        return setRoomPosition(
          room,
          field === 'x' ? nextValue : position.x,
          field === 'y' ? nextValue : position.y
        );
      }
      const nextRoom = { ...room, [field]: nextValue };
      return nextRoom;
    });
  }

  function handleRoomLayerChange(layerId) {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      layout: {
        ...(room.layout || {}),
        layer_id: layerId,
      },
    }));
  }

  function handleRoomTagsChange(rawValue) {
    if (!selectedRoom) {
      return;
    }
    const tags = rawValue
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
    updateRoom(selectedRoom.id, (room) => ({ ...room, tags }));
  }

  function handleJsonField(field, rawValue) {
    if (!selectedRoom) {
      return;
    }

    try {
      const parsed = JSON.parse(rawValue || (field === 'exits' ? '{}' : '[]'));
      updateRoom(selectedRoom.id, (room) => ({ ...room, [field]: parsed }));
      setApiError('');
    } catch (error) {
      setApiError(`${field} JSON is invalid: ${error.message}`);
    }
  }

  function addRoom() {
    const nextRoom = makeRoomForWorld(world);
    setIsDirty(true);
    setWorld({
      ...world,
      rooms: [...world.rooms, nextRoom],
    });
    setSelectedRoomId(nextRoom.id);
    setSelectedRoomIds([nextRoom.id]);
  }

  function deleteSelectedRoom() {
    if (!selectedRoom) {
      return;
    }

    const roomIdsToDelete = new Set(effectiveSelectedRoomIds.length ? effectiveSelectedRoomIds : [selectedRoom.id]);
    const rooms = world.rooms.filter((room) => !roomIdsToDelete.has(room.id));
    const nextSelectedRoomId = rooms[0]?.id || '';
    setIsDirty(true);
    setWorld({
      ...world,
      rooms,
      mobs: (world.mobs || []).filter((mob) => !roomIdsToDelete.has(mob.current_room)),
      scripts: (world.scripts || []).filter((script) => !roomIdsToDelete.has(script.room_id)),
    });
    setSelectedRoomId(nextSelectedRoomId);
    setSelectedRoomIds(nextSelectedRoomId ? [nextSelectedRoomId] : []);
  }

  function addCollectionItem(field) {
    if (!selectedRoom) {
      return;
    }

    const defaults = {
      items: { id: `item-${selectedRoom.items.length + 1}`, name: 'New Item', description: '' },
      mobs: { id: `mob-${selectedRoom.mobs.length + 1}`, name: 'New Mob', description: '' },
      scripts: {
        id: `script-${selectedRoom.scripts.length + 1}`,
        path: 'backend/world_scripts/new_script.py',
        trigger: 'interact',
        content: "def run(context):\n    return None\n",
      },
    };

    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      [field]: [...(room[field] || []), defaults[field]],
    }));
  }

  function addExit() {
    if (!selectedRoom) {
      return;
    }

    const target = world.rooms.find((room) => room.id !== selectedRoom.id)?.id || '';
    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      exits: { ...(room.exits || {}), [nextExitDirection(room.exits)]: target },
    }));
  }

  function nextExitDirection(exits) {
    const existing = exits || {};
    if (!Object.prototype.hasOwnProperty.call(existing, 'new')) {
      return 'new';
    }
    let counter = 2;
    while (Object.prototype.hasOwnProperty.call(existing, `new${counter}`)) {
      counter += 1;
    }
    return `new${counter}`;
  }

  function handleExitDirectionChange(previousDirection, nextDirection) {
    if (!selectedRoom || !nextDirection) {
      return;
    }
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
      exits: {
        ...(room.exits || {}),
        [direction]: targetRoomId,
      },
    }));
  }

  function handleCollectionItemChange(field, index, itemField, value) {
    if (!selectedRoom) {
      return;
    }
    updateRoom(selectedRoom.id, (room) => ({
      ...room,
      [field]: (room[field] || []).map((item, itemIndex) => (
        itemIndex === index ? { ...item, [itemField]: value } : item
      )),
    }));
  }

  function toggleLayerVisibility(layerId) {
    setVisibleLayerIds((current) => (
      current.includes(layerId)
        ? current.filter((visibleLayerId) => visibleLayerId !== layerId)
        : [...current, layerId]
    ));
  }

  function applyBulkMetadata() {
    if (effectiveSelectedRoomIds.length === 0) {
      return;
    }
    updateRooms(effectiveSelectedRoomIds, (room) => ({
      ...room,
      region_id: bulkRegionId || room.region_id,
      layout: {
        ...(room.layout || {}),
        layer_id: bulkLayerId || roomLayerId(room, world),
      },
    }));
  }

  function snapSelectedToGrid() {
    const gridSize = finiteNumber(world.layout?.grid_size, 24) || 24;
    const targetRoomIds = effectiveSelectedRoomIds.length ? effectiveSelectedRoomIds : world.rooms.map((room) => room.id);
    updateRooms(targetRoomIds, (room) => {
      const position = getRoomPosition(room, 0);
      return setRoomPosition(room, snapValue(position.x, gridSize), snapValue(position.y, gridSize));
    });
  }

  function autoGridVisibleRooms() {
    const gridSize = Math.max(finiteNumber(world.layout?.grid_size, 24) || 24, 24);
    const visibleRoomIds = new Set(visibleRooms.map((room) => room.id));
    updateRooms(Array.from(visibleRoomIds), (room, index) => {
      const x = 120 + (index % 4) * gridSize * 7;
      const y = 110 + Math.floor(index / 4) * gridSize * 5;
      return setRoomPosition(room, x, y);
    });
  }

  function arrangeByRegion() {
    const regionIndex = new Map(world.regions.map((region, index) => [region.id, index]));
    const counters = new Map();
    updateRooms(world.rooms.map((room) => room.id), (room) => {
      const regionPosition = regionIndex.get(room.region_id) ?? 0;
      const count = counters.get(room.region_id) || 0;
      counters.set(room.region_id, count + 1);
      return setRoomPosition(room, 120 + regionPosition * 300, 110 + count * 120);
    });
  }

  function alignSelected(axis) {
    if (effectiveSelectedRoomIds.length < 2 || !selectedRoom) {
      return;
    }
    const anchor = getRoomPosition(selectedRoom, 0);
    updateRooms(effectiveSelectedRoomIds, (room) => {
      const position = getRoomPosition(room, 0);
      return setRoomPosition(
        room,
        axis === 'x' ? anchor.x : position.x,
        axis === 'y' ? anchor.y : position.y
      );
    });
  }

  function distributeSelected(axis) {
    if (effectiveSelectedRoomIds.length < 3) {
      return;
    }
    const selectedRooms = world.rooms
      .filter((room) => effectiveSelectedRoomIds.includes(room.id))
      .sort((left, right) => getRoomPosition(left, 0)[axis] - getRoomPosition(right, 0)[axis]);
    const first = getRoomPosition(selectedRooms[0], 0)[axis];
    const last = getRoomPosition(selectedRooms[selectedRooms.length - 1], 0)[axis];
    const gap = (last - first) / Math.max(selectedRooms.length - 1, 1);
    const indexedPositions = new Map(selectedRooms.map((room, index) => [room.id, first + gap * index]));
    updateRooms(effectiveSelectedRoomIds, (room) => {
      const position = getRoomPosition(room, 0);
      return setRoomPosition(
        room,
        axis === 'x' ? indexedPositions.get(room.id) : position.x,
        axis === 'y' ? indexedPositions.get(room.id) : position.y
      );
    });
  }

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

    if (
      draftDialog.mode === 'create'
      && isDirty
      && !window.confirm('Create draft and discard unsaved changes?')
    ) {
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
    const draftPath = selectedDraftId ? `/admin/api/world/drafts/${encodeURIComponent(selectedDraftId)}` : '/admin/api/world';
    const configs = {
      save: { path: draftPath, method: 'POST', body: { world: buildApiWorld(world) }, busy: 'Saving draft...' },
      validate: { path: '/admin/api/world/validate', method: 'POST', body: { world: buildApiWorld(world) }, busy: 'Validating world...' },
      apply: { path: selectedDraftId ? `${draftPath}/apply` : '/admin/api/world/apply', method: 'POST', body: { world: buildApiWorld(world) }, busy: 'Applying live world...' },
      reset: { path: selectedDraftId ? `${draftPath}/reset` : '/admin/api/world/reset', method: 'POST', busy: 'Resetting from baseline...' },
      publish: { path: selectedDraftId ? `${draftPath}/publish` : '/admin/api/world/publish', method: 'POST', body: { world: buildApiWorld(world) }, busy: 'Publishing through Git...' },
    };
    const config = configs[action];

    setIsBusy(true);
    setApiError('');
    setApiStatus(config.busy);
    try {
      const payload = await apiRequest(config.path, config);
      if (payload.world) {
        applyLoadedWorld(payload, selectedDraftId);
      }
      if (payload.saved?.manifest) {
        applyManifestPayload(payload.saved.manifest);
      }
      if (payload.validation) {
        setValidation(payload.validation);
      }
      if (action !== 'validate') {
        setIsDirty(false);
      }
      setApiStatus(summarizePayload(payload));
    } catch (error) {
      setApiError(error.message);
      setApiStatus(`${action} failed`);
    } finally {
      setIsBusy(false);
    }
  }

  const roomCount = world.rooms.length;
  const itemCount = world.rooms.reduce((count, room) => count + (room.items || []).length, 0);
  const mobCount = world.rooms.reduce((count, room) => count + (room.mobs || []).length, 0);
  const scriptCount = world.rooms.reduce((count, room) => count + (room.scripts || []).length, 0);
  const visibleLayerIdSet = new Set(visibleLayerIds);
  const visibleRooms = world.rooms.filter((room) => visibleLayerIdSet.has(roomLayerId(room, world)));

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
              <option key={draft.id} value={draft.id}>
                {formatDraftOption(draft)}
              </option>
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

      <section className="admin-builder__toolbar" aria-label="Runtime controls">
        <button type="button" onClick={loadWorld} disabled={!adminToken || isBusy}>Load World</button>
        <button type="button" onClick={() => runWorldAction('save')} disabled={!adminToken || isBusy || !selectedRoom}>Save Draft</button>
        <button type="button" onClick={() => runWorldAction('validate')} disabled={!adminToken || isBusy}>Validate</button>
        <button type="button" onClick={() => runWorldAction('apply')} disabled={!adminToken || isBusy}>Apply Live</button>
        <button type="button" onClick={() => runWorldAction('reset')} disabled={!adminToken || isBusy}>Reset Baseline</button>
        <button type="button" onClick={() => runWorldAction('publish')} disabled={!adminToken || isBusy}>Publish Git</button>
      </section>

      <section className="admin-builder__status" aria-live="polite">
        <strong>API status:</strong> {apiStatus}
        {apiError ? <div className="admin-builder__error" role="alert">{apiError}</div> : null}
      </section>

      <div className="admin-builder__workspace">
        <section className="admin-panel admin-panel--map">
          <div className="admin-panel__header">
            <h2>Map</h2>
            <button type="button" onClick={addRoom}>Add Room</button>
          </div>
          <section className="layout-toolbar" aria-label="Layout tools">
            <button type="button" onClick={snapSelectedToGrid} disabled={effectiveSelectedRoomIds.length === 0}>Snap Selected to Grid</button>
            <button type="button" onClick={autoGridVisibleRooms} disabled={visibleRooms.length === 0}>Auto Grid</button>
            <button type="button" onClick={arrangeByRegion} disabled={world.rooms.length === 0}>Arrange Regions</button>
            <button type="button" onClick={() => alignSelected('x')} disabled={effectiveSelectedRoomIds.length < 2}>Align X</button>
            <button type="button" onClick={() => alignSelected('y')} disabled={effectiveSelectedRoomIds.length < 2}>Align Y</button>
            <button type="button" onClick={() => distributeSelected('x')} disabled={effectiveSelectedRoomIds.length < 3}>Distribute X</button>
            <button type="button" onClick={() => distributeSelected('y')} disabled={effectiveSelectedRoomIds.length < 3}>Distribute Y</button>
          </section>
          <LayerControls
            layers={world.layers}
            visibleLayerIds={visibleLayerIds}
            onToggleLayer={toggleLayerVisibility}
          />
          <WorldGraph
            rooms={visibleRooms}
            world={world}
            selectedRoomId={selectedRoom?.id || ''}
            selectedRoomIds={effectiveSelectedRoomIds}
            onSelectRoom={handleSelectRoom}
            onSelectionChange={handleGraphSelection}
            onNodesChange={handleGraphNodeChanges}
            onMoveRoom={handleMoveRoom}
          />
        </section>

        <section className="admin-panel admin-panel--list">
          <div className="admin-panel__header">
            <h2>Rooms</h2>
            <span>{roomCount}</span>
          </div>
          <RoomList
            rooms={world.rooms}
            world={world}
            selectedRoomId={selectedRoom?.id || ''}
            selectedRoomIds={effectiveSelectedRoomIds}
            onSelectRoom={handleSelectRoom}
          />
        </section>

        <section className="admin-panel admin-panel--inspector">
          <div className="admin-panel__header">
            <h2>Inspector</h2>
            <button type="button" onClick={deleteSelectedRoom} disabled={!selectedRoom}>Delete Selected</button>
          </div>
          <RoomInspector
            room={selectedRoom}
            rooms={world.rooms}
            regions={world.regions}
            layers={world.layers}
            tags={world.tags}
            world={world}
            selectedCount={selectedCount}
            bulkRegionId={bulkRegionId}
            bulkLayerId={bulkLayerId}
            onBulkRegionChange={setBulkRegionId}
            onBulkLayerChange={setBulkLayerId}
            onApplyBulkMetadata={applyBulkMetadata}
            onFieldChange={handleRoomField}
            onLayerChange={handleRoomLayerChange}
            onTagsChange={handleRoomTagsChange}
            onJsonFieldChange={handleJsonField}
            onAddExit={addExit}
            onAddCollectionItem={addCollectionItem}
            onExitDirectionChange={handleExitDirectionChange}
            onExitTargetChange={handleExitTargetChange}
            onCollectionItemChange={handleCollectionItemChange}
          />
        </section>

        <section className="admin-panel admin-panel--validation" aria-label="Validation panel">
          <div className="admin-panel__header">
            <h2>Validation</h2>
            <span className={validation.ok ? 'admin-pill admin-pill--ok' : 'admin-pill admin-pill--bad'}>
              {validation.ok ? 'OK' : 'Blocked'}
            </span>
          </div>
          <ValidationPanel validation={validation} />
        </section>
      </div>
    </main>
  );
}

function LayerControls({ layers, visibleLayerIds, onToggleLayer }) {
  if (layers.length === 0) {
    return null;
  }

  return (
    <section className="layer-controls" aria-label="Map layers">
      {layers.map((layer) => {
        const name = layer.name || layer.id;
        return (
          <label key={layer.id} className="layer-controls__item">
            <input
              type="checkbox"
              aria-label={`Show ${name.toLowerCase()} layer`}
              checked={visibleLayerIds.includes(layer.id)}
              onChange={() => onToggleLayer(layer.id)}
            />
            <span>{name}</span>
            <small>z {finiteNumber(layer.z, 0)}</small>
          </label>
        );
      })}
    </section>
  );
}

function WorldGraph({
  rooms,
  world,
  selectedRoomId,
  selectedRoomIds,
  onSelectRoom,
  onSelectionChange,
  onNodesChange,
  onMoveRoom,
}) {
  const selectedRoomIdSet = useMemo(() => new Set(selectedRoomIds), [selectedRoomIds]);
  const roomIdSet = useMemo(() => new Set(rooms.map((room) => room.id)), [rooms]);
  const regionById = useMemo(() => (
    new Map(world.regions.map((region) => [region.id, region]))
  ), [world.regions]);
  const nodes = useMemo(() => rooms.map((room, index) => {
    const region = regionById.get(room.region_id);
    const isSelected = selectedRoomIdSet.has(room.id) || room.id === selectedRoomId;
    return {
      id: room.id,
      position: getRoomPosition(room, index),
      selected: isSelected,
      data: {
        label: room.name,
      },
      className: isSelected ? 'world-flow__node world-flow__node--selected' : 'world-flow__node',
      style: {
        borderColor: region?.color || DEFAULT_REGION_COLOR,
      },
    };
  }), [rooms, regionById, selectedRoomId, selectedRoomIdSet]);
  const edges = useMemo(() => rooms.flatMap((room) => exitEntries(room.exits).map(([direction, targetId]) => {
    if (!roomIdSet.has(targetId)) {
      return null;
    }
    return {
      id: `${room.id}-${direction}-${targetId}`,
      source: room.id,
      target: targetId,
      label: direction,
      className: 'world-flow__edge',
    };
  }).filter(Boolean)), [rooms, roomIdSet]);
  const handleNodeClick = useCallback((event, node) => {
    const additive = Boolean(event?.metaKey || event?.ctrlKey || event?.shiftKey);
    onSelectRoom(node.id, additive);
  }, [onSelectRoom]);
  const handleNodeDragStop = useCallback((event, node) => {
    onMoveRoom(node.id, node.position);
  }, [onMoveRoom]);
  const handleSelectionChange = useCallback(({ nodes: selectedNodes = [] }) => {
    onSelectionChange(selectedNodes.map((node) => node.id));
  }, [onSelectionChange]);

  return (
    <div className="world-flow-shell">
      <ReactFlowProvider>
        <ReactFlow
          className="world-flow"
          aria-label="World graph"
          nodes={nodes}
          edges={edges}
          fitView
          fitViewOptions={FLOW_FIT_VIEW_OPTIONS}
          nodesDraggable
          panOnDrag
          selectionOnDrag
          multiSelectionKeyCode={FLOW_MULTI_SELECTION_KEYS}
          onNodeClick={handleNodeClick}
          onNodeDragStop={handleNodeDragStop}
          onSelectionChange={handleSelectionChange}
          onNodesChange={onNodesChange}
        >
          <MiniMap pannable zoomable />
          <Controls />
          <Background gap={finiteNumber(world.layout?.grid_size, 24) || 24} />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}

function RoomList({ rooms, world, selectedRoomId, selectedRoomIds, onSelectRoom }) {
  if (rooms.length === 0) {
    return <p className="admin-empty">No rooms loaded.</p>;
  }

  const selectedRoomIdSet = new Set(selectedRoomIds);

  return (
    <div className="room-list">
      {rooms.map((room) => (
        <button
          type="button"
          key={room.id}
          className={selectedRoomIdSet.has(room.id) || room.id === selectedRoomId
            ? 'room-list__item room-list__item--selected'
            : 'room-list__item'}
          onClick={() => onSelectRoom(room.id)}
        >
          <strong>{room.name}</strong>
          <span>{room.id}</span>
          <small>{room.region_id || DEFAULT_REGION_ID} / {roomLayerId(room, world)} / {exitEntries(room.exits).length} exits</small>
        </button>
      ))}
    </div>
  );
}

function RoomInspector({
  room,
  rooms,
  regions,
  layers,
  tags,
  world,
  selectedCount,
  bulkRegionId,
  bulkLayerId,
  onBulkRegionChange,
  onBulkLayerChange,
  onApplyBulkMetadata,
  onFieldChange,
  onLayerChange,
  onTagsChange,
  onJsonFieldChange,
  onAddExit,
  onAddCollectionItem,
  onExitDirectionChange,
  onExitTargetChange,
  onCollectionItemChange,
}) {
  if (!room) {
    return <p className="admin-empty">Load or add a room to begin editing.</p>;
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
        </div>
      </div>
    );
  }

  return (
    <div className="room-inspector">
      <div className="form-grid">
        <label>
          Room id
          <input value={room.id} onChange={(event) => onFieldChange('id', event.target.value)} />
        </label>
        <label>
          Room name
          <input value={room.name} onChange={(event) => onFieldChange('name', event.target.value)} />
        </label>
        <label className="form-grid__wide">
          Room description
          <textarea value={room.description} onChange={(event) => onFieldChange('description', event.target.value)} rows={4} />
        </label>
        <label>
          X
          <input type="number" value={room.x ?? ''} onChange={(event) => onFieldChange('x', event.target.value)} />
        </label>
        <label>
          Y
          <input type="number" value={room.y ?? ''} onChange={(event) => onFieldChange('y', event.target.value)} />
        </label>
        <label>
          Z
          <input type="number" value={room.z ?? 0} onChange={(event) => onFieldChange('z', event.target.value)} />
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
        <label>
          Tags
          <input
            list="world-builder-tags"
            value={(room.tags || []).join(', ')}
            onChange={(event) => onTagsChange(event.target.value)}
          />
        </label>
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

      <div className="rich-editor-grid">
        <ExitsEditor
          exits={room.exits || {}}
          rooms={rooms}
          onAddExit={onAddExit}
          onDirectionChange={onExitDirectionChange}
          onTargetChange={onExitTargetChange}
        />
        <CollectionEditor
          title="Items"
          field="items"
          items={room.items || []}
          fields={[
            ['id', 'Id'],
            ['name', 'Name'],
            ['description', 'Description'],
          ]}
          onAdd={() => onAddCollectionItem('items')}
          onChange={onCollectionItemChange}
        />
        <CollectionEditor
          title="Mobs"
          field="mobs"
          items={room.mobs || []}
          fields={[
            ['id', 'Id'],
            ['name', 'Name'],
            ['description', 'Description'],
          ]}
          onAdd={() => onAddCollectionItem('mobs')}
          onChange={onCollectionItemChange}
        />
        <CollectionEditor
          title="Scripts"
          field="scripts"
          items={room.scripts || []}
          fields={[
            ['id', 'Id'],
            ['path', 'Path'],
            ['trigger', 'Trigger'],
            ['content', 'Content'],
          ]}
          onAdd={() => onAddCollectionItem('scripts')}
          onChange={onCollectionItemChange}
        />
      </div>

      <details className="raw-json-editors">
        <summary>Raw JSON</summary>
        <div className="editor-tabs">
          <JsonEditor
            label="Exits JSON"
            value={formatJson(room.exits || {})}
            help={`Known rooms: ${rooms.map((item) => item.id).join(', ') || 'none'}`}
            onChange={(value) => onJsonFieldChange('exits', value)}
          />
          <JsonEditor
            label="Items JSON"
            value={formatJson(room.items || [])}
            onChange={(value) => onJsonFieldChange('items', value)}
          />
          <JsonEditor
            label="Mobs JSON"
            value={formatJson(room.mobs || [])}
            onChange={(value) => onJsonFieldChange('mobs', value)}
          />
          <JsonEditor
            label="Scripts JSON"
            value={formatJson(room.scripts || [])}
            onChange={(value) => onJsonFieldChange('scripts', value)}
          />
        </div>
      </details>
    </div>
  );
}

function ExitsEditor({ exits, rooms, onAddExit, onDirectionChange, onTargetChange }) {
  const entries = exitEntries(exits);

  return (
    <section className="rich-editor">
      <div className="rich-editor__header">
        <h3>Exits</h3>
        <button type="button" onClick={onAddExit}>Add Exit</button>
      </div>
      {entries.length === 0 ? <p className="admin-empty">No exits.</p> : null}
      {entries.map(([direction, targetRoomId], index) => (
        <div key={`${direction}-${index}`} className="collection-row">
          <label>
            Direction
            <input
              aria-label={`Exit ${direction} direction`}
              value={direction}
              onChange={(event) => onDirectionChange(direction, event.target.value)}
            />
          </label>
          <label>
            Target
            <select
              aria-label={`Exit ${direction} target`}
              value={targetRoomId}
              onChange={(event) => onTargetChange(direction, event.target.value)}
            >
              <option value="">None</option>
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>{room.name} ({room.id})</option>
              ))}
            </select>
          </label>
        </div>
      ))}
    </section>
  );
}

function CollectionEditor({ title, field, items, fields, onAdd, onChange }) {
  return (
    <section className="rich-editor">
      <div className="rich-editor__header">
        <h3>{title}</h3>
        <button type="button" onClick={onAdd}>Add {title.slice(0, -1)}</button>
      </div>
      {items.length === 0 ? <p className="admin-empty">No {title.toLowerCase()}.</p> : null}
      {items.map((item, index) => (
        <div key={item.id || index} className="collection-row collection-row--stacked">
          {fields.map(([itemField, label]) => {
            const isTextarea = itemField === 'content' || itemField === 'description';
            const inputLabel = `${title.slice(0, -1)} ${index + 1} ${label.toLowerCase()}`;
            return (
              <label key={itemField}>
                {label}
                {isTextarea ? (
                  <textarea
                    aria-label={inputLabel}
                    value={item[itemField] || ''}
                    rows={itemField === 'content' ? 6 : 3}
                    onChange={(event) => onChange(field, index, itemField, event.target.value)}
                  />
                ) : (
                  <input
                    aria-label={inputLabel}
                    value={item[itemField] || ''}
                    onChange={(event) => onChange(field, index, itemField, event.target.value)}
                  />
                )}
              </label>
            );
          })}
        </div>
      ))}
    </section>
  );
}

function JsonEditor({ label, value, help, onChange, actionLabel, onAction }) {
  const [draft, setDraft] = useState(value);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  return (
    <div className="json-editor">
      <span>
        {label}
        {actionLabel && onAction ? <button type="button" onClick={onAction}>{actionLabel}</button> : null}
      </span>
      <textarea
        aria-label={label}
        value={draft}
        onChange={(event) => {
          setDraft(event.target.value);
          onChange(event.target.value);
        }}
        rows={6}
      />
      {help ? <small>{help}</small> : null}
    </div>
  );
}

function ValidationPanel({ validation }) {
  const errors = validation.errors || [];
  const warnings = validation.warnings || [];

  if (errors.length === 0 && warnings.length === 0) {
    return <p className="admin-empty">No validation issues reported.</p>;
  }

  return (
    <div className="validation-list">
      {errors.map((issue, index) => (
        <div key={`error-${index}`} className="validation-list__item validation-list__item--error">
          <strong>{issue.code || 'error'}</strong>
          <span>{issue.message || String(issue)}</span>
        </div>
      ))}
      {warnings.map((issue, index) => (
        <div key={`warning-${index}`} className="validation-list__item validation-list__item--warning">
          <strong>{issue.code || 'warning'}</strong>
          <span>{issue.message || String(issue)}</span>
        </div>
      ))}
    </div>
  );
}

export default App;
