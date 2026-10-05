"use client";

import { CaretRight, CheckCircle, Copy, Info, Trash, WarningCircle, XCircle } from "@phosphor-icons/react";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import { CATALOG, colorFor, NODE_DEFS } from "@/lib/catalog";
import { useStore } from "@/lib/store";
import type { FieldDef, Issue, NodeData } from "@/lib/types";

import { Field, FieldRow } from "./fields";
import { BlockIcon } from "./icons";
import { Button, Hint, inputClass } from "./ui";

// Stable fallback: a fresh [] inside a selector would re-render forever.
const NO_MODULES: string[] = [];

function visible(field: FieldDef, read: (key: string) => unknown): boolean {
  if (!field.showIf) return true;
  return Object.entries(field.showIf).every(([k, want]) => {
    const v = read(k);
    return Array.isArray(want) ? want.includes(String(v)) : String(v) === want;
  });
}

function getPath(obj: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], obj);
}

export function Inspector({ aiAvailable }: { aiAvailable: boolean }) {
  const selectedId = useStore((s) => s.selectedId);
  const node = useStore((s) => s.nodes.find((n) => n.id === s.selectedId));
  return (
    <aside aria-label="Inspector" className="flex h-full w-full flex-col">
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {node && selectedId ? <NodeInspector key={node.id} id={node.id} type={node.type ?? ""} data={node.data} aiAvailable={aiAvailable} /> : <ProjectInspector />}
      </div>
      <Checks />
    </aside>
  );
}

function Section({ title, children, defaultOpen = true }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="border-b border-line px-4 py-3">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center gap-1.5 text-left text-[11.5px] font-semibold tracking-[0.04em] text-muted uppercase"
      >
        <CaretRight size={11} weight="bold" className={`transition-transform duration-200 ${open ? "rotate-90" : ""}`} />
        {title}
      </button>
      {open && <div className="mt-3 space-y-3.5">{children}</div>}
    </section>
  );
}

function NodeInspector({ id, type, data, aiAvailable }: { id: string; type: string; data: NodeData; aiAvailable: boolean }) {
  const def = NODE_DEFS[type];
  const updateData = useStore((s) => s.updateData);
  const renameNode = useStore((s) => s.renameNode);
  const removeNode = useStore((s) => s.removeNode);
  const duplicateNode = useStore((s) => s.duplicateNode);
  const project = useStore((s) => s.project);
  const notify = useStore((s) => s.notify);
  const [idDraft, setIdDraft] = useState(id);
  const [idError, setIdError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [aiResult, setAiResult] = useState<string | null>(null);

  if (!def) return null;
  const color = colorFor(type);
  const basic = def.fields.filter((f) => !f.advanced);
  const advanced = def.fields.filter((f) => f.advanced);

  const setField = (key: string, value: unknown) => {
    if (key === "routes") {
      // Branch ids name the router's outputs: carry existing connections across a rename.
      const before = ((data.routes as { id: string }[]) ?? []).map((r) => r.id);
      const after = ((value as { id: string }[]) ?? []).map((r) => r.id);
      const remap = new Map(before.map((b, i) => [`route:${b}`, after[i] !== undefined ? `route:${after[i]}` : null]));
      useStore.setState((s) => ({
        edges: s.edges
          .map((e) => (e.source === id && remap.has(e.sourceHandle ?? "") ? { ...e, sourceHandle: remap.get(e.sourceHandle ?? "") ?? null } : e))
          .filter((e) => !(e.source === id && e.sourceHandle === null && type === "router")),
      }));
    }
    updateData(id, { [key]: value });
  };

  const runAi = async (kind: string) => {
    setBusy(true);
    setAiResult(null);
    try {
      if (kind === "system_prompt") {
        const state = useStore.getState();
        const toolNames = state.edges
          .filter((e) => e.target === id && e.sourceHandle === "attach")
          .map((e) => String(state.nodes.find((n) => n.id === e.source)?.data.label ?? e.source));
        const res = await api.writePrompt({
          kind: def.title,
          label: String(data.label ?? def.title),
          role: String(data.role ?? ""),
          context: state.project.project.description,
          tools: toolNames,
        });
        updateData(id, { system_prompt: res.prompt });
        setAiResult("Drafted by Claude. Edit it as you like.");
      } else {
        const res = await api.generateCode(useStore.getState().spec(), id);
        if (res.ok) updateData(id, res.data);
        setAiResult(
          res.ok
            ? `Written in ${res.attempts} attempt${res.attempts === 1 ? "" : "s"}; ${res.verified === "executed" ? "passed its contract test in a sandbox" : "passed static checks (start Docker to also run its test)"}. ${res.message}`
            : res.message,
        );
      }
    } catch (err) {
      notify(err instanceof ApiError ? err.message : "Claude couldn't help this time.", "error");
    } finally {
      setBusy(false);
    }
  };

  const aiFor = (f: FieldDef) =>
    f.ai
      ? {
          label: f.ai === "system_prompt" ? "Write with Claude" : data.code ? "Rewrite with Claude" : "Generate with Claude",
          busy,
          onRun: () => void runAi(f.ai!),
          disabled: aiAvailable ? undefined : "Add an Anthropic key in Settings",
        }
      : undefined;

  const render = (f: FieldDef) =>
    visible(f, (k) => data[k]) ? (
      <Field
        key={f.key}
        field={f}
        value={data[f.key]}
        onChange={(v) => setField(f.key, v)}
        provider={project.llm.provider}
        defaultModel={project.llm.model}
        aiAction={aiFor(f)}
      />
    ) : null;

  return (
    <div className="enter-up">
      <header className="flex items-start gap-3 border-b border-line px-4 pt-4 pb-3.5">
        <span className="grid size-9 shrink-0 place-items-center rounded-[10px]" style={{ background: `color-mix(in srgb, ${color} 13%, transparent)`, color }}>
          <BlockIcon name={def.icon} size={19} />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[15px] font-semibold tracking-[-0.01em]">{String(data.label || def.title)}</h2>
          <p className="text-[12.5px] leading-snug text-muted">{def.explain}</p>
        </div>
      </header>
      {def.tradeoff && (
        <p className="mx-4 mt-3 flex gap-2 rounded-[10px] bg-surface-2 px-3 py-2 text-[12px] leading-snug text-muted">
          <Info size={14} className="mt-0.5 shrink-0" aria-hidden />
          {def.tradeoff}
        </p>
      )}
      <Section title="Settings">{basic.map(render)}</Section>
      {aiResult && <p className="mx-4 mt-3 rounded-[10px] border border-line bg-accent-soft px-3 py-2 text-[12px] leading-snug text-accent-ink">{aiResult}</p>}
      <Section title="Advanced" defaultOpen={false}>
        {advanced.map(render)}
        <FieldRow label="Block id" help={idError ?? "Used in generated code and file names."}>
          <input
            value={idDraft}
            onChange={(e) => setIdDraft(e.target.value)}
            onBlur={() => {
              const err = renameNode(id, idDraft);
              setIdError(err);
              if (err) setIdDraft(id);
            }}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
            className={`${inputClass} h-9 font-mono text-[12.5px]`}
            spellCheck={false}
          />
        </FieldRow>
      </Section>
      <div className="flex gap-2 px-4 py-3">
        <Button size="sm" onClick={() => duplicateNode(id)}>
          <Copy size={14} /> Duplicate
        </Button>
        <Button size="sm" variant="danger" onClick={() => removeNode(id)}>
          <Trash size={14} /> Delete
        </Button>
      </div>
    </div>
  );
}

function ProjectInspector() {
  const project = useStore((s) => s.project);
  const setProject = useStore((s) => s.setProject);
  const modules = useStore((s) => s.analysis?.modules ?? NO_MODULES);
  const fields = CATALOG.project_fields;
  const groups: [string, string[]][] = [
    ["Project", ["project."]],
    ["Model", ["llm."]],
    ["Code and interface", ["backend.", "ui."]],
    ["Deployment", ["deploy.", "observability."]],
  ];
  const onChange = (key: string, value: unknown) => {
    if (key === "llm.provider" && value !== project.llm.provider) {
      setProject("llm", { ...project.llm, provider: value, model: CATALOG.default_model[value as string] });
      return;
    }
    setProject(key, value);
  };
  return (
    <div className="enter-up">
      <header className="border-b border-line px-4 pt-4 pb-3.5">
        <h2 className="text-[15px] font-semibold tracking-[-0.01em]">Project</h2>
        <p className="text-[12.5px] text-muted">Applies to every block. Select a block to edit it.</p>
      </header>
      {groups.map(([title, prefixes]) => (
        <Section key={title} title={title}>
          {fields
            .filter((f) => prefixes.some((p) => f.key.startsWith(p)))
            .filter((f) => visible(f, (k) => getPath(project, k)))
            .map((f) => (
              <Field
                key={f.key}
                field={f}
                value={getPath(project, f.key)}
                onChange={(v) => onChange(f.key, v)}
                provider={project.llm.provider}
                defaultModel={project.llm.model}
              />
            ))}
        </Section>
      ))}
      {modules.length > 0 && (
        <Section title={`In this build · ${modules.length} modules`} defaultOpen={false}>
          <ul className="flex flex-wrap gap-1.5">
            {modules.map((m) => (
              <li key={m} className="rounded-md border border-line bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-muted">
                {m}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}

const LEVEL_ICON = { error: XCircle, warning: WarningCircle, info: Info };
const LEVEL_TONE = { error: "text-error", warning: "text-warn", info: "text-muted" };

function Checks() {
  const analysis = useStore((s) => s.analysis);
  const online = useStore((s) => s.engineOnline);
  const selectedId = useStore((s) => s.selectedId);
  const select = useStore((s) => s.select);
  const [open, setOpen] = useState(false);
  if (!online) {
    return (
      <div className="border-t border-line bg-warn-soft px-4 py-3 text-[12.5px] leading-snug text-warn">
        The engine is offline. Editing still works; start it with <code className="font-mono">make api</code> for checks, preview and export.
      </div>
    );
  }
  if (!analysis) return null;
  const relevant: Issue[] = selectedId ? analysis.issues.filter((i) => i.node_id === selectedId) : analysis.issues;
  const errors = analysis.issues.filter((i) => i.level === "error").length;
  const warnings = analysis.issues.filter((i) => i.level === "warning").length;
  return (
    <div className="border-t border-line">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex h-11 w-full cursor-pointer items-center gap-2 px-4 text-left text-[12.5px] font-medium hover:bg-surface-2"
      >
        {errors ? (
          <XCircle size={16} weight="fill" className="text-error" />
        ) : warnings ? (
          <WarningCircle size={16} weight="fill" className="text-warn" />
        ) : (
          <CheckCircle size={16} weight="fill" className="text-ok" />
        )}
        {errors ? `${errors} to fix` : "Ready to export"}
        {warnings > 0 && <span className="text-muted">· {warnings} warning{warnings === 1 ? "" : "s"}</span>}
        <CaretRight size={12} className={`ml-auto text-faint transition-transform duration-200 ${open ? "-rotate-90" : "rotate-90"}`} />
      </button>
      {open && (
        <ul className="scroll-thin max-h-[34vh] space-y-1 overflow-y-auto px-2 pb-3">
          {relevant.length === 0 && <li className="px-2 py-1 text-[12.5px] text-muted">{selectedId ? "Nothing to flag on this block." : "No issues."}</li>}
          {relevant.map((i, k) => {
            const IconFor = LEVEL_ICON[i.level];
            return (
              <li key={`${i.code}-${k}`}>
                <Hint label={i.code} side="left">
                  <button
                    type="button"
                    onClick={() => i.node_id && select(i.node_id)}
                    className="flex w-full cursor-pointer items-start gap-2 rounded-lg px-2 py-1.5 text-left text-[12.5px] leading-snug hover:bg-surface-2"
                  >
                    <IconFor size={15} weight="fill" className={`mt-0.5 shrink-0 ${LEVEL_TONE[i.level]}`} />
                    <span>{i.message}</span>
                  </button>
                </Hint>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
