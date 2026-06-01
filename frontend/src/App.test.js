import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import App from './App';
import io from 'socket.io-client';

jest.mock('socket.io-client', () => jest.fn());
jest.mock('@xyflow/react', () => ({
  ReactFlowProvider: ({ children }) => <div data-testid="react-flow-provider">{children}</div>,
  ReactFlow: ({
    nodes = [],
    edges = [],
    onNodeClick,
    onNodeDragStop,
    onNodesChange,
    onSelectionChange,
    children,
  }) => {
    const React = require('react');
    React.useEffect(() => {
      onSelectionChange?.({ nodes: [], edges: [] });
    }, [onSelectionChange]);

    return (
      <div aria-label="World graph" data-edge-count={edges.length}>
        <button
          type="button"
          onClick={() => {
            if (nodes[0]) {
              onNodeClick?.({}, nodes[0]);
            }
          }}
        >
          Select first flow node
        </button>
        <button
          type="button"
          onClick={() => {
            if (nodes[0]) {
              onNodeDragStop?.({}, { ...nodes[0], position: { x: 444, y: 222 } });
            }
          }}
        >
          Drag first flow node
        </button>
        <button
          type="button"
          onClick={() => {
            if (nodes[0]) {
              onNodesChange?.([{
                id: nodes[0].id,
                type: 'position',
                position: { x: 555, y: 333 },
                dragging: true,
              }]);
            }
          }}
        >
          Move first flow node
        </button>
        <button
          type="button"
          onClick={() => onSelectionChange?.({ nodes: nodes.slice(0, 2), edges: [] })}
        >
          Select two flow nodes
        </button>
        {nodes.map((node) => (
          <div key={node.id} data-testid={`flow-node-${node.id}`}>
            {node.data?.label}
          </div>
        ))}
        {children}
      </div>
    );
  },
  Background: () => <div data-testid="flow-background" />,
  Controls: () => <div data-testid="flow-controls" />,
  MiniMap: () => <div data-testid="flow-minimap" />,
}));

const sampleWorld = {
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
      items: [{ id: 'fountain', name: 'Old Fountain', description: 'Cold stone.' }],
      mobs: [{ id: 'guard', name: 'Town Guard', description: 'Watching the road.' }],
      scripts: [{ id: 'welcome', path: 'scripts/welcome.py', trigger: 'enter' }],
      is_dark: false,
      is_outdoor: true,
      hidden_items: [{ id: 'coin', item: { id: 'coin', name: 'Coin', description: 'Hidden.' } }],
    },
    {
      id: 'woods',
      name: 'Dark Woods',
      description: 'Tall trees block the sky.',
      x: 300,
      y: 90,
      z: 0,
      region_id: 'wilds',
      tags: [],
      layout: { x: 300, y: 90, layer_id: 'surface', pinned: true },
      exits: { south: 'square' },
      items: [],
      mobs: [],
      scripts: [],
    },
  ],
};

let socket;

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

beforeEach(() => {
  routeTo('/');
  installSocketMock();
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  localStorage.clear();
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.clearAllMocks();
});

test('renders the existing game terminal on normal paths', () => {
  render(<App />);

  expect(screen.getByText('The Forgotten Realms')).toBeInTheDocument();
  expect(screen.getByPlaceholderText('Type your command....')).toBeInTheDocument();
  expect(screen.queryByText('Admin World Builder')).not.toBeInTheDocument();
});

test('renders the admin world builder route without replacing the game terminal elsewhere', () => {
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
  global.fetch.mockImplementation(() => okJson({ world: sampleWorld }));

  render(<App />);
  act(() => {
    socket.handlers.adminToken({ token: 'token-123' });
  });

  await screen.findAllByText('Village Square');

  expect(localStorage.getItem('adminToken')).toBe('token-123');
  expect(global.fetch).toHaveBeenCalledWith(
    'http://localhost:8080/admin/api/world',
    expect.objectContaining({
      headers: expect.objectContaining({ Authorization: 'Bearer token-123' }),
    })
  );
  expect(screen.getByLabelText('World graph')).toBeInTheDocument();
  expect(screen.getByTestId('flow-controls')).toBeInTheDocument();
  expect(screen.getByTestId('flow-minimap')).toBeInTheDocument();
  expect(screen.getByText('square')).toBeInTheDocument();
});

test('clears expired admin tokens and returns to the login panel', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'expired-token');
  global.fetch.mockImplementationOnce(() => Promise.resolve({
    ok: false,
    status: 401,
    json: () => Promise.resolve({
      error: 'unauthorized',
      message: 'You must be logged in as stupidgem to use the world builder.',
    }),
  }));

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent('You must be logged in as stupidgem');
  expect(localStorage.getItem('adminToken')).toBeNull();
  expect(screen.getByLabelText('Admin login panel')).toBeInTheDocument();
  expect(screen.getAllByText(/Waiting for stupidgem admin token/i).length).toBeGreaterThan(0);
});

test('edits a selected room and saves the changed world payload', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({ world: sampleWorld }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/draft_world.json' },
    }));

  render(<App />);

  const nameInput = await screen.findByLabelText('Room name');
  fireEvent.change(nameInput, { target: { value: 'Market Square' } });
  fireEvent.change(screen.getByLabelText('Room description'), {
    target: { value: 'Vendors are shouting across the stones.' },
  });
  fireEvent.click(screen.getByRole('button', { name: /add script/i }));
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => {
    expect(global.fetch).toHaveBeenLastCalledWith(
      'http://localhost:8080/admin/api/world',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer stored-token' }),
        body: expect.any(String),
      })
    );
  });

  const payload = JSON.parse(global.fetch.mock.calls[1][1].body);
  expect(payload.world.rooms[0]).toEqual(
    expect.objectContaining({
      id: 'square',
      name: 'Market Square',
      description: 'Vendors are shouting across the stones.',
      is_outdoor: true,
      hidden_items: sampleWorld.rooms[0].hidden_items,
      region_id: 'village',
      layout: expect.objectContaining({ layer_id: 'surface' }),
    })
  );
  expect(payload.world.metadata).toEqual({ source: 'test' });
  expect(payload.world.regions).toHaveLength(2);
  expect(payload.world.layers).toHaveLength(2);
  expect(payload.world.tags).toHaveLength(1);
  expect(payload.world.rooms[0].mobs).toBeUndefined();
  expect(payload.world.mobs[0]).toEqual(
    expect.objectContaining({
      id: 'guard',
      current_room: 'square',
    })
  );
  expect(payload.world.scripts).toEqual(
    expect.arrayContaining([
      expect.objectContaining({
        path: 'backend/world_scripts/new_script.py',
        content: expect.stringContaining('def run'),
        room_id: 'square',
      }),
    ])
  );
  expect(await screen.findByText(/Save complete/i)).toBeInTheDocument();
});

test('runs validate apply reset and publish actions from the admin toolbar', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({ world: sampleWorld }))
    .mockImplementationOnce(() => okJson({
      validation: {
        ok: false,
        errors: [{ code: 'broken_exit', message: 'Exit north points nowhere.' }],
        warnings: [],
      },
    }))
    .mockImplementationOnce(() => okJson({ applied: { rooms: 2, mobs: 1 } }))
    .mockImplementationOnce(() => okJson({
      world: {
        ...sampleWorld,
        rooms: [{ ...sampleWorld.rooms[0], id: 'reset-room', name: 'Reset Room' }],
      },
    }))
    .mockImplementationOnce(() => okJson({
      publish: { committed: true, pushed: true, commit: 'abc123' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /validate/i }));
  expect(await screen.findByText(/Exit north points nowhere/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /apply live/i }));
  expect(await screen.findByText(/Applied live/i)).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /reset baseline/i }));
  expect((await screen.findAllByText('Reset Room')).length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole('button', { name: /publish git/i }));
  expect(await screen.findByText(/Publish complete/i)).toBeInTheDocument();

  const calledPaths = global.fetch.mock.calls.map(([url]) => url);
  expect(calledPaths).toEqual([
    'http://localhost:8080/admin/api/world',
    'http://localhost:8080/admin/api/world/validate',
    'http://localhost:8080/admin/api/world/apply',
    'http://localhost:8080/admin/api/world/reset',
    'http://localhost:8080/admin/api/world/publish',
  ]);

  const validationPanel = screen.getByLabelText('Validation panel');
  expect(within(validationPanel).getByText('broken_exit')).toBeInTheDocument();
});

test('surfaces publish failures instead of reporting success', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({ world: sampleWorld }))
    .mockImplementationOnce(() => Promise.resolve({
      ok: false,
      status: 500,
      json: () => Promise.resolve({
        error: 'publish_failed',
        message: 'tests failed',
        publish: { ok: false, step: 'check', error: 'tests failed' },
      }),
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /publish git/i }));

  expect(await screen.findByText(/publish failed/i)).toBeInTheDocument();
  expect(screen.getByRole('alert')).toHaveTextContent('tests failed');
});

test('drags a React Flow room node and saves updated layout coordinates', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({ world: sampleWorld }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/draft_world.json' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /drag first flow node/i }));
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  const payload = JSON.parse(global.fetch.mock.calls[1][1].body);
  expect(payload.world.rooms[0]).toEqual(
    expect.objectContaining({
      x: 444,
      y: 222,
      layout: expect.objectContaining({ x: 444, y: 222, pinned: true }),
    })
  );
});

test('syncs React Flow controlled node position changes while dragging', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({ world: sampleWorld }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/draft_world.json' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /move first flow node/i }));
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  const payload = JSON.parse(global.fetch.mock.calls[1][1].body);
  expect(payload.world.rooms[0]).toEqual(
    expect.objectContaining({
      x: 555,
      y: 333,
      layout: expect.objectContaining({ x: 555, y: 333, pinned: true }),
    })
  );
});

test('adds rooms with unique ids and saves the selected new room layout', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  const worldWithExistingGeneratedRoom = {
    ...sampleWorld,
    rooms: [
      sampleWorld.rooms[0],
      {
        ...sampleWorld.rooms[1],
        id: 'new-room-3',
        name: 'Existing Draft Room',
      },
    ],
  };
  global.fetch
    .mockImplementationOnce(() => okJson({ world: worldWithExistingGeneratedRoom }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/draft_world.json' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /add room/i }));
  expect(screen.getByLabelText('Room id')).toHaveValue('new-room-4');
  expect(screen.getByTestId('flow-node-new-room-4')).toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  const payload = JSON.parse(global.fetch.mock.calls[1][1].body);
  expect(payload.world.rooms.map((room) => room.id)).toEqual([
    'square',
    'new-room-3',
    'new-room-4',
  ]);
  expect(payload.world.rooms[2]).toEqual(
    expect.objectContaining({
      region_id: 'village',
      x: 520,
      y: 140,
      layout: expect.objectContaining({ x: 520, y: 140, layer_id: 'surface' }),
    })
  );
});

test('bulk edits multi-selected room metadata through rich controls', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({ world: sampleWorld }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/draft_world.json' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /select two flow nodes/i }));
  expect(screen.getByText(/2 rooms selected/i)).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText('Bulk region'), { target: { value: 'wilds' } });
  fireEvent.change(screen.getByLabelText('Bulk layer'), { target: { value: 'surface' } });
  fireEvent.click(screen.getByRole('button', { name: /apply bulk metadata/i }));
  fireEvent.click(screen.getByRole('button', { name: /snap selected to grid/i }));
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  const payload = JSON.parse(global.fetch.mock.calls[1][1].body);
  expect(payload.world.rooms.map((room) => room.region_id)).toEqual(['wilds', 'wilds']);
  expect(payload.world.rooms.every((room) => room.layout.layer_id === 'surface')).toBe(true);
});

test('uses typed rich editors for exits items mobs scripts and layer filtering', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({ world: sampleWorld }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/draft_world.json' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByLabelText('Show surface layer'));
  expect(screen.queryByTestId('flow-node-square')).not.toBeInTheDocument();
  fireEvent.click(screen.getByLabelText('Show surface layer'));

  fireEvent.change(screen.getByLabelText('Exit north target'), { target: { value: 'woods' } });
  fireEvent.change(screen.getByLabelText('Item 1 name'), { target: { value: 'Restored Fountain' } });
  fireEvent.change(screen.getByLabelText('Mob 1 name'), { target: { value: 'Captain' } });
  fireEvent.change(screen.getByLabelText('Script 1 trigger'), { target: { value: 'look' } });
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  const payload = JSON.parse(global.fetch.mock.calls[1][1].body);
  expect(payload.world.rooms[0].exits.north).toBe('woods');
  expect(payload.world.rooms[0].items[0].name).toBe('Restored Fountain');
  expect(payload.world.mobs[0].name).toBe('Captain');
  expect(payload.world.scripts[0].trigger).toBe('look');
});

test('keeps mob and script room references consistent after room rename and delete', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  const worldWithTopLevelRefs = {
    ...sampleWorld,
    mobs: [
      { id: 'legacy-guard', name: 'Legacy Guard', current_room: 'square' },
      { id: 'unassigned', name: 'Unassigned' },
    ],
    scripts: [
      { id: 'legacy-script', path: 'backend/world_scripts/legacy.py', room_id: 'square' },
      { id: 'global-script', path: 'backend/world_scripts/global.py' },
    ],
  };
  global.fetch
    .mockImplementationOnce(() => okJson({ world: worldWithTopLevelRefs }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/draft_world.json' },
    }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/draft_world.json' },
    }));

  render(<App />);
  const idInput = await screen.findByLabelText('Room id');

  fireEvent.change(idInput, { target: { value: 'market' } });
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
  const renamePayload = JSON.parse(global.fetch.mock.calls[1][1].body);
  expect(renamePayload.world.rooms[1].exits.south).toBe('market');
  expect(renamePayload.world.mobs).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ id: 'guard', current_room: 'market' }),
      expect.objectContaining({ id: 'legacy-guard', current_room: 'market' }),
    ])
  );
  expect(renamePayload.world.scripts).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ id: 'welcome', room_id: 'market' }),
      expect.objectContaining({ id: 'legacy-script', room_id: 'market' }),
    ])
  );

  fireEvent.click(screen.getByRole('button', { name: /delete selected/i }));
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
  const deletePayload = JSON.parse(global.fetch.mock.calls[2][1].body);
  expect(deletePayload.world.rooms.map((room) => room.id)).toEqual(['woods']);
  expect(deletePayload.world.mobs.every((mob) => mob.current_room !== 'market')).toBe(true);
  expect(deletePayload.world.scripts.every((script) => script.room_id !== 'market')).toBe(true);
});

test('loads draft manifest and switches between independent draft worlds', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({
      world: sampleWorld,
      draft: { id: 'main', name: 'Main Draft' },
      active_draft_id: 'main',
      drafts: [
        { id: 'main', name: 'Main Draft', room_count: 2, updated_at: '2026-06-01T20:00:00Z' },
        { id: 'experiment', name: 'Experiment', room_count: 1, updated_at: '2026-06-01T20:10:00Z' },
      ],
    }))
    .mockImplementationOnce(() => okJson({
      world: {
        ...sampleWorld,
        rooms: [{ ...sampleWorld.rooms[0], id: 'crypt', name: 'Crypt' }],
      },
      draft: { id: 'experiment', name: 'Experiment' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');
  expect(screen.getByLabelText('Draft project')).toHaveValue('main');

  fireEvent.change(screen.getByLabelText('Draft project'), { target: { value: 'experiment' } });

  expect(await screen.findByTestId('flow-node-crypt')).toBeInTheDocument();
  expect(screen.getAllByText('Crypt').length).toBeGreaterThan(0);
  expect(global.fetch.mock.calls[1][0]).toBe('http://localhost:8080/admin/api/world/drafts/experiment');
});

test('prompts before switching away from unsaved draft changes', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);
  global.fetch
    .mockImplementationOnce(() => okJson({
      world: sampleWorld,
      draft: { id: 'main', name: 'Main Draft' },
      active_draft_id: 'main',
      drafts: [
        { id: 'main', name: 'Main Draft', room_count: 2 },
        { id: 'experiment', name: 'Experiment', room_count: 1 },
      ],
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.change(screen.getByLabelText('Room name'), { target: { value: 'Changed Square' } });
  expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Draft project'), { target: { value: 'experiment' } });

  expect(confirmSpy).toHaveBeenCalledWith('Switch drafts and discard unsaved changes?');
  expect(global.fetch).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Draft project')).toHaveValue('main');
  confirmSpy.mockRestore();
});

test('creates a new draft from the active draft and saves only the selected draft', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({
      world: sampleWorld,
      draft: { id: 'main', name: 'Main Draft' },
      active_draft_id: 'main',
      drafts: [{ id: 'main', name: 'Main Draft', room_count: 2 }],
    }))
    .mockImplementationOnce(() => okJson({
      draft: { id: 'experiment', name: 'Experiment' },
      world: sampleWorld,
      manifest: {
        active_draft_id: 'main',
        drafts: [
          { id: 'main', name: 'Main Draft', room_count: 2 },
          { id: 'experiment', name: 'Experiment', room_count: 2 },
        ],
      },
    }))
    .mockImplementationOnce(() => okJson({
      validation: { ok: true, errors: [], warnings: [] },
      saved: { path: 'storage/world_builder/drafts/experiment.json' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /new draft/i }));
  const dialog = await screen.findByRole('dialog', { name: /create draft project/i });
  expect(dialog).toBeInTheDocument();
  fireEvent.change(within(dialog).getByLabelText('Draft name'), { target: { value: 'Experiment' } });
  fireEvent.change(within(dialog).getByLabelText('Description'), { target: { value: 'Test branch' } });
  fireEvent.change(within(dialog).getByLabelText('Draft source'), { target: { value: 'active' } });
  fireEvent.click(within(dialog).getByRole('button', { name: /create draft/i }));

  expect(await screen.findByText(/Editing Draft: Experiment/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /save draft/i }));

  await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(3));
  expect(global.fetch.mock.calls[1][0]).toBe('http://localhost:8080/admin/api/world/drafts');
  expect(JSON.parse(global.fetch.mock.calls[1][1].body)).toEqual(
    expect.objectContaining({ name: 'Experiment', description: 'Test branch', source: 'active' })
  );
  expect(global.fetch.mock.calls[2][0]).toBe('http://localhost:8080/admin/api/world/drafts/experiment');
});

test('apply and publish target the selected draft project', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({
      world: sampleWorld,
      draft: { id: 'experiment', name: 'Experiment' },
      active_draft_id: 'experiment',
      drafts: [{ id: 'experiment', name: 'Experiment', room_count: 2 }],
    }))
    .mockImplementationOnce(() => okJson({
      applied: { rooms: 2, mobs: 1 },
      validation: { ok: true, errors: [], warnings: [] },
    }))
    .mockImplementationOnce(() => okJson({
      publish: { ok: true, step: 'push' },
      validation: { ok: true, errors: [], warnings: [] },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /apply live/i }));
  expect(await screen.findByText(/Applied live/i)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /publish git/i }));
  expect(await screen.findByText(/Publish complete/i)).toBeInTheDocument();

  expect(global.fetch.mock.calls[1][0]).toBe('http://localhost:8080/admin/api/world/drafts/experiment/apply');
  expect(global.fetch.mock.calls[2][0]).toBe('http://localhost:8080/admin/api/world/drafts/experiment/publish');
});

test('reset baseline targets the selected draft project', async () => {
  routeTo('/admin/world-builder');
  localStorage.setItem('adminToken', 'stored-token');
  global.fetch
    .mockImplementationOnce(() => okJson({
      world: sampleWorld,
      draft: { id: 'experiment', name: 'Experiment' },
      active_draft_id: 'experiment',
      drafts: [{ id: 'experiment', name: 'Experiment', room_count: 2 }],
    }))
    .mockImplementationOnce(() => okJson({
      world: {
        ...sampleWorld,
        rooms: [{ ...sampleWorld.rooms[0], id: 'reset-room', name: 'Reset Room' }],
      },
      draft: { id: 'experiment', name: 'Experiment' },
      active_draft_id: 'experiment',
      drafts: [{ id: 'experiment', name: 'Experiment', room_count: 1 }],
      saved: { path: 'storage/world_builder/drafts/experiment.json' },
    }));

  render(<App />);
  await screen.findAllByText('Village Square');

  fireEvent.click(screen.getByRole('button', { name: /reset baseline/i }));

  expect(await screen.findByTestId('flow-node-reset-room')).toBeInTheDocument();
  expect(global.fetch.mock.calls[1][0]).toBe('http://localhost:8080/admin/api/world/drafts/experiment/reset');
});
