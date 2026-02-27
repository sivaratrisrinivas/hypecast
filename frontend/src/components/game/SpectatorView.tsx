"use client";

import { useEffect, useRef, useState } from "react";

const GEMINI_MODEL =
  process.env.NEXT_PUBLIC_GEMINI_MODEL ?? "gemini-3-flash-preview";
import {
  ParticipantView,
  StreamCall,
  StreamVideoClient,
  useCallStateHooks,
  useStreamVideoClient,
} from "@stream-io/video-react-sdk";
import type { SessionStatus } from "@/src/types/session";
import { CommentaryTranscript } from "./CommentaryTranscript";

const CALL_TYPE = "default";

type SpectatorViewProps = {
  status?: SessionStatus;
  streamCallId?: string | null;
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
    try {
      const ctx = new AudioContext();
      void ctx.resume();
    } catch {
      // ignore
    }
    setAudioEnabled(true);
  };

  if (remoteParticipants.length === 0) {
    return (
      <div className="flex min-h-[240px] w-full items-center justify-center rounded-2xl border border-dashed border-neutral-700 bg-neutral-900/60">
        <p className="text-sm text-neutral-400">Waiting for stream...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {!audioEnabled && (
        <button
          type="button"
          onClick={handleEnableAudio}
          className="mx-auto block rounded-full bg-emerald-400 px-5 py-2 text-sm font-semibold text-black transition hover:bg-emerald-300"
        >
          🔊 Enable Audio
        </button>
      )}

      {audioEnabled && (
        <p className="text-center text-xs font-medium text-emerald-400">🔊 Audio active</p>
      )}

      {remoteParticipants.map((participant) => (
        <ParticipantView
          key={participant.sessionId}
          participant={participant}
          className="aspect-video w-full overflow-hidden rounded-2xl border border-neutral-800 bg-black shadow-2xl"
        />
      ))}
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
    if (!client || !streamCallId) {
      setCallReady(false);
      callRef.current = null;
      return;
    }

    console.log("[SpectatorView] join effect", { streamCallId });
    let cancelled = false;
    const call = client.call(CALL_TYPE, streamCallId);
    callRef.current = call;

    const run = async () => {
      setIsJoining(true);
      setJoinError(null);
      console.log("[SpectatorView] Joining call...", streamCallId);
      try {
        await call.join({ create: false, audio: false, video: false });
        if (cancelled) {
          await call.leave();
          return;
        }
        console.log("[SpectatorView] Call joined");
        setCallReady(true);
      } catch (err) {
        if (!cancelled) {
          console.error("[SpectatorView] Join failed", err);
          setJoinError(err instanceof Error ? err.message : "Failed to join");
        }
      } finally {
        if (!cancelled) setIsJoining(false);
      }
    };

    void run();
    return () => {
      cancelled = true;
      callRef.current = null;
      setCallReady(false);
      void call.leave().catch(() => undefined);
    };
  }, [client, streamCallId]);

  const call = callRef.current;

  if (!hasClientAndCallId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black px-4 text-white">
        <div className="w-full max-w-3xl rounded-3xl border border-white/10 bg-neutral-950/70 p-6 text-center backdrop-blur">
          <p className="text-xs tracking-[0.2em] text-neutral-500">HYPECAST</p>
          <p className="mt-3 text-2xl font-semibold">{label}</p>
          <p className="mt-3 text-sm text-neutral-500">Mock timer: 0:00</p>
          <p className="mt-4 text-xs text-neutral-600">Powered by {GEMINI_MODEL}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-black px-4 text-white">
      <div className="w-full max-w-3xl rounded-3xl border border-white/10 bg-neutral-950/70 p-6 backdrop-blur">
        <p className="text-center text-xs tracking-[0.2em] text-neutral-500">HYPECAST</p>
        <p className="mt-2 text-center text-3xl font-semibold">{label}</p>

        {isJoining && <p className="mt-2 text-center text-sm text-neutral-400">Connecting to stream...</p>}
        {joinError && (
          <p className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300" role="alert">
            {joinError}
          </p>
        )}

        {call && callReady && (
          <StreamCall call={call}>
            <div className="mt-5">
              <SpectatorCallContent />
              <CommentaryTranscript sessionId={streamCallId ? streamCallId.replace(/^pickup-/, "") : null} />
            </div>
          </StreamCall>
        )}

        {!callReady && !joinError && hasClientAndCallId && (
          <div className="mt-5 flex min-h-[240px] w-full items-center justify-center rounded-2xl border border-dashed border-neutral-700 bg-neutral-900/60 px-4">
            <p className="text-sm text-neutral-400">Connecting...</p>
          </div>
        )}
        <p className="mt-4 text-center text-xs text-neutral-600">
          Powered by {GEMINI_MODEL}
        </p>
      </div>
    </div>
  );
}
