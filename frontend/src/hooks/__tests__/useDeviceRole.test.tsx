import { renderHook, waitFor } from "@testing-library/react";
import { useDeviceRole } from "../useDeviceRole";
import type { DeviceRole } from "@/types/session";

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
}

describe("useDeviceRole", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    // Reset location for each test
    // @ts-expect-error - jsdom override
    delete window.location;
    // @ts-expect-error - jsdom override
    window.location = new URL("https://example.com/") as unknown as Location;

    setViewportWidth(1024);
  });

  afterAll(() => {
    // @ts-expect-error - restore
    window.location = originalLocation;
  });

  it("returns spectator on wide screens by default", async () => {
    setViewportWidth(1200);

    const { result } = renderHook(() => useDeviceRole());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.role).toBe< DeviceRole >("spectator");
  });

  it("returns camera on narrow screens by default", async () => {
    setViewportWidth(375);

    const { result } = renderHook(() => useDeviceRole());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.role).toBe< DeviceRole >("camera");
  });

  it("prefers explicit role=camera from URL", async () => {
    // @ts-expect-error - jsdom override
    window.location = new URL("https://example.com/game/abc?role=camera") as unknown as Location;
    setViewportWidth(1200); // would normally be spectator

    const { result } = renderHook(() => useDeviceRole());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.role).toBe("camera");
  });

  it("prefers explicit role=spectator from URL", async () => {
    // @ts-expect-error - jsdom override
    window.location = new URL("https://example.com/game/abc?role=spectator") as unknown as Location;
    setViewportWidth(375); // would normally be camera

    const { result } = renderHook(() => useDeviceRole());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.role).toBe("spectator");
  });

  it("uses initialRoleParam override when provided", async () => {
    setViewportWidth(375); // would normally resolve to camera

    const { result } = renderHook(() =>
      useDeviceRole({ initialRoleParam: "spectator" }),
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.role).toBe("spectator");
  });

  it("forces spectator on /game/[sessionId] route without role param", async () => {
    // @ts-expect-error - jsdom override
    window.location = new URL("https://example.com/game/abc123") as unknown as Location;
    setViewportWidth(375); // would normally be camera

    const { result } = renderHook(() => useDeviceRole());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    expect(result.current.role).toBe("spectator");
  });
});
