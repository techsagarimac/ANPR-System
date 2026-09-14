"""Simple IoU tracker and duplicate-suppression helpers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from backend.config import settings
from backend.utils.geometry import BBox

logger = logging.getLogger(__name__)


@dataclass
class Track:
    track_id: int
    bbox: BBox
    vehicle_type: str
    confidence: float
    centroid: tuple[float, float]
    missed: int = 0
    last_plate: Optional[str] = None
    last_ocr_confidence: float = 0.0
    last_saved_at: float = 0.0
    prev_centroid: Optional[tuple[float, float]] = None

    @property
    def direction(self) -> str:
        if self.prev_centroid is None:
            return "unknown"
        dx = self.centroid[0] - self.prev_centroid[0]
        if abs(dx) < 6:
            return "unknown"
        return "right" if dx > 0 else "left"


@dataclass
class TrackedVehicle:
    track: Track
    bbox: BBox
    vehicle_type: str
    confidence: float
    is_new: bool = False


class VehicleTracker:
    """Greedy IoU tracker sufficient for single-camera ANPR deduplication."""

    def __init__(self) -> None:
        self.tracks: dict[int, Track] = {}
        self._next_id = 1
        self.iou_threshold = settings.track_iou_threshold
        self.max_age = settings.track_max_age_frames

    def update(self, detections: list) -> list[TrackedVehicle]:
        assigned: list[TrackedVehicle] = []
        used_tracks: set[int] = set()
        remaining = list(detections)

        matched_detections: set[int] = set()
        for index, detection in enumerate(remaining):
            best_id = None
            best_iou = self.iou_threshold
            for track_id, track in self.tracks.items():
                if track_id in used_tracks:
                    continue
                iou = detection.bbox.iou(track.bbox)
                if iou >= best_iou:
                    best_iou = iou
                    best_id = track_id
            if best_id is None:
                continue
            track = self.tracks[best_id]
            track.prev_centroid = track.centroid
            track.bbox = detection.bbox
            track.vehicle_type = detection.vehicle_type
            track.confidence = detection.confidence
            track.centroid = detection.bbox.centroid
            track.missed = 0
            used_tracks.add(best_id)
            matched_detections.add(index)
            assigned.append(
                TrackedVehicle(
                    track=track,
                    bbox=detection.bbox,
                    vehicle_type=detection.vehicle_type,
                    confidence=detection.confidence,
                )
            )

        for index, detection in enumerate(remaining):
            if index in matched_detections:
                continue
            track_id = self._next_id
            self._next_id += 1
            track = Track(
                track_id=track_id,
                bbox=detection.bbox,
                vehicle_type=detection.vehicle_type,
                confidence=detection.confidence,
                centroid=detection.bbox.centroid,
            )
            self.tracks[track_id] = track
            used_tracks.add(track_id)
            assigned.append(
                TrackedVehicle(
                    track=track,
                    bbox=detection.bbox,
                    vehicle_type=detection.vehicle_type,
                    confidence=detection.confidence,
                    is_new=True,
                )
            )
            logger.debug("New vehicle track id=%s type=%s", track_id, detection.vehicle_type)

        for track_id, track in list(self.tracks.items()):
            if track_id in used_tracks:
                continue
            track.missed += 1
            if track.missed > self.max_age:
                del self.tracks[track_id]
        return assigned


class DuplicateSuppressor:
    """Prevent the same plate/track from being stored on every frame."""

    def __init__(self, cooldown_seconds: Optional[int] = None) -> None:
        self.cooldown = cooldown_seconds or settings.duplicate_cooldown_seconds
        self._last_seen: dict[str, float] = {}

    def should_save(self, plate_number: str, track_id: Optional[int]) -> bool:
        now = time.time()
        keys = [f"plate:{plate_number}"]
        if track_id is not None:
            keys.append(f"track:{track_id}")
        for key in keys:
            last = self._last_seen.get(key)
            if last is not None and (now - last) < self.cooldown:
                logger.debug("Duplicate suppressed key=%s age=%.1fs", key, now - last)
                return False
        for key in keys:
            self._last_seen[key] = now
        stale = [key for key, ts in self._last_seen.items() if now - ts > self.cooldown * 6]
        for key in stale:
            self._last_seen.pop(key, None)
        return True
