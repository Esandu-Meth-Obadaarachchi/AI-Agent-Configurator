# 0007: Pinned versions in one file

## Decision
Every version an export uses lives in `modules/versions.yaml`. Manifests list package
names only; the merger pins them. A nightly job renders with `CONFIGURATOR_UNPINNED=1`
to catch upstream breakage early.

## Notable pins (October 2026)
LangGraph 1.2.13, LangChain 1.4.3, langchain-anthropic 1.7.5, FastAPI 0.142.2,
Next.js 16.3.8, React 19.3.0, Tailwind 4.3.3.

ESLint stays on 9.39.5: ESLint 10 crashes inside eslint-plugin-react, which
eslint-config-next 16 depends on. TypeScript stays on 5.9.3 rather than 7.x until
Next.js supports the native compiler.
