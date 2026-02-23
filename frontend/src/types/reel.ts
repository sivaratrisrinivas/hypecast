export interface Reel {
  id: string;                 // nanoid
  sessionId: string;
  url: string;                // signed GCS URL
  expiresAt: string;          // ISO 8601, 48h from creation
  durationSeconds: number;    // 30–60s
  highlightCount: number;     // 3–5
  createdAt: string;
}

export interface ReelViewerData {
  reel: Reel;
  expired: boolean;
  gameDate: string;           // formatted display date
}
