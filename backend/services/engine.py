"""Background camera processing engine and annotated MJPEG frames."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import numpy as np

from backend.config import settings
from backend.schemas import LiveOverlay, LiveStatus
from backend.services.camera import CameraError, CameraService
from backend.services.pipeline import ANPRPipeline

logger = logging.getLogger(__name__)


class ANPREngine:
    def __init__(self) -> None:
        self.camera = CameraService()
        self.pipeline = ANPRPipeline()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._models_thread: Optional[threading.Thread] = None
        self._detect_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._annotated: Optional[np.ndarray] = None
        self._raw: Optional[np.ndarray] = None
        self._overlays: list[LiveOverlay] = []
        self._fps = 0.0
        self._last_error: Optional[str] = None
        self.started = False
        self.models_loading = False

    def start(self, source=None) -> None:
        logger.info("Starting ANPR engine")
        try:
            self.camera.open(source)
            self._last_error = None
        except CameraError as exc:
            self._last_error = str(exc)
            logger.error("Camera unavailable: %s", exc)

        self._ensure_models_loading()
        if self.running:
            return
        self.running = True
        self.started = True
        self.thread = threading.Thread(target=self._loop, name="anpr-engine", daemon=True)
        self.thread.start()
        self._detect_thread = threading.Thread(target=self._detect_loop, name="anpr-detect", daemon=True)
        self._detect_thread.start()

    def _ensure_models_loading(self) -> None:
        if self.pipeline.vehicle_detector.model is not None:
            return
        if self._models_thread and self._models_thread.is_alive():
            return

        def _load() -> None:
            self.models_loading = True
            try:
                self.pipeline.load()
            finally:
                self.models_loading = False

        self._models_thread = threading.Thread(target=_load, name="anpr-models", daemon=True)
        self._models_thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self._detect_thread and self._detect_thread.is_alive():
            self._detect_thread.join(timeout=2.0)
        self.camera.close()
        logger.info("ANPR engine stopped")

    def get_annotated_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._annotated is None:
                return None
            return self._annotated.copy()

    def status(self) -> LiveStatus:
        return LiveStatus(
            camera_connected=self.camera.connected,
            fps=round(self._fps, 2),
            frame_index=self.camera.frame_index,
            last_error=self._last_error or self.camera.last_error,
            overlays=list(self._overlays),
            engine_running=self.running,
            models_loading=self.models_loading,
            source=str(self.camera.source),
        )

    def process_still(self, frame: np.ndarray, persist: bool = True):
        return self.pipeline.process_frame(frame, persist=persist)

    def _loop(self) -> None:
        processed = 0
        stamp = time.time()
        while self.running:
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.2)
                if not self.camera.connected:
                    self._reconnect()
                continue

            with self._lock:
                self._raw = frame
                overlays = list(self._overlays)
            annotated = annotate_frame(frame, overlays)
            with self._lock:
                self._annotated = annotated

            processed += 1
            now = time.time()
            if now - stamp >= 1.0:
                self._fps = processed / (now - stamp)
                processed = 0
                stamp = now

    def _detect_loop(self) -> None:
        while self.running:
            with self._lock:
                frame = None if self._raw is None else self._raw.copy()
            if frame is None:
                time.sleep(0.05)
                continue
            try:
                result = self.pipeline.process_frame(frame, persist=True)
                overlays = result.overlays
            except Exception:
                logger.exception("Pipeline crashed on a frame; continuing")
                overlays = []
            with self._lock:
                self._overlays = overlays
            time.sleep(0.03 * max(1, settings.process_every_n_frames))

    def _reconnect(self) -> None:
        try:
            logger.info("Attempting camera reconnect")
            self.camera.open()
            self._last_error = None
        except CameraError as exc:
            self._last_error = str(exc)
            time.sleep(1.0)


engine = ANPREngine()


def annotate_frame(frame: np.ndarray, overlays: list[LiveOverlay]) -> np.ndarray:
    try:
        import cv2
    except ImportError:
        return frame

    canvas = frame.copy()
    frame_area = max(1, canvas.shape[0] * canvas.shape[1])
    for overlay in overlays:
        box = overlay.vehicle_box
        box_area = max(0, (box.x2 - box.x1) * (box.y2 - box.y1))
        if box_area < 0.8 * frame_area:
            cv2.rectangle(canvas, (box.x1, box.y1), (box.x2, box.y2), (34, 211, 238), 2)
            label = f"{overlay.vehicle_type} {overlay.vehicle_confidence:.2f}"
            if overlay.track_id is not None:
                label = f"ID {overlay.track_id} | {label}"
            _draw_label(cv2, canvas, box.x1, max(0, box.y1 - 8), label, (34, 211, 238))

        if overlay.plate_box:
            pbox = overlay.plate_box
            cv2.rectangle(canvas, (pbox.x1, pbox.y1), (pbox.x2, pbox.y2), (251, 191, 36), 2)
            plate_label = overlay.plate_number or "plate"
            if overlay.ocr_confidence is not None:
                plate_label = f"{plate_label} ({overlay.ocr_confidence:.2f})"
            _draw_label(cv2, canvas, pbox.x1, pbox.y2 + 18, plate_label, (251, 191, 36))
    return canvas


def _draw_label(cv2, canvas, x, y, text, color) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.55
    thickness = 1
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    y1 = max(0, y - th - 6)
    x2 = min(canvas.shape[1] - 1, x + tw + 8)
    y2 = min(canvas.shape[0] - 1, y + 4)
    cv2.rectangle(canvas, (x, y1), (x2, y2), (15, 23, 42), -1)
    cv2.putText(canvas, text, (x + 4, y), font, scale, color, thickness, cv2.LINE_AA)


def placeholder_frame(message: str) -> np.ndarray:
    try:
        import cv2
    except ImportError:
        return np.zeros((360, 640, 3), dtype=np.uint8)
    canvas = np.zeros((360, 640, 3), dtype=np.uint8)
    canvas[:] = (15, 23, 42)
    cv2.putText(
        canvas,
        "ANPR LIVE FEED",
        (40, 140),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (34, 211, 238),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        message[:70],
        (40, 200),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (226, 232, 240),
        1,
        cv2.LINE_AA,
    )
    return canvas
