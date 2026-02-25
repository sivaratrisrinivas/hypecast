"""Tests for frame capture pipeline (Sprint 3.4): dummy frames → flush to mock upload buffer."""

import av

from services.frame_capture import FrameWriter


def _dummy_video_frame(width: int = 64, height: int = 64) -> av.VideoFrame:
    """Create a minimal av.VideoFrame for testing (no numpy)."""
    frame = av.VideoFrame(width, height, "rgb24")
    frame.planes[0].update(b"\x80" * (width * height * 3))
    return frame


def test_frame_writer_flushes_to_mock_upload_buffer() -> None:
    """Pass dummy frames to the capture function; verify flush writes to mock upload buffer."""
    writer = FrameWriter(fps=15)
    upload_buffer: list[bytes] = []

    def mock_upload(data: bytes) -> None:
        upload_buffer.append(data)

    # No frames: flush returns empty, callback not called
    writer.flush(upload_callback=mock_upload)
    assert upload_buffer == []

    # Add dummy frames
    for _ in range(3):
        writer.add_frame(_dummy_video_frame())
    assert writer.frame_count == 3

    # Flush: should encode WebM and call mock with non-empty bytes
    writer.flush(upload_callback=mock_upload)
    assert len(upload_buffer) == 1
    assert len(upload_buffer[0]) > 0
    # WebM magic (0x1A 0x45 0xDF 0xA3)
    assert upload_buffer[0][:4] == b"\x1a\x45\xdf\xa3"


def test_frame_writer_flush_returns_bytes_without_callback() -> None:
    """Flush without callback returns WebM bytes."""
    writer = FrameWriter(fps=15)
    writer.add_frame(_dummy_video_frame())
    data = writer.flush()
    assert len(data) > 0
    assert data[:4] == b"\x1a\x45\xdf\xa3"


def test_frame_writer_single_frame_produces_webm() -> None:
    """Single frame still encodes to valid WebM."""
    writer = FrameWriter(fps=15)
    writer.add_frame(_dummy_video_frame(64, 64))
    data = writer.flush()
    assert len(data) > 0
    assert data[:4] == b"\x1a\x45\xdf\xa3"
