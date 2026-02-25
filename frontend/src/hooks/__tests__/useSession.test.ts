import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSession } from "../useSession";

const BASE = "http://localhost:8000";

describe("useSession", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("AbortController", class AbortController {
      signal = { aborted: false };
      abort = vi.fn(() => { (this.signal as { aborted: boolean }).aborted = true; });
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("createSession POSTs /api/sessions and sets session with status waiting", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          session_id: "sid-1",
          stream_call_id: "pickup-sid-1",
          stream_token: "token-1",
          join_url: "/game/sid-1",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      })
      .mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ status: "waiting", reel_id: null, reel_url: null }),
      });

    const { result } = renderHook(() => useSession());

    await act(async () => {
      result.current.createSession();
    });

    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/api/sessions`, { method: "POST" });
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/sessions`,
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          call_type: "default",
          call_id: "pickup-sid-1",
        }),
      })
    );
    expect(result.current.session).not.toBeNull();
    expect(result.current.session?.status).toBe("waiting");
    expect(result.current.session?.sessionId).toBe("sid-1");
    expect(result.current.session?.streamCallId).toBe("pickup-sid-1");
    expect(result.current.session?.joinUrl).toBe("/game/sid-1");
    expect(result.current.isCreating).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("after create, polling GET updates state from waiting to live", async () => {
    vi.useRealTimers();
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          session_id: "sid-2",
          stream_call_id: "pickup-sid-2",
          stream_token: "t",
          join_url: "/game/sid-2",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
      })
      .mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ status: "live", reel_id: null, reel_url: null }),
      });

    const { result } = renderHook(() => useSession());

    await act(async () => {
      result.current.createSession();
    });

    await waitFor(
      () => {
        expect(result.current.session?.status).toBe("live");
      },
      { timeout: 2000 }
    );

    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/api/sessions/sid-2`,
      expect.objectContaining({ signal: expect.any(Object) })
    );
    vi.useFakeTimers();
  });

  it("createSession sets error when POST fails", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      text: async () => "Service Unavailable",
    });

    const { result } = renderHook(() => useSession());

    await act(async () => {
      result.current.createSession();
    });

    expect(result.current.session).toBeNull();
    expect(result.current.error).toBe("Service Unavailable");
    expect(result.current.isCreating).toBe(false);
  });
});
