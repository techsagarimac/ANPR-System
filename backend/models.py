"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VehicleDetection(Base):
    """A single accepted ANPR detection event."""

    __tablename__ = "vehicle_detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plate_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ocr_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vehicle_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    vehicle_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    plate_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    ocr_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, default="cam-01")
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    vehicle_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    plate_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_valid_format: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_plate_timestamp", "plate_number", "timestamp"),
        Index("ix_vehicle_type_timestamp", "vehicle_type", "timestamp"),
        Index("ix_camera_timestamp", "camera_id", "timestamp"),
    )
