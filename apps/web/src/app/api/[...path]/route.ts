import type { NextRequest } from "next/server";

/**
 * Forwards /api/* to the configurator engine (FastAPI) and streams the response back.
 * CONFIGURATOR_API_URL is read at request time, so the same build works locally and in Docker.
 */
export const dynamic = "force-dynamic";

const HOP_BY_HOP = new Set(["connection", "keep-alive", "transfer-encoding", "content-length", "host", "content-encoding"]);

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }): Promise<Response> {
  const { path } = await ctx.params;
  const backend = process.env.CONFIGURATOR_API_URL ?? "http://127.0.0.1:8787";
  const url = `${backend}/api/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });

  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: req.method,
      headers,
      body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
      cache: "no-store",
    });
  } catch {
    return Response.json({ detail: `Can't reach the API at ${backend}. Start it with \`make api\` in the repo root.` }, { status: 502 });
  }

  const out = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) out.set(key, value);
  });
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE };
