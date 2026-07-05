import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from '@xyflow/react';
import {
  DEFAULT_REGION_COLOR,
  OPPOSITE_DIRECTIONS,
  exitEntries,
  finiteNumber,
  getRoomPosition,
  roomHasPuzzle,
  roomHasStrippedLogic,
} from './worldUtils';

const FIT_VIEW_OPTIONS = { padding: 0.2, duration: 250 };
const MULTI_SELECTION_KEYS = ['Meta', 'Control', 'Shift'];

const NODE_WIDTH = 136;
const NODE_HEIGHT = 66;
const HANDLE_SIZE = 8;

// Every direction gets a fixed anchor on the room rectangle: north leaves the
// top edge, northeast the top-right corner, and so on. up/down/in/out get
// offset spots so they don't overlap the cardinals. Dragging a connection out
// of an anchor creates an exit in that direction.
const DIRECTION_ANCHORS = {
  north: { x: NODE_WIDTH / 2, y: 0, position: Position.Top },
  northeast: { x: NODE_WIDTH, y: 0, position: Position.Top },
  east: { x: NODE_WIDTH, y: NODE_HEIGHT / 2, position: Position.Right },
  southeast: { x: NODE_WIDTH, y: NODE_HEIGHT, position: Position.Bottom },
  south: { x: NODE_WIDTH / 2, y: NODE_HEIGHT, position: Position.Bottom },
  southwest: { x: 0, y: NODE_HEIGHT, position: Position.Bottom },
  west: { x: 0, y: NODE_HEIGHT / 2, position: Position.Left },
  northwest: { x: 0, y: 0, position: Position.Top },
  up: { x: NODE_WIDTH * 0.75, y: 0, position: Position.Top },
  down: { x: NODE_WIDTH * 0.25, y: NODE_HEIGHT, position: Position.Bottom },
  in: { x: 0, y: NODE_HEIGHT * 0.25, position: Position.Left },
  out: { x: NODE_WIDTH, y: NODE_HEIGHT * 0.75, position: Position.Right },
};

// Labels only where geometry doesn't already say it: the anchor encodes
// compass directions, so those stay unlabeled unless the exit is one-way.
const COMPASS_DIRECTIONS = new Set([
  'north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest',
]);

function RoomNode({ data }) {
  return (
    <div className="room-node" style={{ borderColor: data.regionColor }}>
      {Object.entries(DIRECTION_ANCHORS).map(([direction, anchor]) => (
        <React.Fragment key={direction}>
          <Handle
            type="target"
            id={`t-${direction}`}
            position={anchor.position}
            className="room-node__handle"
            style={{ left: anchor.x, top: anchor.y }}
          />
          <Handle
            type="source"
            id={`s-${direction}`}
            position={anchor.position}
            className="room-node__handle"
            title={`Drag to dig or connect ${direction}`}
            style={{ left: anchor.x, top: anchor.y }}
          />
        </React.Fragment>
      ))}
      <div className="room-node__name">{data.label}</div>
      <div className="room-node__id">{data.roomId}</div>
      {(data.isDark || data.hasPuzzle || data.hasStrippedLogic || data.isSpawn) ? (
        <div className="room-node__badges">
          {data.isSpawn ? <span title="Spawn room">✦</span> : null}
          {data.isDark ? <span title="Dark room">☾</span> : null}
          {data.hasPuzzle ? <span title="Has stateful items / puzzle">⚙</span> : null}
          {data.hasStrippedLogic ? <span title="Carries Python-only logic that this editor cannot modify">ƒ</span> : null}
        </div>
      ) : null}
    </div>
  );
}

const NODE_TYPES = { room: RoomNode };

const STATIC_HANDLES = Object.entries(DIRECTION_ANCHORS).flatMap(([direction, anchor]) => [
  {
    id: `t-${direction}`,
    type: 'target',
    position: anchor.position,
    x: anchor.x - HANDLE_SIZE / 2,
    y: anchor.y - HANDLE_SIZE / 2,
    width: HANDLE_SIZE,
    height: HANDLE_SIZE,
  },
  {
    id: `s-${direction}`,
    type: 'source',
    position: anchor.position,
    x: anchor.x - HANDLE_SIZE / 2,
    y: anchor.y - HANDLE_SIZE / 2,
    width: HANDLE_SIZE,
    height: HANDLE_SIZE,
  },
]);

function buildNodes(rooms, world, selectedRoomIdSet, spawnRoomId) {
  const regionById = new Map((world.regions || []).map((region) => [region.id, region]));
  return rooms.map((room, index) => ({
    id: room.id,
    type: 'room',
    position: getRoomPosition(room, index),
    // Fixed dimensions + static handle bounds render nodes and edges
    // immediately instead of waiting on ResizeObserver measurement.
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
    handles: STATIC_HANDLES,
    selected: selectedRoomIdSet.has(room.id),
    data: {
      label: room.name,
      roomId: room.id,
      regionColor: regionById.get(room.region_id)?.color || DEFAULT_REGION_COLOR,
      isDark: Boolean(room.is_dark),
      isSpawn: room.id === spawnRoomId,
      hasPuzzle: roomHasPuzzle(room),
      hasStrippedLogic: roomHasStrippedLogic(room),
    },
  }));
}

/**
 * One edge per connection pair: symmetric pairs collapse into a single
 * two-way edge, one-way exits render dashed so asymmetry is visible at a
 * glance.
 */
function buildEdges(rooms) {
  const roomById = new Map(rooms.map((room) => [room.id, room]));
  const edges = [];
  const consumed = new Set();

  rooms.forEach((room) => {
    exitEntries(room.exits).forEach(([direction, targetId]) => {
      const pairKey = `${room.id}|${direction}|${targetId}`;
      if (consumed.has(pairKey) || !roomById.has(targetId)) {
        return;
      }
      const opposite = OPPOSITE_DIRECTIONS[direction];
      const target = roomById.get(targetId);
      const isSymmetric = Boolean(opposite && target.exits?.[opposite] === room.id);
      if (isSymmetric) {
        consumed.add(`${targetId}|${opposite}|${room.id}`);
      }
      // Anchor the line at the direction's spot on each rectangle: a north
      // exit leaves the top of the source and enters the bottom (south side)
      // of the target.
      const sourceHandle = DIRECTION_ANCHORS[direction] ? `s-${direction}` : undefined;
      const targetHandle = opposite && DIRECTION_ANCHORS[opposite] ? `t-${opposite}` : undefined;
      const showLabel = !COMPASS_DIRECTIONS.has(direction) || !isSymmetric;
      edges.push({
        id: `${room.id}-${direction}-${targetId}`,
        source: room.id,
        target: targetId,
        sourceHandle,
        targetHandle,
        type: 'straight',
        ...(showLabel ? { label: isSymmetric ? direction : `${direction} →` } : {}),
        className: isSymmetric ? 'world-flow__edge' : 'world-flow__edge world-flow__edge--oneway',
        ...(isSymmetric ? {} : { style: { strokeDasharray: '6 4' } }),
      });
    });
  });

  return edges;
}

function sameIdSet(left, right) {
  if (left.size !== right.size) {
    return false;
  }
  for (const value of left) {
    if (!right.has(value)) {
      return false;
    }
  }
  return true;
}

function GraphInner({
  rooms,
  world,
  selectedRoomIds,
  spawnRoomId,
  gridSize,
  fitViewToken,
  focusRequest,
  onSelectRoom,
  onSelectionChange,
  onMoveRooms,
  onConnectRooms,
  pointerInteractingRef,
}) {
  const selectedRoomIdSet = useMemo(() => new Set(selectedRoomIds), [selectedRoomIds]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges] = useEdgesState([]);
  const instance = useReactFlow();

  useEffect(() => {
    setNodes(buildNodes(rooms, world, selectedRoomIdSet, spawnRoomId));
    setEdges(buildEdges(rooms));
  }, [rooms, world, selectedRoomIdSet, spawnRoomId, setNodes, setEdges]);

  useEffect(() => {
    if (fitViewToken > 0) {
      const frame = requestAnimationFrame(() => instance.fitView(FIT_VIEW_OPTIONS));
      return () => cancelAnimationFrame(frame);
    }
    return undefined;
  }, [fitViewToken, instance]);

  const roomsRef = useRef(rooms);
  roomsRef.current = rooms;

  // Consume each focus request exactly once — rooms are read through a ref so
  // unrelated re-renders don't re-trigger the pan.
  useEffect(() => {
    if (!focusRequest?.roomId) {
      return;
    }
    const room = roomsRef.current.find((candidate) => candidate.id === focusRequest.roomId);
    if (!room) {
      return;
    }
    const position = getRoomPosition(room, 0);
    instance.setCenter(position.x + NODE_WIDTH / 2, position.y + NODE_HEIGHT / 2, { zoom: 1, duration: 250 });
  }, [focusRequest, instance]);

  // React Flow re-emits its (possibly stale) internal selection whenever we
  // replace nodes programmatically. Only honour selection events while the
  // user is actually pointer-interacting with the canvas — programmatic
  // updates (room-list clicks, dig, load) must not be clobbered by echoes.
  const handleSelectionChange = useCallback(({ nodes: selectedNodes = [] }) => {
    if (!pointerInteractingRef.current) {
      return;
    }
    const nextIds = new Set(selectedNodes.map((node) => node.id));
    if (!sameIdSet(nextIds, selectedRoomIdSet)) {
      onSelectionChange(Array.from(nextIds));
    }
  }, [onSelectionChange, selectedRoomIdSet, pointerInteractingRef]);

  const handleNodeClick = useCallback((event, node) => {
    onSelectRoom(node.id, Boolean(event?.metaKey || event?.ctrlKey || event?.shiftKey));
  }, [onSelectRoom]);

  const handleNodeDragStop = useCallback((event, node, draggedNodes) => {
    const moved = (draggedNodes && draggedNodes.length ? draggedNodes : [node])
      .filter((dragged) => dragged?.position)
      .map((dragged) => ({
        roomId: dragged.id,
        x: finiteNumber(dragged.position.x, 0),
        y: finiteNumber(dragged.position.y, 0),
      }));
    if (moved.length > 0) {
      onMoveRooms(moved);
    }
  }, [onMoveRooms]);

  const handleConnect = useCallback((connection) => {
    if (connection.source && connection.target && connection.source !== connection.target) {
      // The anchor the drag started from names the direction (s-north → north).
      const handleDirection = (connection.sourceHandle || '').replace(/^[st]-/, '');
      onConnectRooms(
        connection.source,
        connection.target,
        DIRECTION_ANCHORS[handleDirection] ? handleDirection : null
      );
    }
  }, [onConnectRooms]);

  return (
    <ReactFlow
      className="world-flow"
      aria-label="World graph"
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      onNodesChange={onNodesChange}
      onNodeClick={handleNodeClick}
      onSelectionChange={handleSelectionChange}
      onNodeDragStop={handleNodeDragStop}
      onConnect={handleConnect}
      connectionMode="loose"
      connectionRadius={28}
      nodesDraggable
      panOnDrag
      selectionOnDrag
      minZoom={0.1}
      multiSelectionKeyCode={MULTI_SELECTION_KEYS}
      deleteKeyCode={null}
      fitView
      fitViewOptions={FIT_VIEW_OPTIONS}
      proOptions={{ hideAttribution: true }}
    >
      <MiniMap
        pannable
        zoomable
        bgColor="#e3cb92"
        maskColor="rgba(58, 37, 24, 0.25)"
        nodeColor="#a9834a"
        nodeStrokeColor="#4c3218"
      />
      <Controls />
      <Background gap={gridSize} />
    </ReactFlow>
  );
}

export default function WorldGraph(props) {
  const pointerInteractingRef = useRef(false);
  const clearTimerRef = useRef(null);

  const handlePointerDown = useCallback(() => {
    if (clearTimerRef.current) {
      clearTimeout(clearTimerRef.current);
    }
    pointerInteractingRef.current = true;
  }, []);

  const handlePointerUp = useCallback(() => {
    // Selection events can arrive just after pointer-up; keep the window
    // open briefly before treating further events as programmatic echoes.
    clearTimerRef.current = setTimeout(() => {
      pointerInteractingRef.current = false;
    }, 150);
  }, []);

  return (
    <div
      className="world-flow-shell"
      data-testid="world-flow-shell"
      onPointerDownCapture={handlePointerDown}
      onPointerUpCapture={handlePointerUp}
    >
      <ReactFlowProvider>
        <GraphInner
          {...props}
          gridSize={finiteNumber(props.world?.layout?.grid_size, 24) || 24}
          pointerInteractingRef={pointerInteractingRef}
        />
      </ReactFlowProvider>
    </div>
  );
}
