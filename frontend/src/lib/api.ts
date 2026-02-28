import type { SessionCreateResponse, SessionReadResponse } from "@/src/types/session";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function createSession(): Promise<SessionCreateResponse> {
  const response = await fetch(`${API_BASE}/api/sessions`, { method: "POST" });
  if (!response.ok) throw new Error("Failed to create session");
  return response.json() as Promise<SessionCreateResponse>;
}

export async function getSession(sessionId: string): Promise<SessionReadResponse> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}`);
  if (!response.ok) throw new Error("Failed to fetch session");
  return response.json() as Promise<SessionReadResponse>;
}
