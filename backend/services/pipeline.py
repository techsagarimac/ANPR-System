"""End-to-end ANPR frame pipeline.

Camera → vehicle detection → tracking → plate detection → preprocessing →
OCR → validation → deduplication → database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from backend.config import settings
from backend.database import SessionLocal
from backend.models import VehicleDetection
from backend.schemas import BoundingBox, LiveOverlay
from backend.services.detector import VehicleDetectionResult, VehicleDetector
from backend.services.ocr import PlateOCR
from backend.services.plate_detector import PlateDetector
from backend.services.storage import save_detection_images
from backend.services.tracker import DuplicateSuppressor, TrackedVehicle, VehicleTracker
from backend.utils.geometry import BBox

logger = logging.getLogger(__name__)


@dataclass
class PipelineStatus:
    vehicle_model: str = "unloaded"
    plate_model: str = "unloaded"
    ocr: str = "unloaded"
    detail: Optional[str] = None


@dataclass
class FrameResult:
    overlays: list[LiveOverlay] = field(default_factory=list)
    saved_ids: list[int] = field(default_factory=list)


class ANPRPipeline:
    def __init__(self) -> None:
        self.vehicle_detector = VehicleDetector()
        self.plate_detector = PlateDetector()
        self.ocr = PlateOCR()
        self.tracker = VehicleTracker()
        self.duplicates = DuplicateSuppressor()
        self.status = PipelineStatus()

    def load(self) -> None:
        try:
            self.vehicle_detector.load()
        except Exception as exc:
            logger.exception("Vehicle model load failed")
            self.status.vehicle_model = "missing"
            self.status.detail = str(exc)
        else:
            self.status.vehicle_model = self.vehicle_detector.status

        try:
            self.plate_detector.load()
        except Exception as exc:
            logger.exception("Plate model load failed")
            self.status.plate_model = "missing"
            self.status.detail = str(exc)
        else:
            self.status.plate_model = self.plate_detector.status

        try:
            self.ocr.load()
        except Exception as exc:
            logger.exception("OCR load failed")
            self.status.ocr = "unavailable"
            self.status.detail = str(exc)
        else:
            self.status.ocr = self.ocr.status

    def process_frame(self, frame: np.ndarray, persist: bool = True) -> FrameResult:
        result = FrameResult()
        if frame is None or getattr(frame, "size", 0) == 0:
            logger.warning("Skipping empty frame")
            return result

        try:
            vehicles = self.vehicle_detector.detect(frame)
        except Exception:
            logger.exception("Vehicle detection crashed on a frame")
            vehicles = []

        if not vehicles:
            vehicles = _scene_as_vehicle(frame)

        try:
            tracked = self.tracker.update(vehicles)
        except Exception:
            logger.exception("Tracker failed; continuing without IDs")
            tracked = []

        for item in tracked:
            overlay = self._process_vehicle(frame, item, persist=persist)
            if overlay is None:
                continue
            result.overlays.append(overlay)
            if overlay.plate_number:
                logger.debug(
                    "Live overlay track=%s plate=%s",
                    overlay.track_id,
                    overlay.plate_number,
                )
        return result

    def _process_vehicle(self, frame, item: TrackedVehicle, persist: bool) -> Optional[LiveOverlay]:
        height, width = frame.shape[:2]
        vehicle_box = item.bbox.clip(width, height)
        overlay = LiveOverlay(
            track_id=item.track.track_id,
            vehicle_type=item.vehicle_type,
            vehicle_confidence=float(item.confidence),
            vehicle_box=BoundingBox(
                x1=vehicle_box.x1, y1=vehicle_box.y1, x2=vehicle_box.x2, y2=vehicle_box.y2
            ),
        )

        vehicle_crop = _crop(frame, vehicle_box)
        if vehicle_crop is None:
            return overlay

        try:
            plates = self.plate_detector.detect(vehicle_crop)
        except Exception:
            logger.exception("Plate detection failed for track %s", item.track.track_id)
            return overlay

        if not plates:
            return overlay

        if not _should_run_ocr(item.track):
            overlay.plate_number = item.track.last_plate
            overlay.ocr_confidence = item.track.last_ocr_confidence or None
            plate = plates[0]
            plate_abs = _offset_box(vehicle_box, plate.bbox, width, height)
            overlay.plate_box = BoundingBox(
                x1=plate_abs.x1, y1=plate_abs.y1, x2=plate_abs.x2, y2=plate_abs.y2
            )
            overlay.plate_confidence = float(plate.confidence)
            return overlay

        best = None
        for plate in plates[:2]:
            plate_abs = _offset_box(vehicle_box, plate.bbox, width, height)
            plate_crop = _crop(frame, plate_abs)
            if plate_crop is None:
                continue
            try:
                ocr_result = self.ocr.recognize(plate_crop)
            except Exception:
                logger.exception("OCR failed for track %s", item.track.track_id)
                continue
            if ocr_result is None or not ocr_result.normalized:
                continue
            candidate = (ocr_result, plate, plate_abs, plate_crop)
            if best is None or _ocr_rank(ocr_result) > _ocr_rank(best[0]):
                best = candidate

        if best is None:
            logger.info("Empty or failed OCR for track %s", item.track.track_id)
            plate = plates[0]
            plate_abs = _offset_box(vehicle_box, plate.bbox, width, height)
            overlay.plate_box = BoundingBox(
                x1=plate_abs.x1, y1=plate_abs.y1, x2=plate_abs.x2, y2=plate_abs.y2
            )
            overlay.plate_confidence = float(plate.confidence)
            return overlay

        ocr_result, plate, plate_abs, plate_crop = best
        overlay.plate_box = BoundingBox(
            x1=plate_abs.x1, y1=plate_abs.y1, x2=plate_abs.x2, y2=plate_abs.y2
        )
        overlay.plate_confidence = float(plate.confidence)
        overlay.plate_number = ocr_result.normalized
        overlay.ocr_confidence = float(ocr_result.confidence)
        item.track.last_plate = ocr_result.normalized
        item.track.last_ocr_confidence = ocr_result.confidence

        if persist and ocr_result.accepted:
            saved_id = self._persist(
                vehicle_crop=vehicle_crop,
                plate_crop=plate_crop,
                item=item,
                plate_confidence=float(plate.confidence),
                ocr_result=ocr_result,
            )
            if saved_id is not None:
                logger.info(
                    "Stored plate detection id=%s plate=%s type=%s",
                    saved_id,
                    ocr_result.normalized,
                    item.vehicle_type,
                )
        return overlay

    def _persist(self, vehicle_crop, plate_crop, item, plate_confidence, ocr_result) -> Optional[int]:
        plate_number = ocr_result.normalized
        if not self.duplicates.should_save(plate_number, item.track.track_id):
            return None

        db = SessionLocal()
        try:
            record = VehicleDetection(
                plate_number=plate_number,
                ocr_raw=ocr_result.raw_text,
                vehicle_type=item.vehicle_type,
                vehicle_confidence=float(item.confidence),
                plate_confidence=plate_confidence,
                ocr_confidence=float(ocr_result.confidence),
                timestamp=datetime.now(timezone.utc),
                camera_id=settings.camera_id,
                direction=item.track.direction,
                is_valid_format=ocr_result.is_valid_format,
                track_id=item.track.track_id,
            )
            db.add(record)
            db.flush()
            vehicle_path, plate_path = save_detection_images(
                record.id, vehicle_crop, plate_crop, record.timestamp
            )
            record.vehicle_image_path = vehicle_path
            record.plate_image_path = plate_path
            db.commit()
            db.refresh(record)
            item.track.last_saved_at = record.timestamp.timestamp()
            return record.id
        except Exception:
            db.rollback()
            logger.exception("Database insertion failed")
            return None
        finally:
            db.close()


def _scene_as_vehicle(frame: np.ndarray) -> list[VehicleDetectionResult]:
    """If YOLO finds no vehicle, still look for a plate in the full frame."""
    height, width = frame.shape[:2]
    logger.debug("No vehicle box; scanning full frame for a plate")
    return [
        VehicleDetectionResult(
            bbox=BBox(0, 0, width, height),
            vehicle_type="unknown",
            confidence=0.5,
            class_id=-1,
        )
    ]


def _offset_box(vehicle_box: BBox, plate_box: BBox, width: int, height: int) -> BBox:
    return BBox(
        vehicle_box.x1 + plate_box.x1,
        vehicle_box.y1 + plate_box.y1,
        vehicle_box.x1 + plate_box.x2,
        vehicle_box.y1 + plate_box.y2,
    ).clip(width, height)


def _crop(frame: np.ndarray, bbox: BBox) -> Optional[np.ndarray]:
    if bbox.width < 4 or bbox.height < 4:
        return None
    crop = frame[bbox.y1 : bbox.y2, bbox.x1 : bbox.x2]
    if crop.size == 0:
        return None
    return crop


def _should_run_ocr(track) -> bool:
    if not track.last_plate:
        return True
    if track.last_ocr_confidence >= 0.92:
        return False
    return True


def _ocr_rank(result) -> float:
    bonus = 0.25 if result.is_valid_format else 0.0
    accepted = 0.2 if result.accepted else 0.0
    return result.confidence * 0.7 + result.quality_score * 0.3 + bonus + accepted
