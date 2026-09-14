"""Number-plate detection on a vehicle crop."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.config import settings
from backend.utils.geometry import BBox

logger = logging.getLogger(__name__)


@dataclass
class PlateDetectionResult:
    bbox: BBox
    confidence: float
    source: str


class PlateDetector:
    """YOLO plate detector with an optional OpenCV morphological fallback."""

    def __init__(self) -> None:
        self.model = None
        self.status = "unloaded"
        self.detail: Optional[str] = None
        self.using_fallback = False

    def load(self) -> None:
        custom_path = settings.resolved_plate_model_path
        if custom_path.exists():
            try:
                from ultralytics import YOLO

                logger.info("Loading plate model from %s", custom_path)
                self.model = YOLO(str(custom_path))
                self.status = "loaded"
                self.using_fallback = False
                self.detail = str(custom_path)
                return
            except Exception:
                logger.exception("Failed to load custom plate model at %s", custom_path)

        message = (
            f"Plate model not found at {custom_path}. "
            "Train one with training/train.py or place plate_model.pt in models/."
        )
        if settings.allow_opencv_plate_fallback:
            logger.warning("%s Using OpenCV plate-candidate fallback.", message)
            self.status = "opencv_fallback"
            self.using_fallback = True
            self.detail = "opencv_morphology"
            return

        self.status = "missing"
        self.detail = message
        logger.error("%s", message)

    def detect(self, vehicle_crop: np.ndarray) -> list[PlateDetectionResult]:
        if vehicle_crop is None or vehicle_crop.size == 0:
            return []
        if self.model is not None:
            plates = self._detect_yolo(vehicle_crop)
            if plates:
                return plates
            if not settings.allow_opencv_plate_fallback:
                return []
        if self.status in {"opencv_fallback", "loaded"} and settings.allow_opencv_plate_fallback:
            return self._detect_opencv(vehicle_crop)
        return []

    def _detect_yolo(self, vehicle_crop: np.ndarray) -> list[PlateDetectionResult]:
        try:
            results = self.model.predict(
                vehicle_crop,
                conf=settings.plate_confidence,
                verbose=False,
            )
        except Exception:
            logger.exception("YOLO plate detection failed")
            return []

        detections: list[PlateDetectionResult] = []
        if not results:
            return detections
        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return detections

        height, width = vehicle_crop.shape[:2]
        for box in boxes:
            try:
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                bbox = BBox(
                    x1=int(xyxy[0]),
                    y1=int(xyxy[1]),
                    x2=int(xyxy[2]),
                    y2=int(xyxy[3]),
                ).clip(width, height)
                if not _looks_like_plate(bbox, width, height):
                    continue
                detections.append(
                    PlateDetectionResult(bbox=bbox, confidence=conf, source="yolo")
                )
            except Exception:
                logger.exception("Skipping malformed plate detection")
        detections.sort(key=lambda item: item.confidence, reverse=True)
        return detections[:3]

    def _detect_opencv(self, vehicle_crop: np.ndarray) -> list[PlateDetectionResult]:
        """Locate rectangular high-edge regions that resemble plates."""
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV is required for plate fallback detection")
            return []

        height, width = vehicle_crop.shape[:2]
        if height < 20 or width < 40:
            return []

        gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        edges = cv2.Canny(gray, 60, 180)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        scored: list[PlateDetectionResult] = []
        image_area = float(width * height)
        for contour in contours:
            x, y, bw, bh = cv2.boundingRect(contour)
            bbox = BBox(x, y, x + bw, y + bh)
            if not _looks_like_plate(bbox, width, height):
                continue
            # Prefer the lower two-thirds of the vehicle crop.
            vertical_bias = 0.7 if y > height * 0.28 else 0.4
            area_score = min(1.0, bbox.area / max(image_area * 0.08, 1.0))
            confidence = float(max(0.41, min(0.75, 0.35 + area_score * 0.3 + vertical_bias * 0.15)))
            if confidence < settings.plate_confidence:
                continue
            scored.append(
                PlateDetectionResult(bbox=bbox, confidence=confidence, source="opencv")
            )

        scored.extend(self._lower_band(vehicle_crop))
        scored.sort(key=lambda item: item.confidence, reverse=True)
        unique: list[PlateDetectionResult] = []
        for item in scored:
            if any(item.bbox.iou(existing.bbox) > 0.7 for existing in unique):
                continue
            unique.append(item)
        if unique:
            logger.debug("OpenCV plate candidates: %s", len(unique))
        return unique[:3]

    def _lower_band(self, vehicle_crop: np.ndarray) -> list[PlateDetectionResult]:
        height, width = vehicle_crop.shape[:2]
        y1 = int(height * 0.58)
        y2 = int(height * 0.96)
        x1 = int(width * 0.12)
        x2 = int(width * 0.88)
        bbox = BBox(x1, y1, x2, y2)
        if bbox.width < settings.min_plate_width or bbox.height < settings.min_plate_height:
            return []
        return [PlateDetectionResult(bbox=bbox, confidence=0.42, source="lower_band")]


def _looks_like_plate(bbox: BBox, crop_width: int, crop_height: int) -> bool:
    if bbox.height < settings.min_plate_height or bbox.width < settings.min_plate_width:
        return False
    if bbox.height == 0:
        return False
    aspect = bbox.width / float(bbox.height)
    if aspect < 1.5 or aspect > 8.0:
        return False
    area_ratio = bbox.area / float(max(crop_width * crop_height, 1))
    if area_ratio < 0.004 or area_ratio > 0.92:
        return False
    return True
