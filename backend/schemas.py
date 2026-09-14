"""Pydantic request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DetectionBase(BaseModel):
    plate_number: str = Field(..., min_length=4, max_length=32)
    vehicle_type: str = Field(..., min_length=2, max_length=32)
    vehicle_confidence: float = Field(..., ge=0.0, le=1.0)
    plate_confidence: float = Field(..., ge=0.0, le=1.0)
    ocr_confidence: float = Field(..., ge=0.0, le=1.0)
    camera_id: str = "cam-01"
    direction: str = "unknown"
    ocr_raw: Optional[str] = None
    is_valid_format: bool = False
    track_id: Optional[int] = None


class DetectionCreate(DetectionBase):
    vehicle_image_path: Optional[str] = None
    plate_image_path: Optional[str] = None
    timestamp: Optional[datetime] = None


class DetectionRead(DetectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    vehicle_image_path: Optional[str] = None
    plate_image_path: Optional[str] = None
    vehicle_image_url: Optional[str] = None
    plate_image_url: Optional[str] = None


class DetectionList(BaseModel):
    total: int
    items: list[DetectionRead]


class DashboardStats(BaseModel):
    total_detections: int
    today_detections: int
    unique_plates: int
    average_ocr_confidence: float
    vehicle_type_counts: dict[str, int]
    recent: list[DetectionRead]
    hourly_today: list[dict]


class HealthResponse(BaseModel):
    status: str
    camera: str
    vehicle_model: str
    plate_model: str
    ocr: str
    engine: str
    detail: Optional[str] = None


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class LiveOverlay(BaseModel):
    track_id: Optional[int] = None
    vehicle_type: str
    vehicle_confidence: float
    vehicle_box: BoundingBox
    plate_box: Optional[BoundingBox] = None
    plate_number: Optional[str] = None
    plate_confidence: Optional[float] = None
    ocr_confidence: Optional[float] = None


class LiveStatus(BaseModel):
    camera_connected: bool
    fps: float
    frame_index: int
    last_error: Optional[str] = None
    overlays: list[LiveOverlay] = Field(default_factory=list)
    engine_running: bool = False
    models_loading: bool = False
    source: Optional[str] = None


class StreamStartRequest(BaseModel):
    source: Optional[str] = None
