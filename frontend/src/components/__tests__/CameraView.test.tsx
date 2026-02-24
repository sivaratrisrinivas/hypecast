import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CameraView } from "../game/CameraView";

function createMockStreamVideoClient() {
  const join = vi.fn().mockResolvedValue(undefined);
  const leave = vi.fn().mockResolvedValue(undefined);
  const cameraEnable = vi.fn().mockResolvedValue(undefined);
  const microphoneEnable = vi.fn().mockResolvedValue(undefined);

  const call = vi.fn(() => ({
    join,
    leave,
    camera: { enable: cameraEnable },
    microphone: { enable: microphoneEnable },
  }));

  const mockClient = { call };
  return {
    mockClient,
    call,
    join,
    leave,
    cameraEnable,
    microphoneEnable,
  };
}

describe("CameraView", () => {
  it("renders a START button", () => {
    const onStart = vi.fn();

    render(<CameraView onStart={onStart} />);

    const button = screen.getByRole("button", { name: /start/i });
    expect(button).toBeInTheDocument();
  });

  it("calls onStart when START is clicked", () => {
    const onStart = vi.fn();

    render(<CameraView onStart={onStart} />);

    const button = screen.getByRole("button", { name: /start/i });
    fireEvent.click(button);

    expect(onStart).toHaveBeenCalledTimes(1);
  });

  it("shows mock join URL and QR when joinUrl is set", () => {
    render(
      <CameraView onStart={vi.fn()} joinUrl="https://example.com/game/abc123" />
    );

    expect(screen.queryByRole("button", { name: /start/i })).not.toBeInTheDocument();
    expect(screen.getByText("https://example.com/game/abc123")).toBeInTheDocument();
    expect(screen.getByText(/open this link on your laptop/i)).toBeInTheDocument();
  });

  it("joins Stream call with create: true and enables camera when streamVideoClient and streamCallId are provided", async () => {
    const { mockClient, call, join, cameraEnable } =
      createMockStreamVideoClient();

    render(
      <CameraView
        onStart={vi.fn()}
        streamVideoClient={mockClient as import("@stream-io/video-react-sdk").StreamVideoClient}
        streamCallId="test-call-id"
      />
    );

    await waitFor(() => {
      expect(call).toHaveBeenCalledWith("default", "test-call-id");
    });
    expect(cameraEnable).toHaveBeenCalled();
    expect(join).toHaveBeenCalledWith({ create: true });
  });
});
