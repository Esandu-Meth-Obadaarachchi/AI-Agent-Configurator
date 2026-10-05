"use client";

import * as Tooltip from "@radix-ui/react-tooltip";
import { type ButtonHTMLAttributes, forwardRef, type ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-white hover:brightness-105 shadow-[0_1px_0_rgb(255_255_255/0.25)_inset,var(--shadow-sm)]",
  secondary: "bg-surface text-ink border border-line hover:border-line-strong shadow-[var(--shadow-sm)]",
  ghost: "text-muted hover:text-ink hover:bg-surface-2",
  danger: "text-error hover:bg-error-soft",
};

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" }>(
  function Button({ variant = "secondary", size = "md", className = "", ...props }, ref) {
    const sizing = size === "sm" ? "h-8 px-2.5 text-[13px] gap-1.5" : "h-9 px-3.5 text-[13.5px] gap-2";
    return (
      <button
        ref={ref}
        type="button"
        className={`inline-flex shrink-0 cursor-pointer items-center justify-center rounded-[9px] font-medium transition-[transform,background-color,border-color,color,filter] duration-150 active:scale-[0.97] disabled:pointer-events-none disabled:opacity-45 ${sizing} ${VARIANTS[variant]} ${className}`}
        {...props}
      />
    );
  },
);

export const IconButton = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { label: string; active?: boolean }>(
  function IconButton({ label, active, className = "", children, ...props }, ref) {
    return (
      <Hint label={label}>
        <button
          ref={ref}
          type="button"
          aria-label={label}
          aria-pressed={active}
          className={`grid size-9 shrink-0 cursor-pointer place-items-center rounded-[9px] transition-[transform,background-color,color] duration-150 active:scale-[0.94] disabled:pointer-events-none disabled:opacity-40 ${
            active ? "bg-accent-soft text-accent-ink" : "text-muted hover:bg-surface-2 hover:text-ink"
          } ${className}`}
          {...props}
        >
          {children}
        </button>
      </Hint>
    );
  },
);

export function Hint({ label, children, side = "bottom" }: { label: ReactNode; children: ReactNode; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <Tooltip.Root delayDuration={350}>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side={side}
          sideOffset={6}
          className="fade-in z-50 max-w-[280px] rounded-lg bg-ink px-2.5 py-1.5 text-[12px] leading-snug text-canvas shadow-[var(--shadow-md)]"
        >
          {label}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded-[5px] border border-line bg-surface-2 px-1 font-mono text-[11px] text-muted">
      {children}
    </kbd>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
  size = "md",
}: {
  value: T;
  options: { value: T; label: ReactNode; disabled?: boolean; hint?: string }[];
  onChange: (v: T) => void;
  label: string;
  size?: "sm" | "md";
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex w-full rounded-[10px] border border-line bg-surface-2 p-0.5">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={o.disabled}
            title={o.hint}
            onClick={() => onChange(o.value)}
            className={`flex-1 cursor-pointer truncate rounded-[8px] px-2 font-medium transition-[background-color,color,box-shadow] duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${
              size === "sm" ? "h-7 text-[12px]" : "h-8 text-[12.5px]"
            } ${active ? "bg-surface text-ink shadow-[var(--shadow-sm)]" : "text-muted hover:text-ink"}`}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative h-[22px] w-[38px] shrink-0 cursor-pointer rounded-full transition-colors duration-200 ${checked ? "bg-accent" : "bg-line-strong"}`}
    >
      <span
        className={`absolute top-[3px] left-[3px] size-4 rounded-full bg-white shadow-sm transition-transform duration-200 ease-[var(--ease-out)] ${checked ? "translate-x-4" : ""}`}
      />
    </button>
  );
}

export const inputClass =
  "w-full rounded-[9px] border border-line bg-surface px-2.5 text-[13.5px] text-ink placeholder:text-faint transition-[border-color,box-shadow] duration-150 hover:border-line-strong focus:border-accent focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--accent)_18%,transparent)] focus:outline-none";
