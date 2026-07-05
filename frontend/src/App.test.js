import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import App from './App';
import io from 'socket.io-client';

jest.mock('socket.io-client', () => jest.fn());
jest.mock('@xyflow/react', () => {
  const React = require('react');
  return {
    ReactFlowProvider: ({ children }) => <div data-testid="react-flow-provider">{children}</div>,
    ReactFlow: ({
      nodes = [],
      edges = [],
      onNodeClick,
      onSelectionChange,
      onNodeDragStop,
      onConnect,
      children,
    }) => (
      <div aria-label="World graph" data-node-count={nodes.length} data-edge-count={edges.length}>
        <button
          type="button"
          onClick={(event) => {
            if (nodes[0]) {
              onNodeClick?.(event, nodes[0]);
            }
          }}
        >
          Select first flow node
        </button>
        <button
          type="button"
          onClick={() => onSelectionChange?.({ nodes: nodes.slice(0, 2), edges: [] })}
        >
          Select two flow nodes
        </button>
        <button
          type="button"
          onClick={() => {
            if (nodes[0]) {
              const dragged = { ...nodes[0], position: { x: 444, y: 222 } };
              onNodeDragStop?.({}, dragged, [dragged]);
            }
          }}
        >
          Drag first flow node
        </button>
        <button
          type="button"
          onClick={() => {
            if (nodes.length >= 2) {
              onConnect?.({ source: nodes[0].id, target: nodes[1].id });
            }
          }}
        >
          Connect first two nodes
        </button>
        {nodes.map((node) => (
          <div
            key={node.id}
            data-testid={`flow-node-${node.id}`}
            data-selected={node.selected ? 'true' : 'false'}
            data-x={node.position?.x}
            data-y={node.position?.y}
          >
            {node.data?.label}
          </div>
        ))}
        {children}
      </div>
    ),
    Background: () => <div data-testid="flow-background" />,
    Controls: () => <div data-testid="flow-controls" />,
    MiniMap: () => <div data-testid="flow-minimap" />,
    Handle: () => null,
    Position: { Left: 'left', Right: 'right', Top: 'top', Bottom: 'bottom' },
    useNodesState: (initial) => {
      const [nodes, setNodes] = React.useState(initial);
      const onNodesChange = React.useCallback(() => {}, []);
      return [nodes, setNodes, onNodesChange];
    },
    useEdgesState: (initial) => {
      const [edges, setEdges] = React.useState(initial);
      const onEdgesChange = React.useCallback(() => {}, []);
      return [edges, setEdges, onEdgesChange];
    },
    useReactFlow: () => ({ fitView: jest.fn(), setCenter: jest.fn() }),
  };
});

function makeSampleWorld() {
  return {
    version: 1,
    spawn_room_id: 'square',
    metadata: { source: 'test' },
    regions: [
      { id: 'village', name: 'Village', color: '#4f8fba' },
      { id: 'wilds', name: 'Wilds', color: '#8f6f4f' },
    ],
    layers: [
      { id: 'surface', name: 'Surface', z: 0, visible: true },
      { id: 'underground', name: 'Underground', z: -1, visible: false },
    ],
    tags: [
      { id: 'safe', label: 'Safe', color: '#4f8fba', scope: ['room'] },
    ],
    layout: { grid_size: 24, snap_to_grid: true, default_layer_id: 'surface' },
    rooms: [
      {
        id: 'square',
        name: 'Village Square',
        description: 'A busy cobblestone square.',
        x: 120,
        y: 160,
        z: 0,
        region_id: 'village',
        tags: ['safe'],
        layout: { x: 120, y: 160, layer_id: 'surface', pinned: true },
        exits: { north: 'woods' },
        items: [{ id: 'fountain', name: 'Old Fountain', description: 'Cold stone.', type: 'item' }],
        mobs: [{ id: 'guard', name: 'Town Guard', description: 'Watching the road.' }],
        scripts: [{ id: 'welcome', path: 'backend/world_scripts/welcome.py', trigger: 'enter' }],
        is_dark: false,
        is_outdoor: true,
      },
      {
        id: 'woods',
        name: 'Dark Woods',
        description: 'Tall trees block the sky.',
        x: 120,
        y: 10,
        z: 0,
        region_id: 'wilds',
        tags: [],
        layout: { x: 120, y: 10, layer_id: 'surface', pinned: true },
        exits: { south: 'square' },
        items: [],
        mobs: [],
        scripts: [],
        is_dark: true,
      },
    ],
  };
}

const LEVEL_NAMES = ['Neophyte', 'Novice', 'Acolyte'];

const MOB_DEFINITIONS = [
  {
    id: 'wolf',
    name: 'wolf',
    description: 'A grey wolf.',
    strength: 14,
    dexterity: 12,
    max_stamina: 30,
    damage: 4,
    aggressive: true,
    aggro_delay_min: 0,
    aggro_delay_max: 0,
    movement_interval: 60,
    patrol_rooms: [],
    point_value: 50,
    pronouns: 'it',
    instant_death: false,
    loot_table: [],
  },
];

let socket;
let confirmSpy;

function installSocketMock() {
  socket = {
    handlers: {},
    emit: jest.fn(),
    on: jest.fn((event, handler) => {
      socket.handlers[event] = handler;
    }),
    disconnect: jest.fn(),
  };
  io.mockReturnValue(socket);
}

function routeTo(pathname) {
  window.history.pushState({}, '', pathname);
}

function okJson(payload) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(payload),
  });
}

// Route-based fetch mock: keys are "METHOD /path" (or "/path" for any method).
function installFetch(routes = {}) {
  const merged = {
    'GET /admin/api/world': () => okJson({ world: makeSampleWorld() }),
    'GET /admin/api/world/mob-definitions': () => okJson({ mob_definitions: MOB_DEFINITIONS, levels: LEVEL_NAMES }),
    ...routes,
  };
  global.fetch = jest.fn((url, options = {}) => {
    const path = String(url).replace('http://localhost:8080', '');
    const method = options.method || 'GET';
    const handler = merged[`${method} ${path}`] || merged[path];
    if (!handler) {
      return okJson({});
    }
    return handler(options, path);
  });
}

function fetchCalls(method, path) {
  return global.fetch.mock.calls.filter(([url, options = {}]) => {
    const callPath = String(url).replace('http://localhost:8080', '');
    return callPath === path && (options.method || 'GET') === method;
  });
}

function lastBody(method, path) {
  const calls = fetchCalls(method, path);
  const [, options] = calls[calls.length - 1];
  return JSON.parse(options.body);
}

async function renderBuilder(routes = {}) {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  installFetch(routes);
  render(<App />);
  await screen.findByLabelText('Search rooms');
  await screen.findAllByText('Village Square');
}

function roomListPanel() {
  return screen.getByRole('region', { name: 'Room browser' });
}

beforeEach(() => {
  routeTo('/');
  installSocketMock();
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  localStorage.clear();
  global.fetch = jest.fn();
  confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
});

afterEach(() => {
  confirmSpy.mockRestore();
  jest.clearAllMocks();
});

test('renders the existing game terminal on normal paths', () => {
  render(<App />);

  expect(screen.getByText('The Forgotten Realms')).toBeInTheDocument();
  expect(screen.getByPlaceholderText('Type your command....')).toBeInTheDocument();
  expect(screen.queryByText('Admin World Builder')).not.toBeInTheDocument();
});

test('renders the admin world builder route with the login panel until a token arrives', () => {
  routeTo('/admin/world-builder');

  render(<App />);

  expect(screen.getByText('Admin World Builder')).toBeInTheDocument();
  expect(screen.getAllByText(/Waiting for stupidgem admin token/i).length).toBeGreaterThan(0);
  expect(screen.getByRole('button', { name: /load world/i })).toBeDisabled();
  expect(screen.getByLabelText('Admin login panel')).toBeInTheDocument();
  fireEvent.change(screen.getByPlaceholderText('Type your admin login command...'), {
    target: { value: 'stupidgem' },
  });
  fireEvent.submit(screen.getByPlaceholderText('Type your admin login command...'));
  expect(socket.emit).toHaveBeenCalledWith('command', 'stupidgem');
});

test('captures adminToken from the socket and loads world data with bearer auth', async () => {
  routeTo('/admin/world-builder');
  installFetch();

  render(<App />);
  act(() => {
    socket.handlers.adminToken({ token: 'token-123' });
  });

  await screen.findAllByText('Village Square');

  expect(localStorage.getItem('adminToken')).toBe('token-123');
  const [, options] = fetchCalls('GET', '/admin/api/world')[0];
  expect(options.headers.Authorization).toBe('Bearer token-123');
  expect(screen.getByLabelText('World graph')).toBeInTheDocument();
});

test('clears expired admin tokens and returns to the login panel', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'expired-token');
  installFetch({
    'GET /admin/api/world': () => Promise.resolve({
      ok: false,
      status: 401,
      json: () => Promise.resolve({
        error: 'unauthorized',
        message: 'You must be logged in as stupidgem to use the world builder.',
      }),
    }),
  });

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent('You must be logged in as stupidgem');
  expect(localStorage.getItem('adminToken')).toBeNull();
  expect(screen.getByLabelText('Admin login panel')).toBeInTheDocument();
});

test('edits the selected room and saves the changed world payload', async () => {
  await renderBuilder();

  fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Grand Plaza' } });
  fireEvent.change(screen.getByLabelText('Room description'), { target: { value: 'Wide and windy.' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const square = body.world.rooms.find((room) => room.id === 'square');
  expect(square.name).toBe('Grand Plaza');
  expect(square.description).toBe('Wide and windy.');
});

test('undo and redo revert and reapply room edits', async () => {
  await renderBuilder();

  fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Grand Plaza' } });
  expect(screen.getByLabelText('Room name')).toHaveValue('Grand Plaza');

  fireEvent.click(screen.getByRole('button', { name: /undo/i }));
  expect(screen.getByLabelText('Room name')).toHaveValue('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /redo/i }));
  expect(screen.getByLabelText('Room name')).toHaveValue('Grand Plaza');

  fireEvent.keyDown(window, { key: 'z', metaKey: true });
  expect(screen.getByLabelText('Room name')).toHaveValue('Village Square');
});

test('digging creates a connected room, selects it, and auto-slugs its id on rename', async () => {
  await renderBuilder();

  fireEvent.click(screen.getByRole('button', { name: 'Dig east' }));

  expect(screen.getByLabelText('Room id')).toHaveValue('room_3');
  fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Rusty Forge' } });
  expect(screen.getByLabelText('Room id')).toHaveValue('rusty_forge');

  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const square = body.world.rooms.find((room) => room.id === 'square');
  const forge = body.world.rooms.find((room) => room.id === 'rusty_forge');
  expect(square.exits.east).toBe('rusty_forge');
  expect(forge.exits.west).toBe('square');
  expect(forge.name).toBe('Rusty Forge');
});

test('connecting two nodes on the canvas wires both exits from their geometry', async () => {
  const world = makeSampleWorld();
  world.rooms[0].exits = {};
  world.rooms[1].exits = {};
  await renderBuilder({ 'GET /admin/api/world': () => okJson({ world }) });

  fireEvent.click(screen.getByRole('button', { name: 'Connect first two nodes' }));

  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const square = body.world.rooms.find((room) => room.id === 'square');
  const woods = body.world.rooms.find((room) => room.id === 'woods');
  // woods sits directly above square in the fixture, so geometry infers north/south.
  expect(square.exits.north).toBe('woods');
  expect(woods.exits.south).toBe('square');
});

test('exit editor changes direction, deletes exits, and adds reverse exits', async () => {
  const world = makeSampleWorld();
  world.rooms[1].exits = {}; // make square -> woods one-way
  await renderBuilder({ 'GET /admin/api/world': () => okJson({ world }) });

  fireEvent.click(screen.getByRole('button', { name: '+ reverse' }));
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  let body = lastBody('POST', '/admin/api/world');
  expect(body.world.rooms.find((room) => room.id === 'woods').exits.south).toBe('square');

  fireEvent.click(screen.getByRole('button', { name: 'Delete exit north' }));
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(2));
  body = lastBody('POST', '/admin/api/world');
  expect(body.world.rooms.find((room) => room.id === 'square').exits.north).toBeUndefined();
});

test('search and filter chips narrow the room list', async () => {
  await renderBuilder();
  const browser = roomListPanel();

  fireEvent.change(screen.getByLabelText('Search rooms'), { target: { value: 'woods' } });
  expect(within(browser).getByRole('button', { name: /Dark Woods/ })).toBeInTheDocument();
  expect(within(browser).queryByRole('button', { name: /Village Square/ })).not.toBeInTheDocument();
  expect(within(browser).getByText('1 / 2 rooms')).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText('Search rooms'), { target: { value: '' } });
  fireEvent.click(screen.getByRole('button', { name: 'Dark' }));
  expect(within(browser).getByRole('button', { name: /Dark Woods/ })).toBeInTheDocument();
  expect(within(browser).queryByRole('button', { name: /Village Square/ })).not.toBeInTheDocument();
});

test('selecting a room in the browser updates the inspector', async () => {
  await renderBuilder();
  const browser = roomListPanel();

  fireEvent.click(within(browser).getByRole('button', { name: /Dark Woods/ }));

  expect(screen.getByLabelText('Room id')).toHaveValue('woods');
});

test('deleting the selected room strips exits that pointed at it', async () => {
  await renderBuilder();
  const browser = roomListPanel();

  fireEvent.click(within(browser).getByRole('button', { name: /Dark Woods/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Delete Room' }));

  expect(confirmSpy).toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  expect(body.world.rooms.map((room) => room.id)).toEqual(['square']);
  expect(body.world.rooms[0].exits.north).toBeUndefined();
});

test('renaming a room id cascades to exits, mobs, and scripts', async () => {
  await renderBuilder();

  // Room ids commit on blur so transient collisions while typing are ignored.
  fireEvent.change(screen.getByLabelText('Room id'), { target: { value: 'plaza' } });
  fireEvent.blur(screen.getByLabelText('Room id'));
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const woods = body.world.rooms.find((room) => room.id === 'woods');
  expect(woods.exits.south).toBe('plaza');
  expect(body.world.mobs.every((mob) => mob.current_room !== 'square')).toBe(true);
  // eslint-disable-next-line testing-library/no-node-access -- world.scripts is plain JSON, not document.scripts
  expect(body.world.scripts.every((script) => script.room_id !== 'square')).toBe(true);
  expect(body.world.spawn_room_id).toBe('plaza');
});

test('rejects renaming a room id to one that already exists', async () => {
  await renderBuilder();

  fireEvent.change(screen.getByLabelText('Room id'), { target: { value: 'woods' } });
  fireEvent.blur(screen.getByLabelText('Room id'));

  expect(await screen.findByRole('alert')).toHaveTextContent("Room id 'woods' is already taken.");
  // The underlying room keeps its id — verify via the save payload.
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  expect(body.world.rooms.map((room) => room.id)).toContain('square');
});

test('item editor switches types and exposes weapon fields', async () => {
  await renderBuilder();

  fireEvent.change(screen.getByLabelText('Item 1 type'), { target: { value: 'weapon' } });
  // Items editor renders before the mobs editor, so its Damage field comes
  // first. Numeric fields commit on blur.
  fireEvent.change(screen.getAllByLabelText('Damage')[0], { target: { value: '55' } });
  fireEvent.blur(screen.getAllByLabelText('Damage')[0]);
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const item = body.world.rooms.find((room) => room.id === 'square').items[0];
  expect(item.type).toBe('weapon');
  expect(item.damage).toBe(55);
});

test('mob palette places a template mob with its stats', async () => {
  await renderBuilder();

  fireEvent.change(screen.getByLabelText('Mob template'), { target: { value: 'wolf' } });
  fireEvent.click(screen.getByRole('button', { name: 'Add Mob' }));
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const wolf = body.world.mobs.find((mob) => mob.id === 'wolf_square_1');
  expect(wolf).toBeTruthy();
  expect(wolf.strength).toBe(14);
  expect(wolf.aggressive).toBe(true);
  expect(wolf.current_room).toBe('square');
});

test('collection rows can be deleted', async () => {
  await renderBuilder();

  fireEvent.click(screen.getByRole('button', { name: 'Delete item fountain' }));
  fireEvent.click(screen.getByRole('button', { name: 'Delete mob guard' }));
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const square = body.world.rooms.find((room) => room.id === 'square');
  expect(square.items).toHaveLength(0);
  expect(body.world.mobs.filter((mob) => mob.current_room === 'square')).toHaveLength(0);
});

test('auto layout assigns positions to rooms that have none', async () => {
  const world = makeSampleWorld();
  world.rooms = world.rooms.map(({ x, y, layout, ...room }) => room);
  await renderBuilder({ 'GET /admin/api/world': () => okJson({ world }) });

  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const square = body.world.rooms.find((room) => room.id === 'square');
  const woods = body.world.rooms.find((room) => room.id === 'woods');
  expect(Number.isFinite(square.x)).toBe(true);
  expect(Number.isFinite(woods.y)).toBe(true);
  // woods is north of square, so the exit-aware layout places it above.
  expect(woods.y).toBeLessThan(square.y);
});

test('dragging a node persists its new position', async () => {
  await renderBuilder();

  fireEvent.click(screen.getByRole('button', { name: 'Drag first flow node' }));
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const dragged = body.world.rooms.find((room) => room.layout.x === 444);
  expect(dragged).toBeTruthy();
  expect(dragged.layout.y).toBe(222);
});

test('multi-select enables bulk metadata editing', async () => {
  await renderBuilder();

  // Box selection only counts while the pointer is on the canvas; simulate
  // the pointer-down that precedes a real drag-select.
  fireEvent.pointerDown(screen.getByTestId('world-flow-shell'));
  fireEvent.click(screen.getByRole('button', { name: 'Select two flow nodes' }));
  expect(screen.getByText('2 rooms selected')).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText('Bulk region'), { target: { value: 'wilds' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply Bulk Metadata' }));
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  expect(body.world.rooms.every((room) => room.region_id === 'wilds')).toBe(true);
});

test('runs validate and apply actions and confirms before applying live', async () => {
  await renderBuilder({
    'POST /admin/api/world/validate': () => okJson({ validation: { ok: true, errors: [], warnings: [] } }),
    'POST /admin/api/world/apply': () => okJson({ applied: { rooms: 2, mobs: 1 } }),
  });

  fireEvent.click(screen.getByRole('button', { name: 'Validate' }));
  await screen.findByText(/Validation complete/);

  fireEvent.click(screen.getByRole('button', { name: 'Apply Live' }));
  await screen.findByText(/Applied live: 2 rooms, 1 mobs/);
  expect(confirmSpy).toHaveBeenCalledWith(expect.stringMatching(/Apply this draft to the LIVE world/));
});

test('surfaces publish failures instead of reporting success', async () => {
  await renderBuilder({
    'POST /admin/api/world/publish': () => okJson({
      publish: { ok: false, step: 'push', error: 'remote rejected' },
    }),
  });

  fireEvent.click(screen.getByRole('button', { name: 'Publish Git' }));

  await screen.findByText(/Publish failed: remote rejected/);
});

test('clicking a validation issue selects the offending room', async () => {
  await renderBuilder({
    'POST /admin/api/world/validate': () => okJson({
      validation: {
        ok: false,
        errors: [{ code: 'broken_exit', message: "Room 'woods' exit east -> 'nowhere'", room_id: 'woods' }],
        warnings: [],
      },
    }),
  });

  fireEvent.click(screen.getByRole('button', { name: 'Validate' }));
  const issue = await screen.findByRole('button', { name: /broken_exit/ });
  fireEvent.click(issue);

  expect(screen.getByLabelText('Room id')).toHaveValue('woods');
});

test('loads draft manifest, switches drafts, and saves to the selected draft', async () => {
  const draftOne = { id: 'main', name: 'Main', room_count: 2, updated_at: '2026-06-01' };
  const draftTwo = { id: 'experiment', name: 'Experiment', room_count: 1, updated_at: '2026-06-02' };
  const secondWorld = makeSampleWorld();
  secondWorld.rooms = [secondWorld.rooms[0]];
  secondWorld.rooms[0].exits = {};

  await renderBuilder({
    'GET /admin/api/world': () => okJson({
      world: makeSampleWorld(),
      manifest: { drafts: [draftOne, draftTwo], active_draft_id: 'main' },
      draft: draftOne,
    }),
    'GET /admin/api/world/drafts/experiment': () => okJson({ world: secondWorld, draft: draftTwo }),
    'POST /admin/api/world/drafts/experiment': () => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'drafts/experiment.json' },
    }),
  });

  expect(screen.getByText('Editing Draft: Main')).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText('Draft project'), { target: { value: 'experiment' } });
  await screen.findByText('Editing Draft: Experiment');

  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world/drafts/experiment').length).toBe(1));
});

test('prompts before switching away from unsaved draft changes', async () => {
  const draftOne = { id: 'main', name: 'Main', room_count: 2 };
  const draftTwo = { id: 'experiment', name: 'Experiment', room_count: 1 };
  await renderBuilder({
    'GET /admin/api/world': () => okJson({
      world: makeSampleWorld(),
      manifest: { drafts: [draftOne, draftTwo], active_draft_id: 'main' },
      draft: draftOne,
    }),
    'GET /admin/api/world/drafts/experiment': () => okJson({
      world: makeSampleWorld(),
      draft: draftTwo,
    }),
  });
  confirmSpy.mockReturnValue(false);

  fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Changed' } });
  fireEvent.change(screen.getByLabelText('Draft project'), { target: { value: 'experiment' } });

  expect(confirmSpy).toHaveBeenCalledWith('Switch drafts and discard unsaved changes?');
  expect(fetchCalls('GET', '/admin/api/world/drafts/experiment')).toHaveLength(0);
  expect(screen.getByText('Editing Draft: Main')).toBeInTheDocument();
});

test('auto-slug keeps following the name when typed character by character', async () => {
  await renderBuilder();

  fireEvent.click(screen.getByRole('button', { name: 'Dig east' }));
  const typeName = (value) => fireEvent.change(screen.getByLabelText('Room name'), { target: { value } });
  typeName('F');
  typeName('Fo');
  typeName('Forge');

  expect(screen.getByLabelText('Room id')).toHaveValue('forge');
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));
  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  expect(body.world.rooms.find((room) => room.id === 'square').exits.east).toBe('forge');
});

test('a burst of name keystrokes undoes as a single history entry', async () => {
  await renderBuilder();

  const typeName = (value) => fireEvent.change(screen.getByLabelText('Room name'), { target: { value } });
  typeName('Village SquareX');
  typeName('Village SquareXY');
  typeName('Village SquareXYZ');
  expect(screen.getByLabelText('Room name')).toHaveValue('Village SquareXYZ');

  fireEvent.click(screen.getByRole('button', { name: /undo/i }));
  expect(screen.getByLabelText('Room name')).toHaveValue('Village Square');
});

test('failed saves surface the returned validation issues', async () => {
  await renderBuilder({
    'POST /admin/api/world': () => Promise.resolve({
      ok: false,
      status: 400,
      json: () => Promise.resolve({
        error: 'validation_failed',
        validation: {
          ok: false,
          errors: [{ code: 'broken_exit', message: "Room 'square' exit north -> 'nowhere'", room_id: 'square' }],
          warnings: [],
        },
      }),
    }),
  });

  fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Changed' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  expect(await screen.findByRole('button', { name: /broken_exit/ })).toBeInTheDocument();
  expect(screen.getByText(/1 errors, 0 warnings/)).toBeInTheDocument();
});

test('reset baseline asks for confirmation before overwriting the draft', async () => {
  await renderBuilder();
  confirmSpy.mockReturnValue(false);

  fireEvent.click(screen.getByRole('button', { name: 'Reset Baseline' }));

  expect(confirmSpy).toHaveBeenCalledWith(expect.stringMatching(/Reset this draft to the generated baseline/));
  expect(fetchCalls('POST', '/admin/api/world/reset')).toHaveLength(0);
});

test('committing unknown tags declares them in world.tags', async () => {
  await renderBuilder();

  const addTag = (tag) => {
    fireEvent.change(screen.getByLabelText('Add to tags'), { target: { value: tag } });
    fireEvent.keyDown(screen.getByLabelText('Add to tags'), { key: 'Enter' });
  };
  addTag('haunted');
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  expect(body.world.tags.map((tag) => tag.id)).toEqual(expect.arrayContaining(['safe', 'haunted']));
  expect(body.world.rooms.find((room) => room.id === 'square').tags).toEqual(['safe', 'haunted']);
});

test('patrol rooms are picked from existing rooms, not typed', async () => {
  await renderBuilder();

  const picker = screen.getByLabelText('Add to mob 1 patrol rooms');
  expect(within(picker).getByRole('option', { name: /Dark Woods/ })).toBeInTheDocument();
  fireEvent.change(picker, { target: { value: 'woods' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  const guard = body.world.mobs.find((mob) => mob.id === 'guard');
  expect(guard.patrol_rooms).toEqual(['woods']);
});

test('patrol room chips can be removed', async () => {
  const world = makeSampleWorld();
  world.rooms[0].mobs[0].patrol_rooms = ['square', 'woods'];
  await renderBuilder({ 'GET /admin/api/world': () => okJson({ world }) });

  fireEvent.click(screen.getByLabelText('Remove square from mob 1 patrol rooms'));
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  expect(body.world.mobs.find((mob) => mob.id === 'guard').patrol_rooms).toEqual(['woods']);
});

test('weapon min level is a dropdown of real level names', async () => {
  await renderBuilder();

  fireEvent.change(screen.getByLabelText('Item 1 type'), { target: { value: 'weapon' } });
  const minLevel = screen.getByLabelText('Min level');
  expect(within(minLevel).getByRole('option', { name: 'Neophyte' })).toBeInTheDocument();
  fireEvent.change(minLevel, { target: { value: 'Novice' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  expect(body.world.rooms.find((room) => room.id === 'square').items[0].min_level).toBe('Novice');
});

test('script paths are pinned inside world_scripts', async () => {
  await renderBuilder();

  fireEvent.change(screen.getByLabelText('Script 1 filename'), { target: { value: '../evil.py' } });
  fireEvent.click(screen.getByRole('button', { name: 'Save Draft' }));

  await waitFor(() => expect(fetchCalls('POST', '/admin/api/world').length).toBe(1));
  const body = lastBody('POST', '/admin/api/world');
  // eslint-disable-next-line testing-library/no-node-access -- world.scripts is plain JSON, not document.scripts
  expect(body.world.scripts[0].path).toBe('backend/world_scripts/..evil.py');
});

test('falls back to a blank mob palette when the definitions endpoint is missing', async () => {
  await renderBuilder({
    'GET /admin/api/world/mob-definitions': () => Promise.resolve({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: 'not found' }),
    }),
  });

  const palette = screen.getByLabelText('Mob template');
  expect(within(palette).queryByRole('option', { name: /wolf/ })).not.toBeInTheDocument();
  expect(within(palette).getByRole('option', { name: 'Blank mob' })).toBeInTheDocument();
});
