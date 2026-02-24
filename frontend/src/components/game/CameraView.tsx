"use client";

import { useEffect, useRef, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import {
  StreamVideoClient,
  useStreamVideoClient,
} from "@stream-io/video-react-sdk";

const CALL_TYPE = "default";

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
  const leaveRef = useRef<(() => Promise<void>) | null>(null);

  const showJoinInfo = Boolean(joinUrl);

  useEffect(() => {
    if (!client || !streamCallId) return;

    const call = client.call(CALL_TYPE, streamCallId);
    let cancelled = false;

    const run = async () => {
      setIsJoining(true);
      setJoinError(null);
      try {
        await call.camera.enable();
        await call.microphone.enable();
        await call.join({ create: true });
        if (cancelled) {
          await call.leave();
          return;
        }
        leaveRef.current = () => call.leave();
      } catch (err) {
        if (!cancelled) {
          setJoinError(err instanceof Error ? err.message : "Failed to join");
        }
      } finally {
        if (!cancelled) setIsJoining(false);
      }
    };

    run();
    return () => {
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
            : showJoinInfo
              ? "Streaming"
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
