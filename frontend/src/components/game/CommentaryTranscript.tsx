"use client";

import { useEffect, useRef, useState } from "react";

type CommentaryLine = {
    text: string;
    energy_level: number;
    is_highlight: boolean;
    ts: number; // local timestamp for key
};

type Props = {
    sessionId: string | null;
};

function getWsBase(): string {
    if (typeof window === "undefined") return "";
    const api =
        (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "") ||
        "http://localhost:8000";
    return api.replace(/^http/, "ws");
}

/**
 * Connects to the backend commentary WebSocket and displays Gemini's
 * live text commentary as an auto-scrolling ticker overlay.
 */
export function CommentaryTranscript({ sessionId }: Props) {
    const [lines, setLines] = useState<CommentaryLine[]>([]);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!sessionId) return;
        const wsBase = getWsBase();
        if (!wsBase) return;

        const url = `${wsBase}/api/ws/sessions/${sessionId}/commentary`;
        let ws: WebSocket | null = null;
        let cancelled = false;

        const connect = () => {
            if (cancelled) return;
            console.log("[CommentaryTranscript] Connecting WebSocket to:", url);
            ws = new WebSocket(url);

            ws.onopen = () => {
                console.log("[CommentaryTranscript] WebSocket OPEN for session:", sessionId);
            };

            ws.onmessage = (evt) => {
                try {
                    const data = JSON.parse(evt.data) as {
                        text: string;
                        energy_level: number;
                        is_highlight: boolean;
                    };
                    console.log("[CommentaryTranscript] Received commentary:", data.text.substring(0, 80), "| energy:", data.energy_level, "| highlight:", data.is_highlight);
                    setLines((prev) => [
                        ...prev.slice(-49), // keep last 50 lines
                        { ...data, ts: Date.now() },
                    ]);
                } catch (e) {
                    console.warn("[CommentaryTranscript] Failed to parse message:", evt.data, e);
                }
            };

            ws.onclose = (evt) => {
                console.log("[CommentaryTranscript] WebSocket CLOSED. code:", evt.code, "reason:", evt.reason, "| Reconnecting in 2s...");
                // Reconnect after 2s if not cancelled
                if (!cancelled) setTimeout(connect, 2000);
            };

            ws.onerror = (evt) => {
                console.error("[CommentaryTranscript] WebSocket ERROR:", evt);
                ws?.close();
            };
        };

        connect();
        return () => {
            cancelled = true;
            ws?.close();
        };
    }, [sessionId]);

    // Auto-scroll to bottom
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
        <div className="mt-4 w-full max-h-48 overflow-y-auto rounded-xl bg-neutral-900/80 px-4 py-3 scrollbar-thin scrollbar-thumb-neutral-700">
            {lines.map((line, i) => (
                <p
                    key={`${line.ts}-${i}`}
                    className={`mb-1 text-sm leading-relaxed ${line.is_highlight
                        ? "font-bold text-yellow-400"
                        : "text-neutral-200"
                        }`}
                >
                    {line.text}
                </p>
            ))}
            <div ref={bottomRef} />
        </div>
    );
}
