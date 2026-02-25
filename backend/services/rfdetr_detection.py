from __future__ import annotations

import asyncio
import time
from typing import Any, Iterable

import numpy as np
from av import VideoFrame
from vision_agents.core.processors import VideoProcessor
from vision_agents.core.utils.video_forwarder import VideoForwarder

from services.detections_hub import detections_hub

_COCO_PERSON = "person"
_COCO_SPORTS_BALL = "sports ball"


def _load_coco_classes() -> list[str]:
    # Imported lazily so unit tests can run without importing rfdetr.
    from rfdetr.util.coco_classes import COCO_CLASSES  # noqa: PLC0415

    return list(COCO_CLASSES)


class RFDetrDetector:
    """
    Thin wrapper around an RF-DETR model to produce a stable JSON payload.

    The model is expected to implement `predict(image, threshold=...)` and return
    a supervision-like Detections object exposing:
      - xyxy: ndarray (N,4)
      - class_id: ndarray (N,)
      - confidence: ndarray (N,)
    """

    def __init__(
        self,
        *,
        model: Any | None = None,
        threshold: float = 0.5,
        include_classes: Iterable[str] | None = (_COCO_PERSON, _COCO_SPORTS_BALL),
    ) -> None:
        self._model = model
        self._threshold = threshold
        self._include_classes = set(include_classes) if include_classes is not None else None
        self._coco_classes: list[str] | None = None

    def _ensure_model(self) -> Any:
        if self._model is not None:
            return self._model
        # Local inference model (COCO-trained).
        from rfdetr import RFDETRMedium  # noqa: PLC0415

        self._model = RFDETRMedium()
        return self._model

    def _ensure_coco_classes(self) -> list[str]:
        if self._coco_classes is None:
            self._coco_classes = _load_coco_classes()
        return self._coco_classes

    def detect_frame(self, frame: VideoFrame) -> dict[str, Any]:
        # Convert to RGB array; rfdetr accepts np.ndarray or PIL.Image.
        rgb = frame.to_ndarray(format="rgb24")
        model = self._ensure_model()
        detections = model.predict(rgb, threshold=self._threshold)

        xyxy = np.asarray(getattr(detections, "xyxy"))
        class_id = np.asarray(getattr(detections, "class_id"))
        confidence = np.asarray(getattr(detections, "confidence"))

        coco = self._ensure_coco_classes()

        items: list[dict[str, Any]] = []
        for i in range(int(xyxy.shape[0])):
            cls_idx = int(class_id[i]) if i < class_id.shape[0] else -1
            cls_name = coco[cls_idx] if 0 <= cls_idx < len(coco) else "unknown"
            if self._include_classes is not None and cls_name not in self._include_classes:
                continue
            conf = float(confidence[i]) if i < confidence.shape[0] else 0.0
            x1, y1, x2, y2 = (float(v) for v in xyxy[i].tolist())
            items.append(
                {
                    "class": cls_name,
                    "confidence": conf,
                    "bbox_xyxy": [x1, y1, x2, y2],
                }
            )

        return {
            "ts": time.time(),
            "frame": {"width": int(frame.width or 0), "height": int(frame.height or 0)},
            "detections": items,
        }


class RFDetrDetectionProcessor(VideoProcessor):
    @property
    def name(self) -> str:
        return "rfdetr-detection"

    def __init__(
        self,
        *,
        fps: int = 5,
        threshold: float = 0.5,
        model: Any | None = None,
    ) -> None:
        self._fps = fps
        self._detector = RFDetrDetector(model=model, threshold=threshold)
        self._forwarder: VideoForwarder | None = None
        self._handler_added = False
        self._frame_q: asyncio.Queue[VideoFrame] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._session_id: str | None = None
        self._latest_payload: dict[str, Any] | None = None

    def set_session_id(self, session_id: str) -> None:
        self._session_id = session_id

    async def process_video(
        self,
        track: object,
        participant_id: str | None,
        shared_forwarder: VideoForwarder | None = None,
    ) -> None:
        if shared_forwarder is None:
            return
        self._forwarder = shared_forwarder
        self._frame_q = asyncio.Queue(maxsize=1)

        def on_frame(frame: VideoFrame) -> None:
            if self._frame_q is None:
                return
            if self._frame_q.full():
                try:
                    _ = self._frame_q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                self._frame_q.put_nowait(frame)
            except asyncio.QueueFull:
                pass

        shared_forwarder.add_frame_handler(on_frame, fps=self._fps, name=self.name)
        self._handler_added = True
        self._worker = asyncio.create_task(self._run())

    async def _run(self) -> None:
        assert self._frame_q is not None
        while True:
            frame = await self._frame_q.get()
            session_id = self._session_id
            if not session_id:
                continue
            payload = self._detector.detect_frame(frame)
            # Cache latest detections so the Vision Agents `Agent` can expose them
            # to the LLM as processor state (frames + Roboflow labels in-context).
            self._latest_payload = payload
            await detections_hub.publish(session_id, payload)

    def state(self) -> dict[str, Any] | None:  # pragma: no cover - trivial getter
        """
        Expose the latest detection payload to the Agent.

        Vision Agents passes each processor's state into the LLM context, which
        lets Gemini commentary reason about structured Roboflow labels in
        addition to raw video frames.
        """
        return self._latest_payload

    async def stop_processing(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None
        self._frame_q = None
        self._forwarder = None
        self._handler_added = False

    async def close(self) -> None:
        await self.stop_processing()

