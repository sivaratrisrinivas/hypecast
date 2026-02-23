"use client";

type SpectatorViewProps = {
  /** Mock status for task 1.5; not wired to real session yet */
  status?: "waiting" | "live" | "processing";
};

export function SpectatorView({ status = "waiting" }: SpectatorViewProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <p className="mb-4 text-lg text-neutral-300">
        {status === "waiting" ? "Awaiting connection..." : status}
      </p>
      <p className="text-sm text-neutral-500">Mock timer: 0:00</p>
    </div>
  );
}
