"use client";

import { Plus, Sparkle, Trash, X } from "@phosphor-icons/react";
import { type KeyboardEvent, type ReactNode, useId, useState } from "react";

import { CATALOG } from "@/lib/catalog";
import type { FieldDef } from "@/lib/types";

import { Button, inputClass, Segmented, Toggle } from "./ui";

export interface FieldProps {
  field: FieldDef;
  value: unknown;
  onChange: (value: unknown) => void;
  provider: string;
  defaultModel: string;
  aiAction?: { label: string; busy: boolean; onRun: () => void; disabled?: string };
}

export function FieldRow({ label, help, htmlFor, children, inline }: { label: string; help?: string; htmlFor?: string; children: ReactNode; inline?: boolean }) {
  if (inline) {
    return (
      <div className="flex items-center justify-between gap-3 py-1">
        <div className="min-w-0">
          <label htmlFor={htmlFor} className="text-[12.5px] font-medium text-ink-2">
            {label}
          </label>
          {help && <p className="text-[11.5px] leading-snug text-muted">{help}</p>}
        </div>
        {children}
      </div>
    );
  }
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-[12.5px] font-medium text-ink-2">
        {label}
      </label>
      {children}
      {help && <p className="text-[11.5px] leading-snug text-muted">{help}</p>}
    </div>
  );
}

export function Field({ field, value, onChange, provider, defaultModel, aiAction }: FieldProps) {
  const id = useId();
  const mono = field.mono ? "font-mono text-[12.5px]" : "";
  switch (field.kind) {
    case "text":
      return (
        <FieldRow label={field.label} help={field.help} htmlFor={id}>
          <input
            id={id}
            value={value == null ? "" : String(value)}
            placeholder={field.placeholder}
            onChange={(e) => onChange(field.nullable && e.target.value === "" ? null : e.target.value)}
            className={`${inputClass} h-9 ${mono}`}
            spellCheck={!field.mono}
          />
        </FieldRow>
      );
    case "textarea":
    case "prompt":
      return (
        <FieldRow label={field.label} help={field.help} htmlFor={id}>
          <textarea
            id={id}
            value={value == null ? "" : String(value)}
            rows={field.rows ?? 3}
            onChange={(e) => onChange(e.target.value)}
            className={`${inputClass} scroll-thin resize-y py-2 leading-relaxed`}
          />
          {aiAction && <AiButton {...aiAction} />}
        </FieldRow>
      );
    case "code":
      return (
        <FieldRow label={field.label} help={field.help} htmlFor={id}>
          {aiAction && <AiButton {...aiAction} />}
          <textarea
            id={id}
            value={value == null ? "" : String(value)}
            rows={12}
            placeholder={"# Leave empty to export a typed stub,\n# or let Claude write it from the description."}
            onChange={(e) => onChange(e.target.value || null)}
            spellCheck={false}
            className={`${inputClass} scroll-thin resize-y bg-surface-2 py-2 font-mono text-[12px] leading-[1.55]`}
          />
        </FieldRow>
      );
    case "number":
      return (
        <FieldRow label={field.label} help={field.help} htmlFor={id} inline>
          <input
            id={id}
            type="number"
            inputMode="decimal"
            value={value == null ? "" : String(value)}
            min={field.min}
            max={field.max}
            step={field.step ?? 1}
            placeholder={field.nullable ? "Default" : undefined}
            onChange={(e) => {
              const raw = e.target.value;
              if (raw === "") return onChange(field.nullable ? null : field.min ?? 0);
              const n = Number(raw);
              if (!Number.isNaN(n)) onChange(n);
            }}
            className={`${inputClass} h-8 w-[96px] text-right font-mono tabular-nums`}
          />
        </FieldRow>
      );
    case "toggle":
      return (
        <FieldRow label={field.label} help={field.help} inline>
          <Toggle checked={Boolean(value)} onChange={onChange} label={field.label} />
        </FieldRow>
      );
    case "segmented":
      return (
        <FieldRow label={field.label} help={field.help}>
          <Segmented
            label={field.label}
            value={value == null ? "" : String(value)}
            options={(field.options ?? []).map((o) => ({ ...o }))}
            onChange={(v) => onChange(field.nullable && v === "" ? null : v)}
          />
        </FieldRow>
      );
    case "select":
      return (
        <FieldRow label={field.label} help={(field.options ?? []).find((o) => o.value === value)?.hint ?? field.help} htmlFor={id}>
          <select id={id} value={String(value ?? "")} onChange={(e) => onChange(e.target.value)} className={`${inputClass} h-9 cursor-pointer`}>
            {(field.options ?? []).map((o) => (
              <option key={o.value} value={o.value} disabled={o.disabled}>
                {o.label}
              </option>
            ))}
          </select>
        </FieldRow>
      );
    case "multiselect": {
      const list = Array.isArray(value) ? (value as string[]) : [];
      return (
        <FieldRow label={field.label} help={field.help}>
          <div className="flex flex-wrap gap-1.5">
            {(field.options ?? []).map((o) => {
              const on = list.includes(o.value);
              return (
                <button
                  key={o.value}
                  type="button"
                  aria-pressed={on}
                  onClick={() => onChange(on ? list.filter((v) => v !== o.value) : [...list, o.value])}
                  className={`h-7 cursor-pointer rounded-full border px-2.5 text-[12px] font-medium transition-colors ${
                    on ? "border-accent bg-accent-soft text-accent-ink" : "border-line text-muted hover:border-line-strong hover:text-ink"
                  }`}
                >
                  {o.label}
                </button>
              );
            })}
          </div>
        </FieldRow>
      );
    }
    case "tags":
      return <TagsField field={field} value={Array.isArray(value) ? (value as string[]) : []} onChange={onChange} />;
    case "model":
      return <ModelField field={field} value={value as string | null} onChange={onChange} provider={provider} defaultModel={defaultModel} />;
    case "routes":
      return (
        <ListField
          label={field.label}
          help="Each branch is an output on the block. Connect each one to a step."
          value={value as Record<string, unknown>[]}
          onChange={onChange}
          make={(i) => ({ id: `branch_${i + 1}`, label: `Branch ${i + 1}`, description: "", keywords: [] })}
          columns={[
            { key: "label", label: "Name" },
            { key: "description", label: "When to take it", wide: true },
            { key: "keywords", label: "Keywords (comma separated)", wide: true, list: true },
          ]}
          idKey="id"
          min={1}
        />
      );
    case "params":
      return (
        <ListField
          label={field.label}
          value={value as Record<string, unknown>[]}
          onChange={onChange}
          make={(i) => ({ name: `param_${i + 1}`, description: "", location: "query" })}
          columns={[
            { key: "name", label: "Name", mono: true },
            { key: "location", label: "Sent as", options: ["query", "path", "body"] },
            { key: "description", label: "Description", wide: true },
          ]}
        />
      );
    case "toolinputs":
      return (
        <ListField
          label={field.label}
          help="The model fills these in when it calls the tool."
          value={value as Record<string, unknown>[]}
          onChange={onChange}
          make={(i) => ({ name: `input_${i + 1}`, type: "str", description: "" })}
          columns={[
            { key: "name", label: "Name", mono: true },
            { key: "type", label: "Type", options: ["str", "int", "float", "bool"] },
            { key: "description", label: "Description", wide: true },
          ]}
        />
      );
    default:
      return null;
  }
}

function AiButton({ label, busy, onRun, disabled }: { label: string; busy: boolean; onRun: () => void; disabled?: string }) {
  return (
    <div className="flex items-center gap-2">
      <Button size="sm" variant="secondary" onClick={onRun} disabled={busy || Boolean(disabled)} title={disabled}>
        <Sparkle size={14} weight="fill" className={busy ? "animate-pulse text-accent" : "text-accent"} />
        {busy ? "Working…" : label}
      </Button>
      {disabled && <span className="text-[11.5px] text-muted">{disabled}</span>}
    </div>
  );
}

function TagsField({ field, value, onChange }: { field: FieldDef; value: string[]; onChange: (v: unknown) => void }) {
  const [draft, setDraft] = useState("");
  const id = useId();
  const commit = () => {
    const parts = draft
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean);
    if (parts.length) onChange([...value, ...parts.filter((p) => !value.includes(p))]);
    setDraft("");
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit();
    } else if (e.key === "Backspace" && !draft && value.length) {
      onChange(value.slice(0, -1));
    }
  };
  return (
    <FieldRow label={field.label} help={field.help ?? "Press Enter to add."} htmlFor={id}>
      <div className={`${inputClass} flex min-h-9 flex-wrap items-center gap-1 py-1`}>
        {value.map((t) => (
          <span key={t} className={`inline-flex items-center gap-1 rounded-md bg-surface-2 py-0.5 pr-1 pl-1.5 text-[12px] ${field.mono ? "font-mono" : ""}`}>
            {t}
            <button type="button" aria-label={`Remove ${t}`} onClick={() => onChange(value.filter((v) => v !== t))} className="cursor-pointer rounded text-faint hover:text-ink">
              <X size={11} weight="bold" />
            </button>
          </span>
        ))}
        <input
          id={id}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          onBlur={commit}
          className={`min-w-[80px] flex-1 bg-transparent py-1 outline-none ${field.mono ? "font-mono text-[12.5px]" : ""}`}
        />
      </div>
    </FieldRow>
  );
}

function ModelField({
  field,
  value,
  onChange,
  provider,
  defaultModel,
}: {
  field: FieldDef;
  value: string | null;
  onChange: (v: unknown) => void;
  provider: string;
  defaultModel: string;
}) {
  const id = useId();
  const listId = useId();
  const isProject = field.key === "llm.model";
  const models = [...(CATALOG.models.anthropic ?? []), ...(CATALOG.models.openai ?? [])].filter((m) =>
    isProject ? (provider === "anthropic" ? m.value.startsWith("claude-") : !m.value.startsWith("claude-")) : true,
  );
  const hint = models.find((m) => m.value === (value || defaultModel))?.hint;
  return (
    <FieldRow label={field.label} help={hint ?? field.help} htmlFor={id}>
      <input
        id={id}
        list={listId}
        value={value ?? ""}
        placeholder={isProject ? undefined : `Project default (${defaultModel})`}
        onChange={(e) => onChange(e.target.value || (isProject ? defaultModel : null))}
        className={`${inputClass} h-9 font-mono text-[12.5px]`}
        spellCheck={false}
      />
      <datalist id={listId}>
        {models.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </datalist>
    </FieldRow>
  );
}

interface Column {
  key: string;
  label: string;
  wide?: boolean;
  mono?: boolean;
  list?: boolean;
  options?: string[];
}

function ListField({
  label,
  help,
  value,
  onChange,
  make,
  columns,
  idKey,
  min = 0,
}: {
  label: string;
  help?: string;
  value: Record<string, unknown>[] | undefined;
  onChange: (v: unknown) => void;
  make: (index: number) => Record<string, unknown>;
  columns: Column[];
  idKey?: string;
  min?: number;
}) {
  const rows = value ?? [];
  const update = (i: number, key: string, v: unknown) => {
    const next = rows.map((r, k) => {
      if (k !== i) return r;
      const row = { ...r, [key]: v };
      // Keep a router branch id in step with its name, so handles stay readable.
      if (idKey && key === "label" && typeof v === "string") {
        const slug = v.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
        const candidate = /^[a-z]/.test(slug) ? slug.slice(0, 40) : `b_${slug}`.slice(0, 40);
        if (candidate && !rows.some((o, j) => j !== i && o[idKey] === candidate)) row[idKey] = candidate;
      }
      return row;
    });
    onChange(next);
  };
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-[12.5px] font-medium text-ink-2">{label}</span>
        <Button size="sm" variant="ghost" onClick={() => onChange([...rows, make(rows.length)])}>
          <Plus size={13} /> Add
        </Button>
      </div>
      {help && <p className="text-[11.5px] leading-snug text-muted">{help}</p>}
      <ol className="space-y-2">
        {rows.map((row, i) => (
          <li key={i} className="space-y-1.5 rounded-[10px] border border-line bg-surface-2 p-2">
            <div className="flex items-center gap-1.5">
              {columns
                .filter((c) => !c.wide)
                .map((c) =>
                  c.options ? (
                    <select
                      key={c.key}
                      aria-label={c.label}
                      value={String(row[c.key] ?? "")}
                      onChange={(e) => update(i, c.key, e.target.value)}
                      className={`${inputClass} h-8 w-auto cursor-pointer`}
                    >
                      {c.options.map((o) => (
                        <option key={o}>{o}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      key={c.key}
                      aria-label={c.label}
                      placeholder={c.label}
                      value={String(row[c.key] ?? "")}
                      onChange={(e) => update(i, c.key, e.target.value)}
                      className={`${inputClass} h-8 min-w-0 flex-1 ${c.mono ? "font-mono text-[12.5px]" : ""}`}
                    />
                  ),
                )}
              <button
                type="button"
                aria-label="Remove row"
                disabled={rows.length <= min}
                onClick={() => onChange(rows.filter((_, k) => k !== i))}
                className="grid size-8 shrink-0 cursor-pointer place-items-center rounded-lg text-faint hover:bg-error-soft hover:text-error disabled:opacity-30"
              >
                <Trash size={14} />
              </button>
            </div>
            {columns
              .filter((c) => c.wide)
              .map((c) => (
                <input
                  key={c.key}
                  aria-label={c.label}
                  placeholder={c.label}
                  value={c.list ? ((row[c.key] as string[]) ?? []).join(", ") : String(row[c.key] ?? "")}
                  onChange={(e) =>
                    update(
                      i,
                      c.key,
                      c.list
                        ? e.target.value
                            .split(",")
                            .map((x) => x.trimStart())
                            .filter((x, k, all) => x || k === all.length - 1)
                        : e.target.value,
                    )
                  }
                  className={`${inputClass} h-8`}
                />
              ))}
            {idKey && <p className="font-mono text-[10.5px] text-faint">id: {String(row[idKey])}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}
