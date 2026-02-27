"use client";

import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import {
  StreamVideoClient,
  useStreamVideoClient,
} from "@stream-io/video-react-sdk";

const CALL_TYPE = "default";
const JOIN_DELAY_MS = 1000;

async function ensureDeviceListPopulated(): Promise<void> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
    stream.getTracks().forEach((t) => t.stop());
  } catch {
    // Continue; call join can still work on some browsers.
  }
}

const GEMINI_MODEL =
  process.env.NEXT_PUBLIC_GEMINI_MODEL ?? "gemini-3-flash-preview";

export type CameraViewProps = {
  onStart: () => void;
  joinUrl?: string | null;
  streamCallId?: string | null;
  streamVideoClient?: StreamVideoClient | null;
};

export function CameraView({
  onStart,
  joinUrl,
  streamCallId,
  streamVideoClient: clientProp,
}: CameraViewProps) {
  const clientFromContext = useStreamVideoClient();
  const client = clientProp ?? clientFromContext;
  const [joinError, setJoinError] = useState<string | null>(null);
  const [isJoining, setIsJoining] = useState(false);
  const [hasJoined, setHasJoined] = useState(false);
  const leaveRef = useRef<(() => Promise<void>) | null>(null);

  const showJoinInfo = Boolean(joinUrl);

  useEffect(() => {
    if (!client || !streamCallId) return;

    console.log("[CameraView] join effect", { streamCallId, hasClient: !!client });
    const call = client.call(CALL_TYPE, streamCallId);
    let cancelled = false;

    const run = async () => {
      setIsJoining(true);
      setJoinError(null);
      setHasJoined(false);
      console.log("[CameraView] Joining call...", streamCallId);
      try {
        await ensureDeviceListPopulated();
        await new Promise((r) => setTimeout(r, JOIN_DELAY_MS));
        if (cancelled) return;
        await call.join({ create: true });
        if (cancelled) {
          await call.leave();
          return;
        }
        console.log("[CameraView] Call joined, enabling camera/mic");
        setHasJoined(true);
        leaveRef.current = () => call.leave();
        await call.camera.enable().catch(() => undefined);
        if (cancelled) return;
        await call.microphone.enable().catch(() => undefined);
      } catch (err) {
        if (!cancelled) {
          console.error("[CameraView] Join failed", err);
          const msg = err instanceof Error ? err.message : String(err);
          const isMediaError =
            msg.toLowerCase().includes("video stream") ||
            msg.toLowerCase().includes("permission") ||
            msg.toLowerCase().includes("notallowed") ||
            msg.toLowerCase().includes("notfound") ||
            msg === "" ||
            msg === "{}";
          setJoinError(
            isMediaError
              ? "Camera/mic unavailable. Open this page in Chrome or Safari for full camera access."
              : msg || "Failed to join call",
          );
        }
      } finally {
        if (!cancelled) setIsJoining(false);
      }
    };

    void run();
    return () => {
      cancelled = true;
      void leaveRef.current?.();
      leaveRef.current = null;
    };
  }, [client, streamCallId]);

  const cameraStatus = isJoining
    ? "Connecting..."
    : hasJoined
      ? "Streaming"
      : showJoinInfo
        ? "Waiting for camera..."
        : "Camera inactive";

  return (
    <div className="flex min-h-screen items-center justify-center bg-black px-4 text-white">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-neutral-950/70 p-6 shadow-2xl backdrop-blur">
        <p className="text-xs tracking-[0.2em] text-neutral-500">HYPECAST</p>
        <h1 className="mt-2 text-2xl font-semibold">One-tap live camera</h1>
        <p className="mt-2 text-sm text-neutral-400">
          Point at the game, tap start, and share the link for instant spectator commentary.
        </p>

        <div
          aria-label="Camera preview"
          className="mt-6 flex h-64 w-full items-center justify-center rounded-2xl border border-dashed border-neutral-700 bg-neutral-900/70"
        >
          <span className="text-sm text-neutral-300">{cameraStatus}</span>
        </div>

        {joinError && (
          <p className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300" role="alert">
            {joinError}
          </p>
        )}

        {showJoinInfo ? (
          <div className="mt-6 flex flex-col items-center gap-4">
            <p className="text-sm text-neutral-400">Open this link on your laptop</p>
            <a
              href={joinUrl ?? "#"}
              className="break-all text-center text-emerald-400 underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {joinUrl}
            </a>
            <div className="rounded-xl bg-white p-3">
              <QRCodeSVG value={joinUrl ?? ""} size={160} level="M" />
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={onStart}
            className="mt-6 w-full rounded-full bg-emerald-400 px-10 py-3 text-lg font-bold uppercase tracking-wide text-black transition hover:bg-emerald-300"
          >
            Start
          </button>
        )}
        <p className="mt-4 text-center text-xs text-neutral-600">
          Powered by {GEMINI_MODEL}
        </p>
      </div>
    </div>
  );
}
