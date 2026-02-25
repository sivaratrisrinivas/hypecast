"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  SessionCreateResponse,
  SessionStatus,
  SessionStatusResponse,
} from "@/src/types/session";

const POLL_INTERVAL_MS = 5000;

function getApiBase(): string {
  if (typeof window === "undefined") return "";
  return (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "") || "http://localhost:8000";
}

/** Session state: create response + polled status. */
export type SessionState = SessionCreateResponse & {
  status: SessionStatus;
  reelId: string | null;
  reelUrl: string | null;
};

type UseSessionResult = {
  /** Current session (create payload + status from polling). Null until created. */
  session: SessionState | null;
  /** Create a new session (POST), then start polling. */
  createSession: () => Promise<void>;
  /** Error from last create or poll. */
  error: string | null;
  /** True while POST /api/sessions is in flight. */
  isCreating: boolean;
};

function mapCreateResponse(body: Record<string, unknown>): SessionCreateResponse {
  return {
    sessionId: body.session_id as string,
    streamCallId: body.stream_call_id as string,
    streamToken: body.stream_token as string,
    joinUrl: body.join_url as string,
  };
}

function mapStatusResponse(body: Record<string, unknown>): SessionStatusResponse {
  return {
    status: body.status as SessionStatus,
    reelId: (body.reel_id as string | null) ?? null,
    reelUrl: (body.reel_url as string | null) ?? null,
  };
}

export function useSession(): UseSessionResult {
  const [session, setSession] = useState<SessionState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const pollAbortRef = useRef<AbortController | null>(null);

  const createSession = useCallback(async () => {
    setError(null);
    setIsCreating(true);
    const base = getApiBase();
    try {
      const res = await fetch(`${base}/api/sessions`, { method: "POST" });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Session create failed: ${res.status}`);
      }
      const body = (await res.json()) as Record<string, unknown>;
      const createPayload = mapCreateResponse(body);
      // Fire-and-forget Vision Agents runner session so the agent joins the Stream call.
      // Runner expects: POST /sessions { "call_type": "default", "call_id": "<stream_call_id>" }.
      if (base && createPayload.streamCallId) {
        // Use an async IIFE so test environments that stub `fetch` as a bare
        // function (returning undefined) don't throw when accessing `.catch`.
        // Any network error here is non-fatal to the main app flow.
        void (async () => {
          try {
            await fetch(`${base}/sessions`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                call_type: "default",
                call_id: createPayload.streamCallId,
              }),
            });
          } catch (err) {
            if (process.env.NODE_ENV === "development") {
              // eslint-disable-next-line no-console
              console.error(
                "[useSession] Failed to start Vision Agent session:",
                err,
              );
            }
          }
        })();
      }
      setSession({
        ...createPayload,
        status: "waiting",
        reelId: null,
        reelUrl: null,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create session");
    } finally {
      setIsCreating(false);
    }
  }, []);

  // Poll GET /api/sessions/{id} when we have a session; stop when terminal status or unmount
  useEffect(() => {
    if (!session?.sessionId) return;

    const base = getApiBase();
    if (!base) return;

    const tick = async () => {
      if (pollAbortRef.current) pollAbortRef.current.abort();
      pollAbortRef.current = new AbortController();
      try {
        const res = await fetch(`${base}/api/sessions/${session.sessionId}`, {
          signal: pollAbortRef.current.signal,
        });
        if (!res.ok) {
          if (res.status === 404) return;
          setError(`Poll failed: ${res.status}`);
          return;
        }
        const body = (await res.json()) as Record<string, unknown>;
        const statusPayload = mapStatusResponse(body);
        setSession((prev: SessionState | null) =>
          prev
            ? { ...prev, ...statusPayload }
            : null
        );
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Poll error");
      }
    };

    tick();
    const interval = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      clearInterval(interval);
      if (pollAbortRef.current) {
        pollAbortRef.current.abort();
        pollAbortRef.current = null;
      }
    };
  }, [session?.sessionId]);

  return { session, createSession, error, isCreating };
}
