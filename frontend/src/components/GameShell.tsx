"use client";

import { useState } from "react";
import { useDeviceRole } from "@/src/hooks/useDeviceRole";
import { CameraView } from "@/src/components/game/CameraView";
import { SpectatorView } from "@/src/components/game/SpectatorView";
import { MOCK_SESSION_ID } from "@/src/mocks/sessionMocks";
import { isSessionStatus, type SessionStatus } from "@/src/types/session";

function getSpectatorStatusFromUrl(): SessionStatus {
  if (typeof window === "undefined") return "waiting";
  const p = new URL(window.location.href).searchParams.get("status");
  return isSessionStatus(p ?? "") ? p : "waiting";
}

export function GameShell() {
  const { role, isLoading } = useDeviceRole();
  const [cameraJoinUrl, setCameraJoinUrl] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-white">
        <p className="text-neutral-400">Detecting device...</p>
      </div>
    );
  }

  if (role === "camera") {
    return (
      <CameraView
        onStart={() => {
          // Sprint 1 demo: show mock join URL + QR. Sprint 2 will create real session.
          const origin =
            typeof window !== "undefined" ? window.location.origin : "";
          setCameraJoinUrl(`${origin}/game/${MOCK_SESSION_ID}`);
        }}
        joinUrl={cameraJoinUrl}
      />
    );
  }

  return <SpectatorView status={getSpectatorStatusFromUrl()} />;
}
