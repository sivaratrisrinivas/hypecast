"use client";

import { useEffect, useRef, useState } from "react";

type CommentaryLine = {
  text: string;
  energy_level: number;
  is_highlight: boolean;
  ts: number;
};

type Props = {
  sessionId: string | null;
};

function getWsBase(): string {
  if (typeof window === "undefined") return "";
  const api = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "") || "http://localhost:8000";
  return api.replace(/^http/, "ws");
}

export function CommentaryTranscript({ sessionId }: Props) {
  const [lines, setLines] = useState<CommentaryLine[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!sessionId) return;
    const wsBase = getWsBase();
    if (!wsBase) return;

    const url = `${wsBase}/api/ws/sessions/${sessionId}/commentary`;
    console.log("[CommentaryTranscript] connecting", { url, sessionId });
    let ws: WebSocket | null = null;
    let cancelled = false;
    let connectTimer: ReturnType<typeof setTimeout> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;

      ws = new WebSocket(url);
      ws.onopen = () => console.log("[CommentaryTranscript] WebSocket connected");
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data) as {
            text: string;
            energy_level: number;
            is_highlight: boolean;
          };
          setLines((prev) => [...prev.slice(-49), { ...data, ts: Date.now() }]);
        } catch {
          // Ignore malformed packets.
        }
      };

      ws.onclose = (e) => {
        console.log("[CommentaryTranscript] WebSocket closed", e.code, e.reason);
        if (cancelled) return;
        reconnectTimer = setTimeout(connect, 1000);
      };

      ws.onerror = (e) => {
        console.warn("[CommentaryTranscript] WebSocket error", e);
      };
    };

    connectTimer = setTimeout(connect, 0);
    return () => {
      cancelled = true;
      if (connectTimer) clearTimeout(connectTimer);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws && ws.readyState !== WebSocket.CLOSED) {
        ws.close();
      }
    };
  }, [sessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  if (lines.length === 0) {
    return (
      <div className="mt-4 w-full rounded-xl bg-neutral-900/80 px-4 py-3 text-center text-sm text-neutral-500">
        Waiting for commentary…
      </div>
    );
  }

  return (
    <div className="mt-4 max-h-48 w-full overflow-y-auto rounded-xl bg-neutral-900/80 px-4 py-3 scrollbar-thin scrollbar-thumb-neutral-700">
      {lines.map((line, i) => (
        <p
          key={`${line.ts}-${i}`}
          className={`mb-1 text-sm leading-relaxed ${line.is_highlight ? "font-bold text-yellow-400" : "text-neutral-200"}`}
        >
          {line.text}
        </p>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
