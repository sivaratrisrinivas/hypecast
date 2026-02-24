"use client";

import { useEffect, useState } from "react";
import type { SessionStatus } from "@/types/session";

function getApiBase(): string {
  if (typeof window === "undefined") return "";
  return (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "") || "http://localhost:8000";
}

export type SpectatorSessionState = {
  streamToken: string;
  streamCallId: string;
  userId: string;
  status: SessionStatus;
  reelId: string | null;
  reelUrl: string | null;
};

type UseSpectatorSessionResult = {
  /** Session + token for spectator; null until loaded or when sessionId is null. */
  session: SpectatorSessionState | null;
  error: string | null;
  isLoading: boolean;
};

/** Fetches spectator token and session by session ID (e.g. from /game/[sessionId]). */
export function useSpectatorSession(sessionId: string | null): UseSpectatorSessionResult {
  const [session, setSession] = useState<SpectatorSessionState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(!!sessionId);

  useEffect(() => {
    if (!sessionId || typeof window === "undefined") {
      setSession(null);
      setError(null);
      setIsLoading(false);
      return;
    }

    const base = getApiBase();
    if (!base) {
      setError("API URL not configured");
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    const load = async () => {
      setError(null);
      setIsLoading(true);
      try {
        const [tokenRes, statusRes] = await Promise.all([
          fetch(`${base}/api/sessions/${sessionId}/token?role=spectator`),
          fetch(`${base}/api/sessions/${sessionId}`),
        ]);

        if (!tokenRes.ok) {
          if (tokenRes.status === 404) {
            setError("Session not found");
            return;
          }
          const text = await tokenRes.text();
          throw new Error(text || `Token failed: ${tokenRes.status}`);
        }

        const tokenBody = (await tokenRes.json()) as {
          stream_token: string;
          user_id: string;
          call_id: string;
        };
        let status: SessionStatus = "waiting";
        let reelId: string | null = null;
        let reelUrl: string | null = null;
        if (statusRes.ok) {
          const statusBody = (await statusRes.json()) as {
            status: SessionStatus;
            reel_id?: string | null;
            reel_url?: string | null;
          };
          status = statusBody.status;
          reelId = statusBody.reel_id ?? null;
          reelUrl = statusBody.reel_url ?? null;
        }

        if (!cancelled) {
          setSession({
            streamToken: tokenBody.stream_token,
            streamCallId: tokenBody.call_id,
            userId: tokenBody.user_id,
            status,
            reelId,
            reelUrl,
          });
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load session");
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  return { session, error, isLoading };
}
