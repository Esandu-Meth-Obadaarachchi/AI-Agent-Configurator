# 0005: Canvas stack

The brief asks to explain dependencies before adding them; these were added overnight,
so here is the reasoning to review.

| Package | Why | Alternative considered |
| --- | --- | --- |
| Next.js 16 + React 19 | Same stack as the generated UI; route handlers give a runtime proxy to the engine | Vite SPA: lighter, but two different frontends to maintain |
| @xyflow/react 12 (React Flow) | Mature node editor: handles, connection validation, minimap, viewport, accessibility | Hand-rolled SVG editor: weeks of work for less |
| zustand 5 | Small store that React Flow's own docs recommend; easy undo snapshots | React context: re-renders the whole canvas on every change |
| @radix-ui/react-dialog, react-tooltip | Accessible dialogs and tooltips (focus trap, escape, aria) | Hand-rolled: easy to get focus management wrong |
| cmdk | Accessible command palette with fuzzy search | Radix + custom filtering |
| highlight.js (core + 10 languages) | Small, synchronous highlighting for the Code view | Shiki: prettier, but WASM and async |
| @phosphor-icons/react | One consistent icon family with duotone weights | Lucide |
| Tailwind CSS 4 | Tokens as CSS variables, light/dark from one set | CSS modules |

Fonts: Geist (UI), Geist Mono (ids and code), Bricolage Grotesque (wordmark and
headings only), loaded with `next/font`.
