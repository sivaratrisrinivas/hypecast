import av
import numpy as np

from services.rfdetr_detection import RFDetrDetector


def _dummy_video_frame(width: int = 64, height: int = 64) -> av.VideoFrame:
    frame = av.VideoFrame(width, height, "rgb24")
    frame.planes[0].update(b"\x10" * (width * height * 3))
    return frame


class _FakeDetections:
    def __init__(self) -> None:
        self.xyxy = np.array([[1.0, 2.0, 30.0, 40.0], [5.0, 6.0, 10.0, 12.0]])
        self.class_id = np.array([0, 1])
        self.confidence = np.array([0.9, 0.7])


class _FakeModel:
    def predict(self, image, threshold: float = 0.5):  # noqa: ANN001
        assert threshold == 0.5
        assert isinstance(image, np.ndarray)
        return _FakeDetections()


def test_rfdetr_detector_emits_json_bounding_boxes() -> None:
    detector = RFDetrDetector(model=_FakeModel(), threshold=0.5, include_classes=["person"])
    # Avoid depending on rfdetr COCO constants in this unit test.
    detector._coco_classes = ["person", "sports ball"]  # type: ignore[attr-defined]

    payload = detector.detect_frame(_dummy_video_frame())
    assert "ts" in payload
    assert payload["frame"] == {"width": 64, "height": 64}
    assert isinstance(payload["detections"], list)

    # include_classes=["person"] should filter out the sports ball
    assert len(payload["detections"]) == 1
    det = payload["detections"][0]
    assert det["class"] == "person"
    assert det["confidence"] == 0.9
    assert det["bbox_xyxy"] == [1.0, 2.0, 30.0, 40.0]

