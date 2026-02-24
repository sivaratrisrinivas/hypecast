"use client";

import { useEffect, useRef, useState } from "react";
import {
  ParticipantView,
  StreamCall,
  StreamVideoClient,
  useStreamVideoClient,
  useCallStateHooks,
} from "@stream-io/video-react-sdk";
import type { SessionStatus } from "@/types/session";

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

  if (remoteParticipants.length === 0) {
    return (
      <div className="flex min-h-[240px] w-full items-center justify-center rounded-xl border border-dashed border-neutral-500 bg-neutral-900/60">
        <p className="text-sm text-neutral-400">Waiting for stream...</p>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col gap-4">
      {remoteParticipants.map((participant) => (
        <ParticipantView
          key={participant.sessionId}
          participant={participant}
          className="aspect-video w-full overflow-hidden rounded-xl bg-black"
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
    let cancelled = false;
    const call = client.call(CALL_TYPE, streamCallId);
    callRef.current = call;
    if (process.env.NODE_ENV === "development") {
      console.debug("[SpectatorView] effect run: new call instance, joining once", streamCallId);
    }

    const run = async () => {
      setIsJoining(true);
      setJoinError(null);
      try {
        await call.join({ create: false });
        if (cancelled) {
          await call.leave();
          return;
        }
        setCallReady(true);
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
      callRef.current = null;
      setCallReady(false);
      call.leave().catch(() => {});
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
