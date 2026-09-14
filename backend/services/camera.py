"""OpenCV camera capture for USB webcams, video files, and RTSP URLs."""

from __future__ import annotations

import logging
import sys
import threading
from typing import Optional

import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)


class CameraError(RuntimeError):
    """Raised when a camera or video source cannot be opened."""


def parse_camera_source(source) -> int | str:
    if source is None:
        return settings.parsed_camera_source()
    if isinstance(source, int):
        return source
    text = str(source).strip()
    if text.isdigit():
        return int(text)
    return text


class CameraService:
    """Thin wrapper around OpenCV VideoCapture with reconnect support."""

    def __init__(self, source=None, width: Optional[int] = None, height: Optional[int] = None):
        self.source = parse_camera_source(source)
        self.width = width if width is not None else settings.camera_width
        self.height = height if height is not None else settings.camera_height
        self._capture = None
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None
        self.connected = False
        self.frame_index = 0

    def open(self, source=None) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise CameraError("OpenCV is not installed. Install opencv-python.") from exc

        if source is not None:
            self.source = parse_camera_source(source)

        self.close()
        logger.info("Opening camera source: %s", self.source)
        capture = self._open_capture(cv2)
        if capture is None or not capture.isOpened():
            hint = ""
            if sys.platform == "darwin":
                hint = (
                    " On macOS, allow Camera access for Terminal or Cursor in "
                    "System Settings → Privacy & Security → Camera."
                )
            self.last_error = f"Unable to open camera source: {self.source}.{hint}"
            logger.error("%s", self.last_error)
            raise CameraError(self.last_error)

        if self.width:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        self._capture = capture
        self.connected = True
        self.last_error = None
        logger.info("Camera connected: source=%s", self.source)

    def _open_capture(self, cv2):
        source = self.source
        if isinstance(source, int):
            return self._open_device_index(cv2, source)
        capture = cv2.VideoCapture(source)
        if capture.isOpened():
            ok, frame = capture.read()
            if ok and frame is not None:
                return capture
            capture.release()
        return None

    def _open_device_index(self, cv2, index: int):
        backends = []
        if sys.platform == "darwin" and hasattr(cv2, "CAP_AVFOUNDATION"):
            backends.append(("AVFOUNDATION", cv2.CAP_AVFOUNDATION))
        backends.append(("ANY", cv2.CAP_ANY))

        candidates = [index]
        if index != 0:
            candidates.append(0)

        for candidate in candidates:
            for name, backend in backends:
                capture = cv2.VideoCapture(candidate, backend)
                if not capture.isOpened():
                    capture.release()
                    continue
                ok, frame = capture.read()
                if ok and frame is not None:
                    if candidate != index:
                        logger.warning(
                            "Camera index %s failed; using index %s (%s)",
                            index,
                            candidate,
                            name,
                        )
                        self.source = candidate
                    else:
                        logger.info("Opened camera index %s via %s", candidate, name)
                    return capture
                capture.release()
        return None

    def read(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._capture is None:
                return None
            ok, frame = self._capture.read()
        if not ok or frame is None:
            self.connected = False
            self.last_error = "Failed to read frame from camera source"
            logger.warning("%s", self.last_error)
            return None
        self.connected = True
        self.frame_index += 1
        return frame

    def close(self) -> None:
        with self._lock:
            if self._capture is not None:
                try:
                    self._capture.release()
                except Exception:
                    logger.exception("Error while releasing camera")
                self._capture = None
                self.connected = False
                logger.info("Camera released")
