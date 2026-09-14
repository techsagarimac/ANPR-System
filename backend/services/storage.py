"""Persist accepted vehicle and plate crops. Images are saved only for accepted detections."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)


def _write_jpeg(path: Path, image: np.ndarray) -> bool:
    try:
        import cv2
    except ImportError:
        logger.error("OpenCV is required to save detection images")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    if not ok:
        logger.error("JPEG encode failed for %s", path)
        return False
    path.write_bytes(encoded.tobytes())
    return True


def save_detection_images(
    detection_id: int,
    vehicle_image: np.ndarray,
    plate_image: np.ndarray,
    timestamp: datetime,
) -> tuple[str | None, str | None]:
    stamp = timestamp.strftime("%Y%m%d_%H%M%S")
    vehicle_name = f"vehicle_{stamp}_{detection_id:03d}.jpg"
    plate_name = f"plate_{stamp}_{detection_id:03d}.jpg"
    vehicle_path = settings.vehicle_image_dir / vehicle_name
    plate_path = settings.plate_image_dir / plate_name

    vehicle_saved = _write_jpeg(vehicle_path, vehicle_image)
    plate_saved = _write_jpeg(plate_path, plate_image)
    if vehicle_saved:
        logger.info("Saved vehicle image %s", vehicle_path.name)
    if plate_saved:
        logger.info("Saved plate image %s", plate_path.name)

    return (
        f"data/vehicles/{vehicle_name}" if vehicle_saved else None,
        f"data/plates/{plate_name}" if plate_saved else None,
    )
