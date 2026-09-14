"""Vehicle detection list, detail, search, ingest, and CSV export."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import VehicleDetection
from backend.schemas import DetectionCreate, DetectionList, DetectionRead
from backend.api.query import apply_filters, count_filtered, to_read

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/vehicles", response_model=DetectionList)
def list_vehicles(
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=200),
    plate_number: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    camera_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    filters = dict(
        plate_number=plate_number,
        vehicle_type=vehicle_type,
        date=date,
        date_from=date_from,
        date_to=date_to,
        camera_id=camera_id,
    )
    total = count_filtered(db, **filters)
    stmt = apply_filters(
        select(VehicleDetection).order_by(VehicleDetection.timestamp.desc()),
        **filters,
    ).offset(skip).limit(limit)
    rows = db.scalars(stmt).all()
    return DetectionList(total=total, items=[to_read(row) for row in rows])


@router.get("/vehicles/{detection_id}", response_model=DetectionRead)
def get_vehicle(detection_id: int, db: Session = Depends(get_db)):
    record = db.get(VehicleDetection, detection_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    return to_read(record)


@router.get("/search", response_model=DetectionList)
def search_vehicles(
    plate_number: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list_vehicles(
        skip=skip,
        limit=limit,
        plate_number=plate_number,
        vehicle_type=vehicle_type,
        date=date,
        date_from=date_from,
        date_to=date_to,
        db=db,
    )


@router.post("/detection", response_model=DetectionRead, status_code=201)
def create_detection(payload: DetectionCreate, db: Session = Depends(get_db)):
    """Persist a structured detection from an authorized camera node or test client."""
    try:
        record = VehicleDetection(
            plate_number=payload.plate_number.upper().replace(" ", ""),
            ocr_raw=payload.ocr_raw,
            vehicle_type=payload.vehicle_type.lower(),
            vehicle_confidence=payload.vehicle_confidence,
            plate_confidence=payload.plate_confidence,
            ocr_confidence=payload.ocr_confidence,
            timestamp=payload.timestamp or datetime.now(timezone.utc),
            camera_id=payload.camera_id,
            direction=payload.direction,
            vehicle_image_path=payload.vehicle_image_path,
            plate_image_path=payload.plate_image_path,
            is_valid_format=payload.is_valid_format,
            track_id=payload.track_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info("Manual detection inserted id=%s plate=%s", record.id, record.plate_number)
        return to_read(record)
    except Exception as exc:
        db.rollback()
        logger.exception("Database failure while inserting detection")
        raise HTTPException(status_code=500, detail="Database failure") from exc


@router.post("/detection/image", response_model=DetectionList)
async def process_image(file: UploadFile = File(...)):
    """Run the ANPR pipeline on a still image. Does not invent OCR results."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="An image file is required")
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="OpenCV is not installed") from exc

    data = await file.read()
    array = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    from backend.services.engine import engine

    try:
        engine.pipeline.process_frame(frame, persist=True)
    except Exception:
        logger.exception("Still-image pipeline failed")
        raise HTTPException(status_code=500, detail="Detection pipeline failed")

    # Return the most recent rows so the caller can see what was stored.
    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        rows = db.scalars(
            select(VehicleDetection).order_by(VehicleDetection.timestamp.desc()).limit(10)
        ).all()
        return DetectionList(total=len(rows), items=[to_read(row) for row in rows])
    finally:
        db.close()


@router.get("/export/csv")
def export_csv(
    plate_number: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    filters = dict(
        plate_number=plate_number,
        vehicle_type=vehicle_type,
        date=date,
        date_from=date_from,
        date_to=date_to,
    )
    stmt = apply_filters(
        select(VehicleDetection).order_by(VehicleDetection.timestamp.desc()),
        **filters,
    )
    rows = db.scalars(stmt).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["ID", "Plate", "Vehicle type", "Timestamp", "Camera", "Confidence"])
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.plate_number,
                row.vehicle_type,
                row.timestamp.isoformat(),
                row.camera_id,
                f"{row.ocr_confidence:.4f}",
            ]
        )
    buffer.seek(0)
    filename = "anpr_detections.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
