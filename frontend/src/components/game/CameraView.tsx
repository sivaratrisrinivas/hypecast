"use client";

import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import {
  StreamVideoClient,
  useStreamVideoClient,
} from "@stream-io/video-react-sdk";

const CALL_TYPE = "default";

/** Delay before joining so the backend Runner has time to create the call on Stream (avoids coordinator timeout). Keep short (1s) so the camera is in the call before the agent's "wait for other participants" check. */
const JOIN_DELAY_MS = 1000;

/** Request and release media so device list is populated before Stream SDK join (avoids MicrophoneManager .find on undefined). */
async function ensureDeviceListPopulated(): Promise<void> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: true,
    });
    stream.getTracks().forEach((t) => t.stop());
  } catch {
    // Permission denied or no devices; continue anyway
  }
}

export type CameraViewProps = {
  onStart: () => void;
  /** When set, show join URL and QR (after session created). */
  joinUrl?: string | null;
  /** Stream call ID to join as publisher (when session is created). */
  streamCallId?: string | null;
  /** Optional client for testing; otherwise from StreamVideo context. */
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
    console.log("[CameraView] Effect triggered. client:", !!client, "streamCallId:", streamCallId);
    if (!client || !streamCallId) {
      console.log("[CameraView] Missing client or streamCallId — not joining.");
      return;
    }

    const call = client.call(CALL_TYPE, streamCallId);
    let cancelled = false;

    const run = async () => {
      setIsJoining(true);
      setJoinError(null);
      setHasJoined(false);
      try {
        console.log("[CameraView] Ensuring device list populated...");
        await ensureDeviceListPopulated();
        console.log("[CameraView] Device list populated. Waiting", JOIN_DELAY_MS, "ms for Runner to create call...");
        // Give Runner time to create the call on Stream; otherwise client join can timeout (5s).
        await new Promise((r) => setTimeout(r, JOIN_DELAY_MS));
        if (cancelled) return;
        console.log("[CameraView] Attempting call.join({ create: true }) for streamCallId:", streamCallId);
        await call.join({ create: true });
        console.log("[CameraView] call.join() SUCCESS");
        if (cancelled) {
          await call.leave();
          return;
        }
        setHasJoined(true);
        leaveRef.current = () => call.leave();
        console.log("[CameraView] Enabling camera...");
        await call.camera.enable().catch((e) => {
          console.warn("[CameraView] camera.enable failed:", e);
        });
        console.log("[CameraView] Camera enabled. Enabling microphone...");
        if (cancelled) return;
        await call.microphone.enable().catch((e) => {
          console.warn("[CameraView] microphone.enable failed:", e);
        });
        console.log("[CameraView] Microphone enabled. Camera is fully streaming.");
      } catch (err) {
        console.error("[CameraView] call.join() or setup FAILED:", err);
        if (!cancelled) {
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

    run();
    return () => {
      console.log("[CameraView] Effect cleanup — leaving call for streamCallId:", streamCallId);
      cancelled = true;
      leaveRef.current?.();
      leaveRef.current = null;
    };
  }, [client, streamCallId]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <div
        aria-label="Camera preview"
        className="mb-8 flex h-64 w-40 items-center justify-center rounded-xl border border-dashed border-neutral-500 bg-neutral-900/60"
      >
        <span className="text-sm text-neutral-400">
          {isJoining
            ? "Connecting..."
            : hasJoined
              ? "Streaming"
              : showJoinInfo
                ? "Waiting for camera..."
                : "Camera inactive"}
        </span>
      </div>

      {joinError && (
        <p className="mb-4 text-sm text-red-400" role="alert">
          {joinError}
        </p>
      )}

      {showJoinInfo ? (
        <div className="flex flex-col items-center gap-4">
          <p className="text-sm text-neutral-400">Open this link on your laptop</p>
          <a
            href={joinUrl ?? "#"}
            className="break-all text-emerald-400 underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {joinUrl}
          </a>
          <div className="rounded-lg bg-white p-3">
            <QRCodeSVG value={joinUrl ?? ""} size={160} level="M" />
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={onStart}
          className="rounded-full bg-emerald-500 px-10 py-3 text-lg font-bold uppercase tracking-wide text-black"
        >
          Start
        </button>
      )}
    </div>
  );
}
