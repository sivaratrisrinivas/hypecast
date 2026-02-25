"""Frame capture pipeline: encode incoming video frames to WebM and upload to GCS."""

import io
import logging
from typing import Callable

import av
from av import VideoFrame

from vision_agents.core.processors import VideoProcessor
from vision_agents.core.utils.video_forwarder import VideoForwarder

logger = logging.getLogger(__name__)

# Target encoding for WebM (libvpx expects yuv420p)
WEBM_FPS = 15
WEBM_PIX_FMT = "yuv420p"


class FrameWriter:
    """
    Encodes av.VideoFrame instances to WebM in memory.
    Call add_frame() for each frame, then flush() to get bytes or write to a callback.
    """

    def __init__(self, *, fps: int = WEBM_FPS) -> None:
        self._fps = fps
        self._buffer = io.BytesIO()
        self._container: av.ContainerOutput | None = None
        self._stream: av.Stream | None = None
        self._frame_count = 0

    def _ensure_container(self, width: int, height: int) -> None:
        if self._container is not None:
            return
        self._container = av.open(self._buffer, "w", format="webm")
        self._stream = self._container.add_stream("libvpx", rate=self._fps)
        self._stream.width = width
        self._stream.height = height
        self._stream.pix_fmt = WEBM_PIX_FMT

    def add_frame(self, frame: VideoFrame) -> None:
        """Encode one frame into the WebM stream."""
        if frame.width <= 0 or frame.height <= 0:
            return
        self._ensure_container(frame.width, frame.height)
        # Reformat to yuv420p if needed (libvpx requirement)
        if frame.format and frame.format.name != WEBM_PIX_FMT:
            frame = frame.reformat(format=WEBM_PIX_FMT)
        assert self._stream is not None and self._container is not None
        for packet in self._stream.encode(frame):
            self._container.mux(packet)
        self._frame_count += 1

    def flush(self, upload_callback: Callable[[bytes], None] | None = None) -> bytes:
        """
        Flush the encoder, close the container, and return WebM bytes.
        If upload_callback is provided, call it with the bytes (e.g. to upload to GCS).
        """
        data = b""
        if self._container is not None and self._stream is not None:
            for packet in self._stream.encode():
                self._container.mux(packet)
            self._container.close()
            self._container = None
            self._stream = None
            data = self._buffer.getvalue()
            self._buffer = io.BytesIO()
        if data and upload_callback is not None:
            upload_callback(data)
        return data

    @property
    def frame_count(self) -> int:
        return self._frame_count


class FrameCaptureProcessor(VideoProcessor):
    """
    VideoProcessor that captures incoming WebRTC frames, encodes to raw.webm,
    and uploads to GCS at sessions/{session_id}/raw.webm.
    Set output blob path via set_output_blob_path() from join_call before frames arrive.
    """

    @property
    def name(self) -> str:
        return "frame-capture"

    def __init__(self, *, fps: int = WEBM_FPS) -> None:
        self._fps = fps
        self._output_blob_path: str | None = None
        self._writer: FrameWriter | None = None
        self._forwarder: VideoForwarder | None = None
        self._handler_added = False

    def set_output_blob_path(self, blob_path: str) -> None:
        """Set GCS blob path (e.g. sessions/{session_id}/raw.webm). Call from join_call."""
        self._output_blob_path = blob_path

    async def process_video(
        self,
        track: object,
        participant_id: str | None,
        shared_forwarder: VideoForwarder | None = None,
    ) -> None:
        if shared_forwarder is None:
            logger.warning("[frame_capture] No shared_forwarder; skipping capture.")
            return
        self._forwarder = shared_forwarder
        self._writer = FrameWriter(fps=self._fps)

        def on_frame(frame: VideoFrame) -> None:
            if self._writer is not None:
                self._writer.add_frame(frame)

        shared_forwarder.add_frame_handler(on_frame, fps=self._fps, name=self.name)
        self._handler_added = True
        logger.info("[frame_capture] Capturing frames to %s", self._output_blob_path or "(path not set)")

    async def stop_processing(self) -> None:
        if not self._handler_added or self._forwarder is None or self._writer is None:
            return
        # Flush and upload if path was set
        def upload(data: bytes) -> None:
            if self._output_blob_path:
                from services.gcs import upload_blob
                upload_blob(self._output_blob_path, data)  # noqa: PLC0415
                logger.info("[frame_capture] Uploaded %d bytes to %s", len(data), self._output_blob_path)

        self._writer.flush(upload_callback=upload)
        self._writer = None
        self._forwarder = None
        self._handler_added = False

    async def close(self) -> None:
        await self.stop_processing()
