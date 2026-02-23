import { describe, it, expect } from "vitest";
import {
  SESSION_STATUSES,
  isSessionStatus,
  type SessionStatus,
} from "../session";

describe("SessionStatus typing", () => {
  it("accepts all valid SessionStatus values", () => {
    const valid: SessionStatus[] = [
      "waiting",
      "live",
      "processing",
      "completed",
      "error",
    ];
    valid.forEach((s) => {
      expect(isSessionStatus(s)).toBe(true);
      expect(SESSION_STATUSES).toContain(s);
    });
  });

  it("rejects invalid status strings", () => {
    expect(isSessionStatus("invalid")).toBe(false);
    expect(isSessionStatus("")).toBe(false);
    expect(isSessionStatus("pending")).toBe(false);
    expect(isSessionStatus("WAITING")).toBe(false);
  });
});
