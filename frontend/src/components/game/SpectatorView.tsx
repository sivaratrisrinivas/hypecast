"use client";

import type { SessionStatus } from "@/types/session";

type SpectatorViewProps = {
  /** Mock status for task 1.5; not wired to real session yet */
  status?: SessionStatus;
};

const STATUS_LABELS: Record<SessionStatus, string> = {
  waiting: "Awaiting connection...",
  live: "Live",
  processing: "Generating Reel",
  completed: "Reel ready",
  error: "Something went wrong",
};

export function SpectatorView({ status = "waiting" }: SpectatorViewProps) {
  const label = STATUS_LABELS[status];
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <p className="mb-4 text-lg text-neutral-300">{label}</p>
      <p className="text-sm text-neutral-500">Mock timer: 0:00</p>
    </div>
  );
}
