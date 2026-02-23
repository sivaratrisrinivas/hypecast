import type { Session, SessionStatusResponse } from "@/types/session";
import type { CommentaryEntry } from "@/types/commentary";

export const MOCK_SESSION_ID = "demo-session";
export const MOCK_STREAM_CALL_ID = "pickup-demo-session";

export const mockSession: Session = {
  id: MOCK_SESSION_ID,
  streamCallId: MOCK_STREAM_CALL_ID,
  streamCallType: "default",
  status: "waiting",
  createdAt: new Date().toISOString(),
  endedAt: null,
  duration: 0,
  reelId: null,
  reelUrl: null,
};

export const mockSessionStatusLive: SessionStatusResponse = {
  status: "live",
  reelId: null,
  reelUrl: null,
};

export const mockCommentaryLog: CommentaryEntry[] = [
  {
    timestamp: 3,
    text: "And we're underway here with the opening possession.",
    energyLevel: 0.4,
    isHighlight: false,
  },
  {
    timestamp: 27,
    text: "UNBELIEVABLE crossover and finish at the rim!",
    energyLevel: 0.9,
    isHighlight: true,
  },
];
