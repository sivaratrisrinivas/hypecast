"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createSession } from "@/src/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Role = "camera" | "spectator";

function detectRole(): Role {
  if (typeof window === "undefined") return "spectator";
  const forced = new URL(window.location.href).searchParams.get("role");
  if (forced === "camera" || forced === "spectator") return forced;
  return window.innerWidth < 900 ? "camera" : "spectator";
}

export function HypecastApp(): JSX.Element {
  const [role, setRole] = useState<Role>("spectator");
  const [sessionId, setSessionId] = useState<string>("");
  const [joinLink, setJoinLink] = useState<string>("");
  const [commentary, setCommentary] = useState<string[]>([]);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    setRole(detectRole());
  }, []);

  useEffect(() => {
    if (role !== "camera") return;
    let stream: MediaStream | null = null;
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((mediaStream) => {
        stream = mediaStream;
        if (videoRef.current) videoRef.current.srcObject = mediaStream;
      })
      .catch(() => undefined);

    return () => {
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, [role]);

  useEffect(() => {
    if (!sessionId || role !== "spectator") return;
    const ws = new WebSocket(`${API_BASE.replace("http", "ws")}/api/ws/sessions/${sessionId}/commentary`);
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { text?: string };
        if (payload.text) setCommentary((prev) => [...prev, payload.text]);
      } catch {
        // ignore malformed message
      }
    };
    return () => ws.close();
  }, [role, sessionId]);

  const heading = useMemo(
    () => (role === "camera" ? "Camera Mode" : "Spectator Mode"),
    [role],
  );

  async function onStart(): Promise<void> {
    const session = await createSession();
    const fullUrl = `${window.location.origin}${session.join_url}?role=spectator`;
    setSessionId(session.session_id);
    setJoinLink(fullUrl);
  }

  return (
    <main style={{ padding: 24, maxWidth: 880, margin: "0 auto" }}>
      <h1>HypeCast</h1>
      <p>Real-time sports commentary with Vision Agents + Gemini.</p>
      <h2>{heading}</h2>

      {role === "camera" ? (
        <section>
          <video
            ref={videoRef}
            autoPlay
            muted
            playsInline
            style={{ width: "100%", maxWidth: 560, borderRadius: 12, border: "1px solid #333" }}
          />
          <div style={{ marginTop: 12 }}>
            <button onClick={() => void onStart()} style={{ padding: "10px 16px", borderRadius: 10 }}>
              START SESSION
            </button>
          </div>
          {joinLink && (
            <p style={{ marginTop: 12 }}>
              Share this link on laptop: <a href={joinLink}>{joinLink}</a>
            </p>
          )}
        </section>
      ) : (
        <section>
          <label htmlFor="session">Session ID</label>
          <input
            id="session"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            placeholder="Enter session id"
            style={{ display: "block", marginTop: 8, marginBottom: 12, padding: 10, width: "100%" }}
          />
          <div style={{ border: "1px solid #333", borderRadius: 12, padding: 12 }}>
            <h3>Live Commentary</h3>
            {commentary.length === 0 ? (
              <p>Waiting for commentary…</p>
            ) : (
              <ul>
                {commentary.map((line, idx) => (
                  <li key={`${line}-${idx}`}>{line}</li>
                ))}
              </ul>
            )}
          </div>
        </section>
      )}
    </main>
  );
}
