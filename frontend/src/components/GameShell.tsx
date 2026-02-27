"use client";

import { useEffect, useMemo, useRef } from "react";
import { StreamVideo, StreamVideoClient } from "@stream-io/video-react-sdk";
import { useDeviceRole } from "@/src/hooks/useDeviceRole";
import { useSession } from "@/src/hooks/useSession";
import { useSpectatorSession } from "@/src/hooks/useSpectatorSession";
import { CameraView } from "@/src/components/game/CameraView";
import { SpectatorView } from "@/src/components/game/SpectatorView";
import { isSessionStatus, type SessionStatus } from "@/src/types/session";

const GEMINI_MODEL =
  process.env.NEXT_PUBLIC_GEMINI_MODEL ?? "gemini-3-flash-preview";

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
  useEffect(() => {
    console.log("[GameShell] mount", {
      spectatorSessionId,
      hasStreamKey: Boolean(process.env.NEXT_PUBLIC_STREAM_API_KEY),
    });
    return () => console.log("[GameShell] unmount");
  }, [spectatorSessionId]);

  const { role, isLoading } = useDeviceRole({
    // Any explicit /game/[sessionId] route is a spectator join flow.
    initialRoleParam: spectatorSessionId ? "spectator" : null,
  });
  const resolvedRole = spectatorSessionId ? "spectator" : role;
  const { session, createSession, error: sessionError, isCreating } = useSession();
  const {
    session: spectatorSession,
    error: spectatorError,
    isLoading: spectatorLoading,
  } = useSpectatorSession(spectatorSessionId ?? null);

  const sessionId = session?.sessionId ?? null;
  const streamToken = session?.streamToken ?? null;

  useEffect(() => {
    console.log("[GameShell] session state", {
      sessionId,
      spectatorSessionId,
      spectatorSession: spectatorSession
        ? {
            streamCallId: spectatorSession.streamCallId,
            status: spectatorSession.status,
          }
        : null,
      sessionError,
      spectatorError,
    });
  }, [
    sessionId,
    spectatorSessionId,
    spectatorSession,
    sessionError,
    spectatorError,
  ]);

  const streamClient = useMemo(() => {
    if (!sessionId || !streamToken || typeof window === "undefined" || !STREAM_API_KEY) {
      return null;
    }
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
      return null;
    }
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
      <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
        <p className="text-neutral-400">Detecting device...</p>
        <p className="mt-4 text-xs text-neutral-600">
          Powered by {GEMINI_MODEL}
        </p>
      </div>
    );
  }

  if (resolvedRole === "camera") {
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
      streamCallId={spectatorCallId}
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
