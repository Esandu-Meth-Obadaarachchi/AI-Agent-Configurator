"use client";

import { ArrowCounterClockwise, WarningCircle } from "@phosphor-icons/react";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { getInfo, getThread, readEvents, resumeTurn, sendFeedback, startTurn } from "@/lib/api";
import { turnsFromHistory, turnsReducer } from "@/lib/turns";
import type { AppInfo, Pending } from "@/lib/types";

import { Activity } from "./activity";
import { ApprovalCard } from "./approval-card";
import { Composer } from "./composer";
import { Reply } from "./reply";

const THREAD_KEY = "chat-thread-id";

function newThreadId(): string {
  return crypto.randomUUID().replaceAll("-", "");
}

export function Chat() {
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [offline, setOffline] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string>("");
  const [turns, dispatch] = useReducer(turnsReducer, []);
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const appInfo = await getInfo();
        if (cancelled) return;
        setInfo(appInfo);
        let id = window.localStorage.getItem(THREAD_KEY);
        if (!id) {
          id = newThreadId();
          window.localStorage.setItem(THREAD_KEY, id);
        }
        setThreadId(id);
        const history = await getThread(id);
        if (cancelled) return;
        dispatch({ type: "reset", turns: turnsFromHistory(history.messages) });
        setPending(history.pending[0] ?? null);
      } catch (err) {
        if (!cancelled) setOffline(err instanceof Error ? err.message : "The API is not reachable.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns, pending]);

  const run = useCallback(async (turnId: string, request: Promise<Response>) => {
    setBusy(true);
    try {
      await readEvents(await request, (e) => {
        if (e.event === "interrupt") setPending(e.data);
        dispatch({ type: "event", turnId, e });
      });
    } catch (err) {
      dispatch({ type: "fail", turnId, message: err instanceof Error ? err.message : "Something went wrong." });
    } finally {
      setBusy(false);
    }
  }, []);

  const send = useCallback(
    (text: string) => {
      const turnId = crypto.randomUUID();
      setPending(null);
      dispatch({ type: "start", turnId, text });
      void run(turnId, startTurn(text, threadId));
    },
    [run, threadId],
  );

  const decide = useCallback(
    (decision: { approved: boolean; edited?: string; feedback?: string }) => {
      const turnId = turns[turns.length - 1]?.id;
      if (!turnId) return;
      setPending(null);
      dispatch({ type: "resume", turnId });
      void run(turnId, resumeTurn(threadId, decision));
    },
    [run, threadId, turns],
  );

  const rate = useCallback(
    (messageId: string, score: -1 | 1) => {
      dispatch({ type: "score", messageId, score });
      void sendFeedback(threadId, messageId, score);
    },
    [threadId],
  );

  const reset = () => {
    const id = newThreadId();
    window.localStorage.setItem(THREAD_KEY, id);
    setThreadId(id);
    setPending(null);
    dispatch({ type: "reset", turns: [] });
  };

  const multiAgent = info ? Object.values(info.nodes).filter((n) => ["agent", "prompt", "supervisor"].includes(n.kind)).length > 1 : false;

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col px-4">
      <header className="sticky top-0 z-10 -mx-4 flex h-14 items-center gap-3 border-b border-line bg-canvas/85 px-4 backdrop-blur">
        <h1 className="text-[15px] font-semibold tracking-tight">{info?.title ?? "Assistant"}</h1>
        {info?.demo && (
          <span className="rounded-full bg-warn-soft px-2 py-0.5 text-xs font-medium text-warn" title="LLM_PROVIDER=fake">
            Demo mode
          </span>
        )}
        {info && !info.demo && <span className="font-mono text-xs text-muted">{info.model}</span>}
        <button
          type="button"
          onClick={reset}
          className="ml-auto inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm text-muted transition-colors hover:bg-surface hover:text-ink"
        >
          <ArrowCounterClockwise size={16} aria-hidden />
          New chat
        </button>
      </header>

      <main className="flex-1 py-6" aria-live="polite">
        {offline && (
          <div role="alert" className="flex items-start gap-3 rounded-xl border border-line bg-surface p-4 text-sm">
            <WarningCircle size={20} className="mt-0.5 shrink-0 text-danger" aria-hidden />
            <div>
              <p className="font-medium">Can&apos;t reach the API</p>
              <p className="mt-1 text-muted">{offline}</p>
            </div>
          </div>
        )}
        {info && turns.length === 0 && (
          <div className="enter mt-[18vh]">
            <p className="text-2xl font-semibold tracking-tight">{info.greeting}</p>
            <p className="mt-2 max-w-[52ch] text-muted">
              {info.features.knowledge.length > 0 && "I can search your documents. "}
              {info.features.approval && "Some replies wait for a person to approve them. "}
              {info.features.long_term_memory && "I remember what you tell me between chats. "}
              Ask me anything to begin.
            </p>
          </div>
        )}

        <ol className="space-y-8">
          {turns.map((turn, index) => (
            <li key={turn.id} className="space-y-3">
              <div className="enter ml-auto w-fit max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-[15px] leading-relaxed text-white">
                {turn.user.content}
              </div>
              {info?.features.show_steps !== false && (turn.steps.length > 0 || turn.running) && (
                <Activity steps={turn.steps} nodes={info?.nodes ?? {}} running={turn.running} />
              )}
              {turn.replies.map((r) => (
                <Reply
                  key={r.id}
                  message={r}
                  showLabel={multiAgent}
                  feedback={Boolean(info?.features.feedback) && !r.streaming && !r.id.startsWith("draft-")}
                  onRate={rate}
                />
              ))}
              {turn.error && (
                <p role="alert" className="flex items-center gap-2 text-sm text-danger">
                  <WarningCircle size={16} aria-hidden /> {turn.error}
                </p>
              )}
              {index === turns.length - 1 && pending && <ApprovalCard pending={pending} onDecide={decide} />}
            </li>
          ))}
        </ol>
        <div ref={bottom} />
      </main>

      <Composer
        disabled={!info || busy || Boolean(pending)}
        hint={pending ? "Approve or reject the reply above to continue." : undefined}
        knowledge={info?.features.knowledge ?? []}
        onSend={send}
      />
    </div>
  );
}
