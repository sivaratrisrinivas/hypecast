"use client";

import { QRCodeSVG } from "qrcode.react";

type CameraViewProps = {
  onStart: () => void;
  /** When set, show mock join URL and QR (Sprint 1 demo). */
  joinUrl?: string | null;
};

export function CameraView({ onStart, joinUrl }: CameraViewProps) {
  const showJoinInfo = Boolean(joinUrl);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <div
        aria-label="Camera preview"
        className="mb-8 flex h-64 w-40 items-center justify-center rounded-xl border border-dashed border-neutral-500 bg-neutral-900/60"
      >
        <span className="text-sm text-neutral-400">
          {showJoinInfo ? "Streaming" : "Camera inactive"}
        </span>
      </div>

      {showJoinInfo ? (
        <div className="flex flex-col items-center gap-4">
          <p className="text-sm text-neutral-400">Open this link on your laptop</p>
          <a
            href={joinUrl ?? "#"}
            className="break-all text-emerald-400 underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {joinUrl}
          </a>
          <div className="rounded-lg bg-white p-3">
            <QRCodeSVG value={joinUrl ?? ""} size={160} level="M" />
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={onStart}
          className="rounded-full bg-emerald-500 px-10 py-3 text-lg font-bold uppercase tracking-wide text-black"
        >
          Start
        </button>
      )}
    </div>
  );
}
