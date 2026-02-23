import { renderHook, act } from "@testing-library/react";
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

  it("returns spectator on wide screens by default", () => {
    setViewportWidth(1200);

    const { result } = renderHook(() => useDeviceRole());

    // Run useEffect
    act(() => {});

    expect(result.current.isLoading).toBe(false);
    expect(result.current.role).toBe< DeviceRole >("spectator");
  });

  it("returns camera on narrow screens by default", () => {
    setViewportWidth(375);

    const { result } = renderHook(() => useDeviceRole());

    act(() => {});

    expect(result.current.isLoading).toBe(false);
    expect(result.current.role).toBe< DeviceRole >("camera");
  });

  it("prefers explicit role=camera from URL", () => {
    // @ts-expect-error - jsdom override
    window.location = new URL("https://example.com/game/abc?role=camera") as unknown as Location;
    setViewportWidth(1200); // would normally be spectator

    const { result } = renderHook(() => useDeviceRole());

    act(() => {});

    expect(result.current.isLoading).toBe(false);
    expect(result.current.role).toBe("camera");
  });

  it("prefers explicit role=spectator from URL", () => {
    // @ts-expect-error - jsdom override
    window.location = new URL("https://example.com/game/abc?role=spectator") as unknown as Location;
    setViewportWidth(375); // would normally be camera

    const { result } = renderHook(() => useDeviceRole());

    act(() => {});

    expect(result.current.isLoading).toBe(false);
    expect(result.current.role).toBe("spectator");
  });
});
