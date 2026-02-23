import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SpectatorView } from "../game/SpectatorView";

describe("SpectatorView", () => {
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
});
