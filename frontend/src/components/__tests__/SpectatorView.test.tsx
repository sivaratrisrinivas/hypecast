import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SpectatorView } from "../game/SpectatorView";

const mockRemoteParticipants: unknown[] = [];
vi.mock("@stream-io/video-react-sdk", async (importOriginal) => {
  const mod = await importOriginal();
  return {
    ...mod,
    useCallStateHooks: () => ({
      useRemoteParticipants: () => mockRemoteParticipants,
    }),
    ParticipantView: ({ className }: { className?: string }) => (
      <div data-testid="participant-view" className={className} />
    ),
  };
});

function createMockStreamVideoClient() {
  const join = vi.fn().mockResolvedValue(undefined);
  const leave = vi.fn().mockResolvedValue(undefined);
  const call = vi.fn(() => ({
    join,
    leave,
  }));
  return { mockClient: { call }, call, join, leave };
}

describe("SpectatorView", () => {
  beforeEach(() => {
    mockRemoteParticipants.length = 0;
  });

  it("shows Awaiting connection... when status is waiting", () => {
    render(<SpectatorView status="waiting" />);
    expect(screen.getByText("Awaiting connection...")).toBeInTheDocument();
    expect(screen.getByText("Mock timer: 0:00")).toBeInTheDocument();
  });

  it("shows Live when status is live", () => {
    render(<SpectatorView status="live" />);
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("shows Generating Reel when status is processing", () => {
    render(<SpectatorView status="processing" />);
    expect(screen.getByText("Generating Reel")).toBeInTheDocument();
  });

  it("defaults to waiting when status is not provided", () => {
    render(<SpectatorView />);
    expect(screen.getByText("Awaiting connection...")).toBeInTheDocument();
  });

  it("renders Stream ParticipantView when remote tracks exist", async () => {
    const { mockClient, call, join } = createMockStreamVideoClient();
    mockRemoteParticipants.push({
      sessionId: "remote-1",
      userId: "user-1",
      name: "Camera",
    });

    render(
      <SpectatorView
        status="live"
        streamCallId="test-call-id"
        streamVideoClient={mockClient as import("@stream-io/video-react-sdk").StreamVideoClient}
      />
    );

    await waitFor(() => {
      expect(call).toHaveBeenCalledWith("default", "test-call-id");
      expect(join).toHaveBeenCalledWith({ create: false, audio: false, video: false });
    });

    await waitFor(() => {
      expect(screen.queryByText("Waiting for stream...")).not.toBeInTheDocument();
    });

    expect(screen.getByTestId("participant-view")).toBeInTheDocument();
  });
});
