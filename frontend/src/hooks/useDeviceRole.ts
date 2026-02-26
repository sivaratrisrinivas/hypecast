"use client";

import { useEffect, useState } from "react";
import type { DeviceRole } from "@/src/types/session";

type UseDeviceRoleResult = {
  role: DeviceRole | null;
  isLoading: boolean;
};

type DetectionOptions = {
  /**
   * Optional explicit role override from URL, e.g. ?role=camera|spectator
   */
  initialRoleParam?: string | null;
};

/**
 * Heuristics:
 * 1. If URL role param is present and valid -> use it.
 * 2. Else, if viewport is narrow (<= 768px) -> "camera".
 * 3. Else -> "spectator".
 */
export function useDeviceRole(options?: DetectionOptions): UseDeviceRoleResult {
  const [role, setRole] = useState<DeviceRole | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Guard against SSR / non-browser environments
    if (typeof window === "undefined" || typeof navigator === "undefined") {
      return;
    }

    let resolvedRole: DeviceRole | null = null;

    // 1. URL param override
    const url = new URL(window.location.href);
    const paramRole = options?.initialRoleParam ?? url.searchParams.get("role");
    if (paramRole === "camera" || paramRole === "spectator") {
      resolvedRole = paramRole;
    }

    // 1.5 Route override: /game/[sessionId] is always spectator join flow.
    // This prevents narrow devices from falling back to camera UI when opening
    // a shared join URL.
    if (!resolvedRole && /^\/game\/[^/]+/.test(url.pathname)) {
      resolvedRole = "spectator";
    }

    // 2. Screen-width heuristic if not set yet
    if (!resolvedRole) {
      const width = window.innerWidth || document.documentElement.clientWidth;
      if (width <= 768) {
        resolvedRole = "camera";
      } else {
        resolvedRole = "spectator";
      }
    }

    queueMicrotask(() => {
      setRole(resolvedRole);
      setIsLoading(false);
    });
  }, [options?.initialRoleParam]);

  return { role, isLoading };
}
