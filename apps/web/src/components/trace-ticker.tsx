"use client";

import { Pause, Play, SkipBack, SkipForward, X } from "@phosphor-icons/react";
import { useEffect } from "react";

import { useStore } from "@/lib/store";
import type { TraceStep } from "@/lib/types";

import { IconButton } from "./ui";

const STEP_MS = 1100;
const NO_STEPS: TraceStep[] = [];

/** Narrates the dry run while pulses travel along the cables. */
export function TraceTicker() {
  const trace = useStore((s) => s.trace);
  const steps = useStore((s) => s.analysis?.trace ?? NO_STEPS);
  const stepTrace = useStore((s) => s.stepTrace);
  const stopTrace = useStore((s) => s.stopTrace);
  const labels = useStore((s) => s.nodes);

  useEffect(() => {
    if (!trace.playing || trace.step < 0) return;
    const t = setTimeout(() => {
      if (trace.step + 1 < steps.length) stepTrace(trace.step + 1);
      else useStore.setState({ trace: { playing: false, step: trace.step } });
    }, STEP_MS);
    return () => clearTimeout(t);
  }, [trace, steps.length, stepTrace]);

  if (trace.step < 0 || !steps.length) return null;
  const step = steps[Math.min(trace.step, steps.length - 1)];
  const names = step.nodes.map((id) => String(labels.find((n) => n.id === id)?.data.label ?? id)).join(" + ");

  return (
    <div
      role="status"
      aria-live="polite"
      className="glass enter-up absolute top-4 left-1/2 flex w-[min(560px,calc(100%-32px))] -translate-x-1/2 items-center gap-3 rounded-2xl border border-line py-2 pr-2 pl-4 shadow-[var(--shadow-lg)]"
    >
      <span className="font-mono text-[11px] tabular-nums text-faint">
        {String(trace.step + 1).padStart(2, "0")}/{String(steps.length).padStart(2, "0")}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-semibold">{names}</p>
        <p className="truncate text-[12px] text-muted">{step.note || "Runs"}</p>
      </div>
      <div className="flex items-center">
        <IconButton label="Previous step" disabled={trace.step === 0} onClick={() => useStore.setState({ trace: { playing: false, step: trace.step - 1 } })}>
          <SkipBack size={15} />
        </IconButton>
        <IconButton
          label={trace.playing ? "Pause" : "Play"}
          onClick={() =>
            useStore.setState({
              trace: { playing: !trace.playing, step: trace.step + 1 >= steps.length && !trace.playing ? 0 : trace.step },
            })
          }
        >
          {trace.playing ? <Pause size={15} weight="fill" /> : <Play size={15} weight="fill" />}
        </IconButton>
        <IconButton
          label="Next step"
          disabled={trace.step >= steps.length - 1}
          onClick={() => useStore.setState({ trace: { playing: false, step: trace.step + 1 } })}
        >
          <SkipForward size={15} />
        </IconButton>
        <IconButton label="Close trace" onClick={stopTrace}>
          <X size={15} />
        </IconButton>
      </div>
    </div>
  );
}
