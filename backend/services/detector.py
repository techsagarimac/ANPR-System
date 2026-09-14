"""YOLO vehicle detection for car, motorcycle, bus, and truck."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.config import settings
from backend.utils.geometry import BBox

logger = logging.getLogger(__name__)

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck", "motorbike"}
CLASS_ALIASES = {"motorbike": "motorcycle"}


class ModelNotFoundError(RuntimeError):
    """Raised when a required YOLO model file is missing."""


@dataclass
class VehicleDetectionResult:
    bbox: BBox
    vehicle_type: str
    confidence: float
    class_id: int


class VehicleDetector:
    """Ultralytics YOLO detector filtered to vehicle classes."""

    def __init__(self) -> None:
        self.model = None
        self.status = "unloaded"
        self.detail: Optional[str] = None
        self.using_fallback = False

    def load(self) -> None:
        custom_path = settings.resolved_vehicle_model_path
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            self.status = "missing"
            self.detail = "ultralytics is not installed"
            logger.error("Vehicle detector unavailable: %s", self.detail)
            raise ModelNotFoundError(self.detail) from exc

        if custom_path.exists():
            logger.info("Loading vehicle model from %s", custom_path)
            self.model = YOLO(str(custom_path))
            self.status = "loaded"
            self.using_fallback = False
            self.detail = str(custom_path)
            return

        message = (
            f"Vehicle model not found at {custom_path}. "
            "Place a YOLO .pt file there or enable the pretrained fallback."
        )
        if not settings.allow_pretrained_vehicle_fallback:
            self.status = "missing"
            self.detail = message
            logger.error("%s", message)
            raise ModelNotFoundError(message)

        logger.warning(
            "%s Falling back to Ultralytics pretrained model %s "
            "(COCO classes filtered to vehicles).",
            message,
            settings.pretrained_vehicle_model,
        )
        self.model = YOLO(settings.pretrained_vehicle_model)
        self.status = "fallback"
        self.using_fallback = True
        self.detail = f"pretrained:{settings.pretrained_vehicle_model}"

    def detect(self, frame: np.ndarray) -> list[VehicleDetectionResult]:
        if self.model is None:
            return []
        try:
            results = self.model.predict(
                frame,
                conf=settings.vehicle_confidence,
                verbose=False,
            )
        except Exception:
            logger.exception("Vehicle detection failed on a frame")
            return []

        detections: list[VehicleDetectionResult] = []
        if not results:
            return detections

        result = results[0]
        names = result.names or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return detections

        height, width = frame.shape[:2]
        for box in boxes:
            try:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                raw_name = str(names.get(cls_id, "")).lower()
                vehicle_type = CLASS_ALIASES.get(raw_name, raw_name)
                if vehicle_type not in {"car", "motorcycle", "bus", "truck"}:
                    if raw_name not in VEHICLE_CLASSES:
                        continue
                xyxy = box.xyxy[0].tolist()
                bbox = BBox(
                    x1=int(xyxy[0]),
                    y1=int(xyxy[1]),
                    x2=int(xyxy[2]),
                    y2=int(xyxy[3]),
                ).clip(width, height)
                if bbox.area < 400:
                    continue
                detections.append(
                    VehicleDetectionResult(
                        bbox=bbox,
                        vehicle_type=vehicle_type,
                        confidence=conf,
                        class_id=cls_id,
                    )
                )
            except Exception:
                logger.exception("Skipping malformed vehicle detection")
                continue

        logger.debug("Vehicle detections: %s", len(detections))
        return detections
