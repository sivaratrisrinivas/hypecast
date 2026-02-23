"use client";

import { useDeviceRole } from "@/src/hooks/useDeviceRole";
import { CameraView } from "@/src/components/game/CameraView";
import { SpectatorView } from "@/src/components/game/SpectatorView";

export function GameShell() {
  const { role, isLoading } = useDeviceRole();

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
          // TODO Sprint 2: start session / stream
          console.log("START clicked");
        }}
      />
    );
  }

  return <SpectatorView status="waiting" />;
}
