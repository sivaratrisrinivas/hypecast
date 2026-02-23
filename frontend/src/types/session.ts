export type SessionStatus = "waiting" | "live" | "processing" | "completed" | "error";
export type DeviceRole = "camera" | "spectator";

export const SESSION_STATUSES: readonly SessionStatus[] = [
  "waiting",
  "live",
  "processing",
  "completed",
  "error",
] as const;

export function isSessionStatus(s: string): s is SessionStatus {
  return (SESSION_STATUSES as readonly string[]).includes(s);
}

export interface Session {
  id: string;                 // nanoid, e.g. "abc123"
  streamCallId: string;       // Stream call ID bound to this session
  streamCallType: string;     // "default"
  status: SessionStatus;
  createdAt: string;          // ISO 8601
  endedAt: string | null;
  duration: number;           // seconds elapsed
  reelId: string | null;      // populated after reel generation
  reelUrl: string | null;     // 48h signed GCS URL
}

export interface SessionCreateResponse {
  sessionId: string;
  streamCallId: string;
  streamToken: string;        // user-scoped JWT for Stream SDK
  joinUrl: string;            // /game/{sessionId}
}

export interface SessionStatusResponse {
  status: SessionStatus;
  reelId: string | null;
  reelUrl: string | null;
}
