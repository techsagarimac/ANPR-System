"""Dashboard statistics."""

from __future__ import annotations

from datetime import datetime, time, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.query import to_read
from backend.database import get_db
from backend.models import VehicleDetection
from backend.schemas import DashboardStats

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    total = int(db.scalar(select(func.count(VehicleDetection.id))) or 0)
    today = int(
        db.scalar(
            select(func.count(VehicleDetection.id)).where(VehicleDetection.timestamp >= start)
        )
        or 0
    )
    unique = int(
        db.scalar(select(func.count(func.distinct(VehicleDetection.plate_number)))) or 0
    )
    avg = db.scalar(select(func.avg(VehicleDetection.ocr_confidence))) or 0.0

    type_rows = db.execute(
        select(VehicleDetection.vehicle_type, func.count(VehicleDetection.id)).group_by(
            VehicleDetection.vehicle_type
        )
    ).all()
    vehicle_type_counts = {name: int(count) for name, count in type_rows}

    recent_rows = db.scalars(
        select(VehicleDetection).order_by(VehicleDetection.timestamp.desc()).limit(8)
    ).all()

    hourly_map = {hour: 0 for hour in range(24)}
    hourly_rows = db.execute(
        select(
            func.strftime("%H", VehicleDetection.timestamp),
            func.count(VehicleDetection.id),
        )
        .where(VehicleDetection.timestamp >= start)
        .group_by(func.strftime("%H", VehicleDetection.timestamp))
    ).all()
    for hour, count in hourly_rows:
        try:
            hourly_map[int(hour)] = int(count)
        except (TypeError, ValueError):
            continue
    hourly_today = [{"hour": hour, "count": hourly_map[hour]} for hour in range(24)]

    return DashboardStats(
        total_detections=total,
        today_detections=today,
        unique_plates=unique,
        average_ocr_confidence=float(avg or 0.0),
        vehicle_type_counts=vehicle_type_counts,
        recent=[to_read(row) for row in recent_rows],
        hourly_today=hourly_today,
    )
