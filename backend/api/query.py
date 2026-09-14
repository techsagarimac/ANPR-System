"""Shared query helpers for detection records."""

from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from backend.models import VehicleDetection
from backend.schemas import DetectionRead


def apply_filters(
    stmt: Select,
    plate_number: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    camera_id: Optional[str] = None,
) -> Select:
    if plate_number:
        stmt = stmt.where(VehicleDetection.plate_number.ilike(f"%{plate_number.strip().upper()}%"))
    if vehicle_type:
        stmt = stmt.where(VehicleDetection.vehicle_type == vehicle_type.lower())
    if camera_id:
        stmt = stmt.where(VehicleDetection.camera_id == camera_id)

    start = None
    end = None
    try:
        if date:
            day = datetime.fromisoformat(date).date()
            start = datetime.combine(day, time.min, tzinfo=timezone.utc)
            end = datetime.combine(day, time.max, tzinfo=timezone.utc)
        if date_from:
            start = datetime.fromisoformat(date_from)
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        if date_to:
            end = datetime.fromisoformat(date_to)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date filter: {exc}") from exc
    if start:
        stmt = stmt.where(VehicleDetection.timestamp >= start)
    if end:
        stmt = stmt.where(VehicleDetection.timestamp <= end)
    return stmt


def count_filtered(db: Session, **filters) -> int:
    stmt = apply_filters(select(func.count(VehicleDetection.id)), **filters)
    return int(db.scalar(stmt) or 0)


def to_read(record: VehicleDetection) -> DetectionRead:
    payload = DetectionRead.model_validate(record)
    if record.vehicle_image_path:
        payload.vehicle_image_url = "/" + record.vehicle_image_path.lstrip("/")
    if record.plate_image_path:
        payload.plate_image_url = "/" + record.plate_image_path.lstrip("/")
    return payload
