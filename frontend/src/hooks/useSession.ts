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
    console.log("[useSession] Creating session... POST", `${base}/api/sessions`);
    try {
      const res = await fetch(`${base}/api/sessions`, { method: "POST" });
      console.log("[useSession] POST /api/sessions response:", res.status, res.statusText);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Session create failed: ${res.status}`);
      }
      const body = (await res.json()) as Record<string, unknown>;
      console.log("[useSession] POST /api/sessions body:", body);
      const createPayload = mapCreateResponse(body);
      console.log("[useSession] Mapped create payload:", createPayload);
      // Fire-and-forget Vision Agents runner session so the agent joins the Stream call.
      // Runner expects: POST /sessions { "call_type": "default", "call_id": "<stream_call_id>" }.
      if (base && createPayload.streamCallId) {
        // Use an async IIFE so test environments that stub `fetch` as a bare
        // function (returning undefined) don't throw when accessing `.catch`.
        // Any network error here is non-fatal to the main app flow.
        void (async () => {
          try {
            const runnerRes = await fetch(`${base}/sessions`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                call_type: "default",
                call_id: createPayload.streamCallId,
              }),
            });
            console.info(
              "[useSession] Runner POST /sessions →",
              runnerRes.status,
              runnerRes.statusText,
            );
          } catch (err) {
            console.warn(
              "[useSession] Runner POST /sessions failed:",
              err,
            );
          }
        })();
      }
      console.log("[useSession] Setting initial session state (waiting)");
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
        console.log("[useSession] Polling GET", `${base}/api/sessions/${session.sessionId}`);
        const res = await fetch(`${base}/api/sessions/${session.sessionId}`, {
          signal: pollAbortRef.current.signal,
        });
        if (!res.ok) {
          console.warn("[useSession] Poll response not ok:", res.status);
          if (res.status === 404) return;
          setError(`Poll failed: ${res.status}`);
          return;
        }
        const body = (await res.json()) as Record<string, unknown>;
        const statusPayload = mapStatusResponse(body);
        console.log("[useSession] Poll result:", statusPayload);
        setSession((prev: SessionState | null) => {
          if (!prev) return null;
          // Avoid new object reference when nothing changed (prevents downstream memo busts)
          if (
            prev.status === statusPayload.status &&
            prev.reelId === statusPayload.reelId &&
            prev.reelUrl === statusPayload.reelUrl
          ) {
            return prev;
          }
          return { ...prev, ...statusPayload };
        });
      } catch (err) {
        if (err instanceof Error && err.name === "AbortError") return;
        console.error("[useSession] Poll error:", err);
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
