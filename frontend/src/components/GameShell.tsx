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
  return isSessionStatus(p ?? "") ? (p as SessionStatus) : "waiting";
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

  const sessionId = session?.sessionId ?? null;
  const streamToken = session?.streamToken ?? null;

  const streamClient = useMemo(() => {
    if (!sessionId || !streamToken || typeof window === "undefined" || !STREAM_API_KEY) {
      console.log("[GameShell] streamClient: not creating (sessionId:", !!sessionId, "STREAM_API_KEY:", !!STREAM_API_KEY, ")");
      return null;
    }
    console.log("[GameShell] Creating StreamVideoClient for camera user:", `camera-${sessionId}`);
    return StreamVideoClient.getOrCreateInstance({
      apiKey: STREAM_API_KEY,
      user: { id: `camera-${sessionId}` },
      token: streamToken,
    });
  }, [sessionId, streamToken]);

  const spectatorUserId = spectatorSession?.userId ?? null;
  const spectatorToken = spectatorSession?.streamToken ?? null;
  const spectatorCallId = spectatorSession?.streamCallId ?? null;

  const spectatorClient = useMemo(() => {
    if (!spectatorUserId || !spectatorToken || typeof window === "undefined" || !STREAM_API_KEY) {
      console.log("[GameShell] spectatorClient: not creating (spectatorUserId:", !!spectatorUserId, "STREAM_API_KEY:", !!STREAM_API_KEY, ")");
      return null;
    }
    console.log("[GameShell] Creating StreamVideoClient for spectator user:", spectatorUserId, "callId:", spectatorCallId);
    return StreamVideoClient.getOrCreateInstance({
      apiKey: STREAM_API_KEY,
      user: { id: spectatorUserId },
      token: spectatorToken,
    });
  }, [spectatorUserId, spectatorToken]);

  const cameraClientRef = useRef<StreamVideoClient | null>(null);
  useEffect(() => {
    if (!streamClient) return;
    const prev = cameraClientRef.current;
    if (prev && prev !== streamClient) {
      prev.disconnectUser().catch(() => { });
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
      prev.disconnectUser().catch(() => { });
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
    console.log("[GameShell] Rendering CAMERA view. session:", !!session, "streamClient:", !!streamClient, "streamCallId:", session?.streamCallId);
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

  console.log("[GameShell] Rendering SPECTATOR view. spectatorSessionId:", spectatorSessionId, "spectatorSession:", !!spectatorSession, "spectatorClient:", !!spectatorClient, "spectatorStatus:", spectatorSession?.status);
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
