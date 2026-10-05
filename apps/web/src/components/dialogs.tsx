"use client";

import { Desktop, Moon, Sun, X } from "@phosphor-icons/react";
import * as Dialog from "@radix-ui/react-dialog";
import { Command } from "cmdk";
import { type ReactNode, useEffect, useState } from "react";

import { api, sessionKey, setSessionKey } from "@/lib/api";
import { CATALOG, colorFor } from "@/lib/catalog";
import { useStore } from "@/lib/store";

import { BlockIcon } from "./icons";
import { Button, inputClass, Kbd, Segmented } from "./ui";

function Sheet({ name, title, description, children, width = 480 }: { name: "settings" | "shortcuts"; title: string; description: string; children: ReactNode; width?: number }) {
  const open = useStore((s) => s.dialogs[name]);
  const openDialog = useStore((s) => s.openDialog);
  return (
    <Dialog.Root open={open} onOpenChange={(v) => openDialog(name, v)}>
      <Dialog.Portal>
        <Dialog.Overlay className="fade-in fixed inset-0 z-40 bg-[rgb(8_12_18/0.4)]" />
        <Dialog.Content
          style={{ width: `min(${width}px, calc(100vw - 32px))` }}
          className="enter-up fixed top-1/2 left-1/2 z-50 max-h-[calc(100dvh-32px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-[18px] border border-line bg-surface p-5 shadow-[var(--shadow-lg)] focus:outline-none"
        >
          <div className="flex items-start gap-3">
            <div>
              <Dialog.Title className="text-[16px] font-semibold tracking-[-0.01em]">{title}</Dialog.Title>
              <Dialog.Description className="mt-0.5 text-[13px] text-muted">{description}</Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button type="button" aria-label="Close" className="ml-auto grid size-8 cursor-pointer place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-ink">
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>
          <div className="mt-4">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

type Theme = "system" | "light" | "dark";

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", theme);
  try {
    window.localStorage.setItem("configurator.theme", theme);
  } catch {
    /* ignore */
  }
}

export function SettingsDialog({ onKeyChange, ai }: { onKeyChange: () => void; ai: { available: boolean; model: string; sandbox: boolean } | null }) {
  const open = useStore((s) => s.dialogs.settings);
  const online = useStore((s) => s.engineOnline);
  const [key, setKey] = useState("");
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    if (!open) return;
    const stored = sessionKey();
    let saved: Theme = "system";
    try {
      saved = (window.localStorage.getItem("configurator.theme") as Theme) || "system";
    } catch {
      /* ignore */
    }
    // Sync the form with storage each time the dialog opens.
    queueMicrotask(() => {
      setKey(stored ?? "");
      setTheme(saved);
    });
  }, [open]);

  return (
    <Sheet name="settings" title="Settings" description="Keys stay in this browser tab only and are never saved on the server.">
      <div className="space-y-5">
        <div className="space-y-1.5">
          <label htmlFor="anthropic-key" className="text-[12.5px] font-medium text-ink-2">
            Anthropic API key
          </label>
          <div className="flex gap-2">
            <input
              id="anthropic-key"
              type="password"
              autoComplete="off"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="sk-ant-…"
              className={`${inputClass} h-9 font-mono text-[12.5px]`}
            />
            <Button
              variant="primary"
              onClick={() => {
                setSessionKey(key.trim() || null);
                onKeyChange();
              }}
            >
              Save
            </Button>
          </div>
          <p className="text-[12px] leading-snug text-muted">
            Used for the only AI features: drafting a graph from a description, writing custom tools and steps, and drafting prompts. Code generation from
            templates never needs a key. If the engine has ANTHROPIC_API_KEY set, you can leave this empty.
          </p>
        </div>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 rounded-[12px] bg-surface-2 p-3 text-[12.5px]">
          <dt className="text-muted">Engine</dt>
          <dd className={online ? "text-ok" : "text-error"}>{online ? "Connected" : "Offline (run make api)"}</dd>
          <dt className="text-muted">Claude</dt>
          <dd>{ai?.available ? <span className="text-ok">Ready · {ai.model}</span> : <span className="text-muted">No key yet</span>}</dd>
          <dt className="text-muted">Code sandbox</dt>
          <dd className="text-muted">{ai?.sandbox ? "Docker: generated code runs its contract test in a container" : "Docker not running: static checks only"}</dd>
        </dl>
        <div className="space-y-1.5">
          <span className="text-[12.5px] font-medium text-ink-2">Appearance</span>
          <Segmented<Theme>
            label="Theme"
            value={theme}
            onChange={(t) => {
              setTheme(t);
              applyTheme(t);
            }}
            options={[
              { value: "system", label: <span className="inline-flex items-center gap-1.5"><Desktop size={13} /> System</span> },
              { value: "light", label: <span className="inline-flex items-center gap-1.5"><Sun size={13} /> Light</span> },
              { value: "dark", label: <span className="inline-flex items-center gap-1.5"><Moon size={13} /> Dark</span> },
            ]}
          />
        </div>
      </div>
    </Sheet>
  );
}

const SHORTCUTS: [string, string[]][] = [
  ["Command palette", ["⌘", "K"]],
  ["Undo / redo", ["⌘", "Z", "/", "⇧", "⌘", "Z"]],
  ["Delete selected", ["⌫"]],
  ["Duplicate block", ["⌘", "D"]],
  ["Trace the loop", ["T"]],
  ["Canvas / Code / Spec", ["1", "2", "3"]],
  ["Export project", ["⌘", "E"]],
  ["Blueprints", ["B"]],
  ["Multi-select", ["⇧", "click"]],
  ["This list", ["?"]],
];

export function ShortcutsDialog() {
  return (
    <Sheet name="shortcuts" title="Keyboard shortcuts" description="Everything on the canvas also works with the mouse." width={420}>
      <ul className="divide-y divide-line">
        {SHORTCUTS.map(([label, keys]) => (
          <li key={label} className="flex items-center justify-between py-2">
            <span className="text-[13px]">{label}</span>
            <span className="flex items-center gap-1">
              {keys.map((k, i) => (k === "/" ? <span key={i} className="px-0.5 text-faint">/</span> : <Kbd key={i}>{k}</Kbd>))}
            </span>
          </li>
        ))}
      </ul>
    </Sheet>
  );
}

export function CommandPalette({ onExport }: { onExport: () => void }) {
  const open = useStore((s) => s.dialogs.palette);
  const openDialog = useStore((s) => s.openDialog);
  const addNode = useStore((s) => s.addNode);
  const setView = useStore((s) => s.setView);
  const playTrace = useStore((s) => s.playTrace);
  const close = () => openDialog("palette", false);
  const run = (fn: () => void) => () => {
    close();
    fn();
  };
  const item = "flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] data-[selected=true]:bg-surface-2";

  return (
    <Dialog.Root open={open} onOpenChange={(v) => openDialog("palette", v)}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-[rgb(8_12_18/0.3)]" />
        <Dialog.Content className="fixed top-[16vh] left-1/2 z-50 w-[min(560px,calc(100vw-32px))] -translate-x-1/2 overflow-hidden rounded-[16px] border border-line bg-surface shadow-[var(--shadow-lg)] focus:outline-none">
          <Dialog.Title className="sr-only">Command palette</Dialog.Title>
          <Dialog.Description className="sr-only">Add blocks and run actions</Dialog.Description>
          <Command label="Command palette" loop>
            <Command.Input autoFocus placeholder="Add a block or run an action…" className="h-12 w-full border-b border-line bg-transparent px-4 text-[14px] outline-none placeholder:text-faint" />
            <Command.List className="scroll-thin max-h-[52vh] overflow-y-auto p-1.5">
              <Command.Empty className="px-3 py-6 text-center text-muted">No matches.</Command.Empty>
              <Command.Group heading="Actions" className="px-1 text-[11px] font-semibold text-faint [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
                <Command.Item className={item} onSelect={run(playTrace)}>Trace the loop</Command.Item>
                <Command.Item className={item} onSelect={run(onExport)}>Export project (.zip)</Command.Item>
                <Command.Item className={item} onSelect={run(() => openDialog("gallery", true))}>Open blueprints</Command.Item>
                <Command.Item className={item} onSelect={run(() => setView("canvas"))}>Show canvas</Command.Item>
                <Command.Item className={item} onSelect={run(() => setView("code"))}>Show generated code</Command.Item>
                <Command.Item className={item} onSelect={run(() => setView("spec"))}>Show spec.json</Command.Item>
                <Command.Item className={item} onSelect={run(() => openDialog("settings", true))}>Settings and API key</Command.Item>
              </Command.Group>
              <Command.Group heading="Add a block" className="px-1 text-[11px] font-semibold text-faint [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5">
                {CATALOG.nodes.map((n) => (
                  <Command.Item
                    key={n.type}
                    value={`${n.title} ${n.blurb}`}
                    className={item}
                    onSelect={run(() => {
                      const s = useStore.getState();
                      const sel = s.nodes.find((x) => x.id === s.selectedId);
                      const attach = n.role === "resource" && sel && (sel.type === "agent" || (n.type === "knowledge" && sel.type === "retriever")) ? sel.id : undefined;
                      addNode(n.type, sel ? { x: sel.position.x + (attach ? 0 : 300), y: sel.position.y + (attach ? 220 : 0) } : undefined, attach);
                    })}
                  >
                    <span className="grid size-6 place-items-center rounded-md" style={{ color: colorFor(n.type), background: `color-mix(in srgb, ${colorFor(n.type)} 12%, transparent)` }}>
                      <BlockIcon name={n.icon} size={14} />
                    </span>
                    <span className="font-medium text-ink">{n.title}</span>
                    <span className="truncate text-muted">{n.blurb}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function Toast() {
  const toast = useStore((s) => s.toast);
  if (!toast) return null;
  const tone = toast.tone === "error" ? "border-error/40 text-error" : toast.tone === "success" ? "border-ok/40 text-ink" : "border-line text-ink";
  return (
    <div
      key={toast.id}
      role={toast.tone === "error" ? "alert" : "status"}
      className={`glass enter-up fixed bottom-5 left-1/2 z-50 max-w-[min(560px,calc(100vw-32px))] -translate-x-1/2 rounded-xl border px-4 py-2.5 text-[13px] shadow-[var(--shadow-lg)] ${tone}`}
    >
      {toast.text}
    </div>
  );
}

export async function exportProject(): Promise<void> {
  const state = useStore.getState();
  const errors = state.analysis?.issues.filter((i) => i.level === "error").length ?? 0;
  if (errors) {
    state.notify(`Fix ${errors} issue${errors === 1 ? "" : "s"} first. They're listed at the bottom of the inspector.`, "error");
    return;
  }
  try {
    const blob = await api.exportZip(state.spec());
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.project.project.name}.zip`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    state.notify("Project exported. Unzip it, then run: make setup && make dev", "success");
  } catch (err) {
    state.notify((err as Error).message, "error");
  }
}
