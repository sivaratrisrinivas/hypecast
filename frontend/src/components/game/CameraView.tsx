"use client";

type CameraViewProps = {
  onStart: () => void;
};

export function CameraView({ onStart }: CameraViewProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <div
        aria-label="Camera preview"
        className="mb-8 flex h-64 w-40 items-center justify-center rounded-xl border border-dashed border-neutral-500 bg-neutral-900/60"
      >
        <span className="text-sm text-neutral-400">Camera inactive</span>
      </div>

      <button
        type="button"
        onClick={onStart}
        className="rounded-full bg-emerald-500 px-10 py-3 text-lg font-bold uppercase tracking-wide text-black"
      >
        Start
      </button>
    </div>
  );
}
