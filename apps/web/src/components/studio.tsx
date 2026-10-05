"use client";

import * as Tooltip from "@radix-ui/react-tooltip";
import { ReactFlowProvider } from "@xyflow/react";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import { CATALOG } from "@/lib/catalog";
import { useStore } from "@/lib/store";
import type { Spec } from "@/lib/types";

import { Canvas } from "./canvas";
import { CodeView } from "./code-view";
import { applyTheme, CommandPalette, exportProject, SettingsDialog, ShortcutsDialog, Toast } from "./dialogs";
import { Gallery } from "./gallery";
import { Inspector } from "./inspector";
import { SpecView } from "./spec-view";
import { Toolkit } from "./toolkit";
import { Topbar } from "./topbar";

const SAVE_KEY = "configurator.spec.v2";

function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return Boolean(el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable));
}

/** Load the last session, or a starter blueprint behind the gallery on a first visit. */
function useBootstrap() {
  const loaded = useRef(false);
  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    try {
      const theme = window.localStorage.getItem("configurator.theme");
      if (theme === "light" || theme === "dark") applyTheme(theme);
    } catch {
      /* ignore */
    }
    const state = useStore.getState();
    // Deep link: ?blueprint=<id> opens that blueprint directly.
    const linked = new URLSearchParams(window.location.search).get("blueprint");
    const fromLink = CATALOG.blueprints.find((b) => b.id === linked);
    if (fromLink) {
      state.loadSpec(fromLink.spec);
      return;
    }
    let saved: Spec | null = null;
    try {
      const raw = window.localStorage.getItem(SAVE_KEY);
      saved = raw ? (JSON.parse(raw) as Spec) : null;
    } catch {
      saved = null;
    }
    if (saved?.graph) {
      state.loadSpec(saved);
    } else {
      state.loadSpec(CATALOG.blueprints.find((b) => b.id === "support-bot")?.spec ?? CATALOG.blueprints[0].spec);
      state.openDialog("gallery", true);
    }
  }, []);
}

/** Save to this browser and re-check with the engine after every change. */
function useSync() {
  const revision = useStore((s) => s.revision);
  useEffect(() => {
    const ctrl = new AbortController();
    const save = setTimeout(() => {
      try {
        window.localStorage.setItem(SAVE_KEY, JSON.stringify(useStore.getState().spec()));
      } catch {
        /* storage full or blocked: editing still works */
      }
    }, 400);
    const check = setTimeout(async () => {
      const state = useStore.getState();
      try {
        const analysis = await api.validate(state.spec(), ctrl.signal);
        state.setAnalysis(analysis, true);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        if (err instanceof ApiError && err.status === 422) {
          state.setAnalysis(
            { ok: false, issues: [{ level: "error", code: "schema", message: err.message, node_id: null, fix: null }], modules: [], gaps: [], trace: [] },
            true,
          );
        } else {
          state.setAnalysis(state.analysis, false);
        }
      }
    }, 220);
    return () => {
      clearTimeout(save);
      clearTimeout(check);
      ctrl.abort();
    };
  }, [revision]);
}

function useShortcuts() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const s = useStore.getState();
      const mod = e.metaKey || e.ctrlKey;
      const key = e.key.toLowerCase();
      if (mod && key === "k") {
        e.preventDefault();
        s.openDialog("palette", !s.dialogs.palette);
        return;
      }
      if (isTyping(e.target) || Object.values(s.dialogs).some(Boolean)) return;
      if (mod && key === "z") {
        e.preventDefault();
        if (e.shiftKey) s.redo();
        else s.undo();
      } else if (mod && key === "y") {
        e.preventDefault();
        s.redo();
      } else if (mod && key === "d" && s.selectedId) {
        e.preventDefault();
        s.duplicateNode(s.selectedId);
      } else if (mod && key === "e") {
        e.preventDefault();
        void exportProject();
      } else if (!mod && !e.altKey) {
        if (key === "t") (s.trace.step >= 0 ? s.stopTrace : s.playTrace)();
        else if (key === "1") s.setView("canvas");
        else if (key === "2") s.setView("code");
        else if (key === "3") s.setView("spec");
        else if (key === "b") s.openDialog("gallery", true);
        else if (e.key === "?") s.openDialog("shortcuts", true);
        else if (key === "escape" && s.trace.step >= 0) s.stopTrace();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

export function Studio() {
  useBootstrap();
  useSync();
  useShortcuts();
  const view = useStore((s) => s.view);
  const [ai, setAi] = useState<{ available: boolean; model: string; sandbox: boolean } | null>(null);
  // On narrow screens the side panels are drawers, closed until asked for.
  const [panels, setPanels] = useState({ toolkit: false, inspector: false });

  const refreshAi = useCallback(() => {
    api
      .aiStatus()
      .then(setAi)
      .catch(() => setAi(null));
  }, []);
  useEffect(() => {
    refreshAi();
  }, [refreshAi]);

  const togglePanel = (p: "toolkit" | "inspector") => setPanels((v) => ({ ...v, [p]: !v[p] }));
  const aiAvailable = Boolean(ai?.available);

  return (
    <Tooltip.Provider delayDuration={350} skipDelayDuration={200}>
      <ReactFlowProvider>
        <a href="#canvas" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2">
          Skip to canvas
        </a>
        <div className="flex h-dvh flex-col">
          <Topbar aiAvailable={aiAvailable} panels={panels} togglePanel={togglePanel} />
          <div className="relative flex min-h-0 flex-1">
            <div
              className={`absolute inset-y-0 left-0 z-10 w-[252px] shrink-0 border-r border-line bg-canvas transition-transform duration-300 ease-[var(--ease-drawer)] lg:static lg:translate-x-0 ${
                panels.toolkit ? "translate-x-0 shadow-[var(--shadow-lg)] lg:shadow-none" : "-translate-x-full"
              }`}
            >
              <Toolkit />
            </div>
            <main id="canvas" className="relative min-w-0 flex-1">
              <div className={view === "canvas" ? "size-full" : "invisible absolute inset-0"} aria-hidden={view !== "canvas"}>
                <Canvas />
              </div>
              {view === "code" && (
                <div className="fade-in absolute inset-0">
                  <CodeView />
                </div>
              )}
              {view === "spec" && (
                <div className="fade-in absolute inset-0">
                  <SpecView />
                </div>
              )}
            </main>
            <div
              className={`absolute inset-y-0 right-0 z-10 w-[328px] shrink-0 border-l border-line bg-surface transition-transform duration-300 ease-[var(--ease-drawer)] xl:static xl:translate-x-0 ${
                panels.inspector ? "translate-x-0 shadow-[var(--shadow-lg)] xl:shadow-none" : "translate-x-full"
              }`}
            >
              <Inspector aiAvailable={aiAvailable} />
            </div>
          </div>
        </div>
        <Gallery aiAvailable={aiAvailable} />
        <SettingsDialog ai={ai} onKeyChange={refreshAi} />
        <ShortcutsDialog />
        <CommandPalette onExport={() => void exportProject()} />
        <Toast />
      </ReactFlowProvider>
    </Tooltip.Provider>
  );
}
