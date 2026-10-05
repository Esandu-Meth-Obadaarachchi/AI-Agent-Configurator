"use client";

import { ArrowsOut, MagicWand, Minus, Plus } from "@phosphor-icons/react";
import {
  Background,
  BackgroundVariant,
  type Connection,
  type Edge,
  MiniMap,
  ReactFlow,
  useReactFlow,
} from "@xyflow/react";
import { type DragEvent, useCallback, useEffect, useMemo, useRef } from "react";

import { api } from "@/lib/api";
import { CATALOG, colorFor, NODE_DEFS } from "@/lib/catalog";
import { connectionProblem } from "@/lib/connect";
import { useStore } from "@/lib/store";
import type { BlockNode as BlockNodeType } from "@/lib/types";

import { BlockNode } from "./block-node";
import { EDGE_TYPES, EdgeMarkers } from "./edges";
import { TraceTicker } from "./trace-ticker";
import { IconButton } from "./ui";

export const DRAG_MIME = "application/x-agent-block";

const NODE_TYPES = Object.fromEntries(CATALOG.nodes.map((n) => [n.type, BlockNode]));

export function Canvas() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const onNodesChange = useStore((s) => s.onNodesChange);
  const onEdgesChange = useStore((s) => s.onEdgesChange);
  const onConnect = useStore((s) => s.onConnect);
  const addNode = useStore((s) => s.addNode);
  const syncSelection = useStore((s) => s.syncSelection);
  const fitRequest = useStore((s) => s.fitRequest);
  const rf = useReactFlow<BlockNodeType>();
  const wrapper = useRef<HTMLDivElement>(null);

  /**
   * Fit the whole loop when it fits at a readable zoom. Otherwise keep the text readable
   * and anchor on the left, so the flow reads from its start (the minimap shows the rest).
   */
  const frame = useCallback(
    (duration = 350) => {
      const box = wrapper.current?.getBoundingClientRect();
      const all = rf.getNodes();
      if (!box || !all.length) return;
      const b = rf.getNodesBounds(all);
      const pad = 48;
      const fit = Math.min((box.width - pad * 2) / b.width, (box.height - pad * 2) / b.height);
      const zoom = Math.max(0.8, Math.min(1, fit));
      const x = fit >= 0.8 ? (box.width - b.width * zoom) / 2 - b.x * zoom : pad - b.x * zoom;
      const y = b.height * zoom <= box.height - pad * 2 ? (box.height - b.height * zoom) / 2 - b.y * zoom : pad - b.y * zoom;
      void rf.setViewport({ x, y, zoom }, { duration });
    },
    [rf],
  );

  useEffect(() => {
    if (fitRequest) {
      const t = setTimeout(() => frame(), 80);
      return () => clearTimeout(t);
    }
  }, [fitRequest, frame]);

  const typeOf = useCallback((id: string) => useStore.getState().nodes.find((n) => n.id === id)?.type, []);

  const isValidConnection = useCallback((c: Connection | Edge) => connectionProblem(c, typeOf) === null, [typeOf]);

  const onDragOver = useCallback((e: DragEvent) => {
    if (e.dataTransfer.types.includes(DRAG_MIME)) {
      e.preventDefault();
      e.dataTransfer.dropEffect = "copy";
    }
  }, []);

  const onDrop = useCallback(
    (e: DragEvent) => {
      const type = e.dataTransfer.getData(DRAG_MIME);
      if (!type || !NODE_DEFS[type]) return;
      e.preventDefault();
      const point = rf.screenToFlowPosition({ x: e.clientX, y: e.clientY });
      // Dropping a tool or knowledge base onto an agent attaches it straight away.
      const host = NODE_DEFS[type].role === "resource"
        ? rf.getIntersectingNodes({ x: point.x, y: point.y, width: 1, height: 1 }).find((n) => n.type === "agent" || (type === "knowledge" && n.type === "retriever"))
        : undefined;
      const position = host
        ? { x: host.position.x + 20, y: host.position.y + (host.measured?.height ?? 120) + 90 }
        : { x: point.x - 110, y: point.y - 30 };
      addNode(type, position, host?.id);
    },
    [addNode, rf],
  );

  const onSelectionChange = useCallback(
    ({ nodes: selected }: { nodes: BlockNodeType[] }) => {
      syncSelection(selected.length === 1 ? selected[0].id : null);
    },
    [syncSelection],
  );

  const tidy = useCallback(async () => {
    const state = useStore.getState();
    try {
      const laidOut = await api.layout(state.spec());
      state.loadSpec(laidOut, { keepHistory: true });
    } catch (err) {
      state.notify((err as Error).message, "error");
    }
  }, []);

  const defaultEdgeOptions = useMemo(() => ({ interactionWidth: 24 }), []);

  return (
    <div ref={wrapper} className="relative size-full" onDragOver={onDragOver} onDrop={onDrop}>
      <EdgeMarkers />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        isValidConnection={isValidConnection}
        onSelectionChange={onSelectionChange}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionRadius={28}
        snapToGrid
        snapGrid={[10, 10]}
        minZoom={0.2}
        maxZoom={1.8}
        deleteKeyCode={["Backspace", "Delete"]}
        multiSelectionKeyCode={["Meta", "Shift"]}
        proOptions={{ hideAttribution: true }}
        onInit={() => setTimeout(() => frame(0), 50)}
        aria-label="Agent loop canvas"
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1.4} color="var(--grid)" />
        <MiniMap
          pannable
          zoomable
          position="bottom-right"
          nodeColor={(n) => colorFor(n.type ?? "flow")}
          nodeStrokeWidth={0}
          nodeBorderRadius={6}
          maskColor="transparent"
          className="!mb-4 !mr-4 hidden !h-[110px] !w-[170px] md:block"
          ariaLabel="Minimap"
        />
      </ReactFlow>

      <div className="glass absolute bottom-4 left-4 flex items-center gap-0.5 rounded-xl border border-line p-1 shadow-[var(--shadow-md)]">
        <IconButton label="Zoom out" onClick={() => void rf.zoomOut({ duration: 200 })}>
          <Minus size={16} />
        </IconButton>
        <IconButton label="Zoom in" onClick={() => void rf.zoomIn({ duration: 200 })}>
          <Plus size={16} />
        </IconButton>
        <IconButton label="Fit to screen" onClick={() => void rf.fitView({ padding: 0.12, duration: 300, maxZoom: 1 })}>
          <ArrowsOut size={16} />
        </IconButton>
        <span className="mx-0.5 h-5 w-px bg-line" />
        <IconButton label="Tidy up the layout" onClick={() => void tidy()}>
          <MagicWand size={16} />
        </IconButton>
      </div>

      {nodes.length === 0 && <EmptyCanvas />}
      <TraceTicker />
    </div>
  );
}

function EmptyCanvas() {
  const openDialog = useStore((s) => s.openDialog);
  return (
    <div className="pointer-events-none absolute inset-0 grid place-items-center">
      <div className="enter-up pointer-events-auto max-w-sm text-center">
        <p className="font-display text-[22px] font-semibold tracking-[-0.02em]">An empty bench</p>
        <p className="mt-2 text-muted">
          Drag a Chat input from the toolkit to begin, or start from a blueprint that already works.
        </p>
        <button
          type="button"
          onClick={() => openDialog("gallery", true)}
          className="mt-4 inline-flex h-9 cursor-pointer items-center rounded-[9px] bg-accent px-4 text-[13.5px] font-medium text-white transition-transform active:scale-[0.97]"
        >
          Browse blueprints
        </button>
      </div>
    </div>
  );
}
