"use client";

import { useEffect, useRef, useState } from "react";
import {
  ParticipantView,
  StreamCall,
  StreamVideoClient,
  useStreamVideoClient,
  useCallStateHooks,
} from "@stream-io/video-react-sdk";
import type { SessionStatus } from "@/src/types/session";
import { CommentaryTranscript } from "./CommentaryTranscript";

const CALL_TYPE = "default";

type SpectatorViewProps = {
  /** Mock or polled status (waiting, live, processing, etc.). */
  status?: SessionStatus;
  /** Stream call ID to join as subscriber (when provided with client). */
  streamCallId?: string | null;
  /** Optional client for testing; otherwise from StreamVideo context. */
  streamVideoClient?: StreamVideoClient | null;
};

const STATUS_LABELS: Record<SessionStatus, string> = {
  waiting: "Awaiting connection...",
  live: "Live",
  processing: "Generating Reel",
  completed: "Reel ready",
  error: "Something went wrong",
};

function SpectatorCallContent() {
  const { useRemoteParticipants } = useCallStateHooks();
  const remoteParticipants = useRemoteParticipants();
  const [audioEnabled, setAudioEnabled] = useState(false);

  const handleEnableAudio = () => {
    // Unlocking browser autoplay policy
    try {
      const ctx = new AudioContext();
      ctx.resume();
    } catch (e) {
      console.warn("[SpectatorCallContent] AudioContext unlock failed:", e);
    }
    setAudioEnabled(true);
  };

  if (remoteParticipants.length === 0) {
    return (
      <div className="flex min-h-[240px] w-full items-center justify-center rounded-xl border border-dashed border-neutral-500 bg-neutral-900/60">
        <p className="text-sm text-neutral-400">Waiting for stream...</p>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col gap-4">
      {!audioEnabled && (
        <button
          type="button"
          onClick={handleEnableAudio}
          className="mx-auto rounded-full bg-emerald-500 px-6 py-2 text-sm font-semibold uppercase tracking-wide text-black hover:bg-emerald-400 transition-colors"
        >
          🔊 Enable Audio
        </button>
      )}
      {audioEnabled && (
        <div className="space-y-4">
          <p className="text-center text-xs text-emerald-400 font-medium">🔊 Audio active</p>
          {remoteParticipants.map((participant) => (
            <ParticipantView
              key={participant.sessionId}
              participant={participant}
              className="aspect-video w-full overflow-hidden rounded-xl bg-black shadow-2xl border border-neutral-800"
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function SpectatorView({
  status = "waiting",
  streamCallId,
  streamVideoClient: clientProp,
}: SpectatorViewProps) {
  const clientFromContext = useStreamVideoClient();
  const client = clientProp ?? clientFromContext;
  const [joinError, setJoinError] = useState<string | null>(null);
  const [isJoining, setIsJoining] = useState(false);
  const [callReady, setCallReady] = useState(false);
  const callRef = useRef<ReturnType<StreamVideoClient["call"]> | null>(null);

  const hasClientAndCallId = Boolean(client && streamCallId);
  const label = STATUS_LABELS[status];

  useEffect(() => {
    console.log("[SpectatorView] Effect triggered. client:", !!client, "streamCallId:", streamCallId, "status:", status);
    if (!client || !streamCallId) {
      console.log("[SpectatorView] Missing client or streamCallId — not joining. client:", !!client, "streamCallId:", streamCallId);
      setCallReady(false);
      callRef.current = null;
      return;
    }
    let cancelled = false;
    const call = client.call(CALL_TYPE, streamCallId);
    callRef.current = call;
    console.log("[SpectatorView] Created call instance for streamCallId:", streamCallId, "callType:", CALL_TYPE);

    const run = async () => {
      setIsJoining(true);
      setJoinError(null);
      console.log("[SpectatorView] Attempting call.join({ create: false }) for streamCallId:", streamCallId);
      try {
        await call.join({ create: false });
        console.log("[SpectatorView] call.join() SUCCESS for streamCallId:", streamCallId);
        if (cancelled) {
          console.log("[SpectatorView] Join succeeded but effect was cancelled — leaving call.");
          await call.leave();
          return;
        }
        setCallReady(true);
        console.log("[SpectatorView] callReady set to true. Call state:", call.state);
      } catch (err) {
        console.error("[SpectatorView] call.join() FAILED for streamCallId:", streamCallId, "error:", err);
        if (!cancelled) {
          setJoinError(err instanceof Error ? err.message : "Failed to join");
        }
      } finally {
        if (!cancelled) setIsJoining(false);
      }
    };

    run();
    return () => {
      console.log("[SpectatorView] Effect cleanup — leaving call for streamCallId:", streamCallId);
      cancelled = true;
      callRef.current = null;
      setCallReady(false);
      call.leave().catch(() => { });
    };
  }, [client, streamCallId]);

  const call = callRef.current;

  if (!hasClientAndCallId) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
        <p className="mb-4 text-lg text-neutral-300">{label}</p>
        <p className="text-sm text-neutral-500">Mock timer: 0:00</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <p className="mb-4 text-lg text-neutral-300">{label}</p>
      {isJoining && (
        <p className="mb-2 text-sm text-neutral-400">Connecting to stream...</p>
      )}
      {joinError && (
        <p className="mb-4 text-sm text-red-400" role="alert">
          {joinError}
        </p>
      )}
      {call && callReady && (
        <StreamCall call={call}>
          <div className="w-full max-w-2xl px-4">
            <SpectatorCallContent />
            <CommentaryTranscript
              sessionId={
                streamCallId
                  ? streamCallId.replace(/^pickup-/, "")
                  : null
              }
            />
          </div>
        </StreamCall>
      )}
      {!callReady && !joinError && hasClientAndCallId && (
        <div className="flex min-h-[240px] w-full max-w-2xl items-center justify-center rounded-xl border border-dashed border-neutral-500 bg-neutral-900/60 px-4">
          <p className="text-sm text-neutral-400">Connecting...</p>
        </div>
      )}
    </div>
  );
}
