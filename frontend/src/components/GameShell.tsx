"use client";

import { useMemo } from "react";
import { StreamVideo, StreamVideoClient } from "@stream-io/video-react-sdk";
import { useDeviceRole } from "@/src/hooks/useDeviceRole";
import { useSession } from "@/src/hooks/useSession";
import { CameraView } from "@/src/components/game/CameraView";
import { SpectatorView } from "@/src/components/game/SpectatorView";
import { isSessionStatus, type SessionStatus } from "@/src/types/session";

function getSpectatorStatusFromUrl(): SessionStatus {
  if (typeof window === "undefined") return "waiting";
  const p = new URL(window.location.href).searchParams.get("status");
  return isSessionStatus(p ?? "") ? p : "waiting";
}

const STREAM_API_KEY = process.env.NEXT_PUBLIC_STREAM_API_KEY ?? "";

export function GameShell() {
  const { role, isLoading } = useDeviceRole();
  const { session, createSession, error: sessionError, isCreating } = useSession();

  const streamClient = useMemo(() => {
    if (!session || typeof window === "undefined" || !STREAM_API_KEY) return null;
    return new StreamVideoClient({
      apiKey: STREAM_API_KEY,
      user: { id: `camera-${session.sessionId}` },
      token: session.streamToken,
    });
  }, [session]);

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

  return <SpectatorView status={getSpectatorStatusFromUrl()} />;
}
