export type SessionStatus = "waiting" | "live" | "processing" | "completed" | "error";

export interface SessionCreateResponse {
  session_id: string;
  join_url: string;
}

export interface SessionReadResponse {
  session_id: string;
  status: SessionStatus;
}
