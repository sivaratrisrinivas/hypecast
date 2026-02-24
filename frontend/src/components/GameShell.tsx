"use client";

import { useEffect, useMemo, useRef } from "react";
import { StreamVideo, StreamVideoClient } from "@stream-io/video-react-sdk";
import { useDeviceRole } from "@/src/hooks/useDeviceRole";
import { useSession } from "@/src/hooks/useSession";
import { useSpectatorSession } from "@/src/hooks/useSpectatorSession";
import { CameraView } from "@/src/components/game/CameraView";
import { SpectatorView } from "@/src/components/game/SpectatorView";
import { isSessionStatus, type SessionStatus } from "@/src/types/session";

function getSpectatorStatusFromUrl(): SessionStatus {
  if (typeof window === "undefined") return "waiting";
  const p = new URL(window.location.href).searchParams.get("status");
  return isSessionStatus(p ?? "") ? p : "waiting";
}

const STREAM_API_KEY = process.env.NEXT_PUBLIC_STREAM_API_KEY ?? "";

export type GameShellProps = {
  /** When set (e.g. on /game/[sessionId]), spectator loads this session and joins the Stream call. */
  spectatorSessionId?: string | null;
};

export function GameShell({ spectatorSessionId = null }: GameShellProps) {
  const { role, isLoading } = useDeviceRole();
  const { session, createSession, error: sessionError, isCreating } = useSession();
  const {
    session: spectatorSession,
    error: spectatorError,
    isLoading: spectatorLoading,
  } = useSpectatorSession(spectatorSessionId ?? null);

  const streamClient = useMemo(() => {
    if (!session || typeof window === "undefined" || !STREAM_API_KEY) return null;
    return StreamVideoClient.getOrCreateInstance({
      apiKey: STREAM_API_KEY,
      user: { id: `camera-${session.sessionId}` },
      token: session.streamToken,
    });
  }, [session?.sessionId, session?.streamToken]);

  const spectatorClient = useMemo(() => {
    if (!spectatorSession || typeof window === "undefined" || !STREAM_API_KEY) return null;
    return StreamVideoClient.getOrCreateInstance({
      apiKey: STREAM_API_KEY,
      user: { id: spectatorSession.userId },
      token: spectatorSession.streamToken,
    });
  }, [spectatorSession?.userId, spectatorSession?.streamToken]);

  const cameraClientRef = useRef<StreamVideoClient | null>(null);
  useEffect(() => {
    if (!streamClient) return;
    const prev = cameraClientRef.current;
    if (prev && prev !== streamClient) {
      prev.disconnectUser().catch(() => {});
    }
    cameraClientRef.current = streamClient;
    return () => {
      cameraClientRef.current = null;
    };
  }, [streamClient]);

  const spectatorClientRef = useRef<StreamVideoClient | null>(null);
  useEffect(() => {
    if (!spectatorClient) return;
    const prev = spectatorClientRef.current;
    if (prev && prev !== spectatorClient) {
      prev.disconnectUser().catch(() => {});
    }
    spectatorClientRef.current = spectatorClient;
    return () => {
      spectatorClientRef.current = null;
    };
  }, [spectatorClient]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-white">
        <p className="text-neutral-400">Detecting device...</p>
      </div>
    );
  }

  if (role === "camera") {
    const joinUrl = session
      ? `${typeof window !== "undefined" ? window.location.origin : ""}${session.joinUrl}`
      : null;

    const cameraView = (
      <CameraView
        onStart={createSession}
        joinUrl={joinUrl}
        streamCallId={session?.streamCallId ?? null}
      />
    );

    if (streamClient) {
      return (
        <StreamVideo client={streamClient}>
          {sessionError && (
            <div className="fixed left-0 right-0 top-0 bg-red-900/90 px-4 py-2 text-center text-sm text-white">
              {sessionError}
            </div>
          )}
          {cameraView}
        </StreamVideo>
      );
    }

    return (
      <>
        {sessionError && (
          <div className="fixed left-0 right-0 top-0 bg-red-900/90 px-4 py-2 text-center text-sm text-white">
            {sessionError}
          </div>
        )}
        {isCreating && (
          <div className="fixed left-0 right-0 top-0 bg-black/80 px-4 py-2 text-center text-sm text-white">
            Creating session...
          </div>
        )}
        {cameraView}
      </>
    );
  }

  const spectatorStatus = spectatorSession?.status ?? getSpectatorStatusFromUrl();
  const spectatorView = (
    <SpectatorView
      status={spectatorStatus}
      streamCallId={spectatorSession?.streamCallId ?? null}
      streamVideoClient={spectatorClient}
    />
  );

  if (spectatorClient && spectatorSession) {
    return (
      <StreamVideo client={spectatorClient}>
        {spectatorError && (
          <div className="fixed left-0 right-0 top-0 bg-red-900/90 px-4 py-2 text-center text-sm text-white">
            {spectatorError}
          </div>
        )}
        {spectatorLoading && (
          <div className="fixed left-0 right-0 top-0 bg-black/80 px-4 py-2 text-center text-sm text-white">
            Loading session...
          </div>
        )}
        {spectatorView}
      </StreamVideo>
    );
  }

  return (
    <>
      {spectatorError && (
        <div className="fixed left-0 right-0 top-0 bg-red-900/90 px-4 py-2 text-center text-sm text-white">
          {spectatorError}
        </div>
      )}
      {spectatorLoading && spectatorSessionId && (
        <div className="fixed left-0 right-0 top-0 bg-black/80 px-4 py-2 text-center text-sm text-white">
          Loading session...
        </div>
      )}
      {spectatorView}
    </>
  );
}
