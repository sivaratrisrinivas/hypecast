import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CameraView } from "../game/CameraView";

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
});
