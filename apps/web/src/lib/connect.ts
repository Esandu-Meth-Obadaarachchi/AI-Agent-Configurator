import type { Connection, Edge } from "@xyflow/react";

import { NODE_DEFS } from "./catalog";

/**
 * Mirror of the engine's edge rules, so invalid wires are refused while dragging
 * instead of showing up later as errors.
 */
export function connectionProblem(c: Connection | Edge, typeOf: (id: string) => string | undefined): string | null {
  if (!c.source || !c.target) return "Incomplete connection.";
  if (c.source === c.target) return "A block can't connect to itself. Use a Review loop to repeat work.";
  const src = NODE_DEFS[typeOf(c.source) ?? ""];
  const dst = NODE_DEFS[typeOf(c.target) ?? ""];
  if (!src || !dst) return "Unknown block.";
  const fromAttach = c.sourceHandle === "attach";
  if (fromAttach) {
    if (c.targetHandle === "tools") {
      if (dst.type !== "agent") return "Only agents take tools.";
      return null;
    }
    if (c.targetHandle === "knowledge") {
      return src.type === "knowledge" ? null : "Only a Knowledge base plugs into a Retrieve step.";
    }
    return "Drop resources on an agent's Tools socket.";
  }
  if (c.targetHandle !== "in") return "Connect flow outputs to a block's input on the left.";
  if (dst.type === "input") return "Nothing flows back into the Chat input.";
  if (dst.role === "resource") return "Resources plug into agents, not the other way round.";
  return null;
}
