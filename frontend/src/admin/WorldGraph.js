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

function RoomNode({ data }) {
  return (
    <div className="room-node" style={{ borderColor: data.regionColor }}>
      <Handle type="target" position={Position.Left} className="room-node__handle" />
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
      <Handle type="source" position={Position.Right} className="room-node__handle" />
    </div>
  );
}

const NODE_TYPES = { room: RoomNode };

const NODE_WIDTH = 136;
const NODE_HEIGHT = 66;

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
    handles: [
      { type: 'target', position: Position.Left, x: -4, y: NODE_HEIGHT / 2 - 4, width: 8, height: 8 },
      { type: 'source', position: Position.Right, x: NODE_WIDTH - 4, y: NODE_HEIGHT / 2 - 4, width: 8, height: 8 },
    ],
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
      edges.push({
        id: `${room.id}-${direction}-${targetId}`,
        source: room.id,
        target: targetId,
        label: isSymmetric ? direction : `${direction} →`,
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
      onConnectRooms(connection.source, connection.target);
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
      <MiniMap pannable zoomable />
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
