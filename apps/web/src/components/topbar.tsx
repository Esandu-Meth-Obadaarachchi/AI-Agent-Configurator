"use client";

import {
  ArrowArcLeft,
  ArrowArcRight,
  DownloadSimple,
  GearSix,
  Play,
  SidebarSimple,
  SquaresFour,
  Stop,
} from "@phosphor-icons/react";
import { useState } from "react";

import { api, ApiError, download } from "@/lib/api";
import { useStore } from "@/lib/store";

import { Button, Hint, IconButton, Kbd, Segmented } from "./ui";

export function Topbar({
  aiAvailable,
  panels,
  togglePanel,
}: {
  aiAvailable: boolean;
  panels: { toolkit: boolean; inspector: boolean };
  togglePanel: (p: "toolkit" | "inspector") => void;
}) {
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);
  const name = useStore((s) => s.project.project.name);
  const setProject = useStore((s) => s.setProject);
  const canUndo = useStore((s) => s.past.length > 0);
  const canRedo = useStore((s) => s.future.length > 0);
  const undo = useStore((s) => s.undo);
  const redo = useStore((s) => s.redo);
  const tracing = useStore((s) => s.trace.step >= 0);
  const hasTrace = useStore((s) => (s.analysis?.trace.length ?? 0) > 1);
  const playTrace = useStore((s) => s.playTrace);
  const stopTrace = useStore((s) => s.stopTrace);
  const openDialog = useStore((s) => s.openDialog);
  const errors = useStore((s) => s.analysis?.issues.filter((i) => i.level === "error").length ?? 0);
  const [editing, setEditing] = useState(false);
  const [exporting, setExporting] = useState(false);

  const exportZip = async () => {
    const state = useStore.getState();
    if (errors) {
      state.notify(`Fix ${errors} issue${errors === 1 ? "" : "s"} first. They're listed at the bottom of the inspector.`, "error");
      return;
    }
    setExporting(true);
    try {
      const blob = await api.exportZip(state.spec());
      download(blob, `${state.project.project.name}.zip`);
      state.notify("Project exported. Unzip it, then run: make setup && make dev", "success");
    } catch (err) {
      state.notify(err instanceof ApiError ? err.message : "Export failed.", "error");
    } finally {
      setExporting(false);
    }
  };

  return (
    <header className="glass relative z-20 flex h-[52px] shrink-0 items-center gap-2 border-b border-line px-2.5">
      <IconButton label={panels.toolkit ? "Hide toolkit" : "Show toolkit"} onClick={() => togglePanel("toolkit")} active={panels.toolkit} className="lg:hidden">
        <SidebarSimple size={18} />
      </IconButton>
      <div className="flex min-w-0 items-center gap-2 pl-1">
        <span aria-hidden className="grid size-7 shrink-0 place-items-center rounded-[8px] bg-ink text-canvas">
          <svg viewBox="0 0 32 32" className="size-5">
            <path d="M8 10h7v12H8zM17 10h7v5h-7zM17 17h7v5h-7z" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <path d="M15 16h2" stroke="var(--accent)" strokeWidth="2.4" />
          </svg>
        </span>
        <span className="hidden font-display text-[15px] font-semibold tracking-[-0.02em] sm:inline">configurator</span>
        <span className="hidden text-faint sm:inline">/</span>
        {editing ? (
          <input
            autoFocus
            defaultValue={name}
            aria-label="Project name"
            onBlur={(e) => {
              const v = e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/^-+|-+$/g, "");
              if (v && /^[a-z]/.test(v)) setProject("project.name", v.slice(0, 48));
              setEditing(false);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") (e.target as HTMLInputElement).blur();
              if (e.key === "Escape") setEditing(false);
            }}
            className="h-7 w-44 rounded-md border border-accent bg-surface px-1.5 font-mono text-[13px] outline-none"
          />
        ) : (
          <Hint label="Rename project">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="h-7 max-w-[180px] cursor-text truncate rounded-md px-1.5 font-mono text-[13px] text-ink-2 hover:bg-surface-2"
            >
              {name}
            </button>
          </Hint>
        )}
      </div>

      <div className="mx-auto hidden w-[260px] md:block">
        <Segmented
          label="View"
          size="sm"
          value={view}
          onChange={setView}
          options={[
            { value: "canvas", label: "Canvas" },
            { value: "code", label: "Code" },
            { value: "spec", label: "Spec" },
          ]}
        />
      </div>

      <div className="ml-auto flex items-center gap-1 md:ml-0">
        <IconButton label="Undo (⌘Z)" onClick={undo} disabled={!canUndo}>
          <ArrowArcLeft size={17} />
        </IconButton>
        <IconButton label="Redo (⇧⌘Z)" onClick={redo} disabled={!canRedo}>
          <ArrowArcRight size={17} />
        </IconButton>
        <span className="mx-1 hidden h-5 w-px bg-line sm:block" />
        <IconButton label="Blueprints" onClick={() => openDialog("gallery", true)}>
          <SquaresFour size={17} />
        </IconButton>
        <Hint label={aiAvailable ? "Settings · Claude connected" : "Settings · add an Anthropic key for AI features"}>
          <button
            type="button"
            aria-label="Settings"
            onClick={() => openDialog("settings", true)}
            className="relative grid size-9 cursor-pointer place-items-center rounded-[9px] text-muted transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <GearSix size={17} />
            <span className={`absolute top-2 right-2 size-1.5 rounded-full ${aiAvailable ? "bg-ok" : "bg-faint"}`} aria-hidden />
          </button>
        </Hint>
        <Hint
          label={
            <span>
              Dry-run the loop on the canvas <Kbd>T</Kbd>
            </span>
          }
        >
          <Button
            variant="secondary"
            size="sm"
            onClick={tracing ? stopTrace : playTrace}
            disabled={!hasTrace && !tracing}
            aria-pressed={tracing}
            className="ml-1"
          >
            {tracing ? <Stop size={14} weight="fill" className="text-accent" /> : <Play size={14} weight="fill" className="text-accent" />}
            <span className="hidden sm:inline">{tracing ? "Stop" : "Trace"}</span>
          </Button>
        </Hint>
        <Button variant="primary" size="sm" onClick={() => void exportZip()} disabled={exporting}>
          <DownloadSimple size={15} weight="bold" />
          <span className="hidden sm:inline">{exporting ? "Exporting…" : "Export"}</span>
        </Button>
        <IconButton label={panels.inspector ? "Hide inspector" : "Show inspector"} onClick={() => togglePanel("inspector")} active={panels.inspector} className="xl:hidden">
          <SidebarSimple size={18} className="-scale-x-100" />
        </IconButton>
      </div>
    </header>
  );
}
