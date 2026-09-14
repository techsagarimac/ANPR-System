"""Application configuration loaded from environment variables and .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime settings for the ANPR system."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    camera_source: str = Field(default="0", alias="CAMERA_SOURCE")
    camera_id: str = Field(default="cam-01", alias="CAMERA_ID")
    camera_width: int = Field(default=1280, alias="CAMERA_WIDTH")
    camera_height: int = Field(default=720, alias="CAMERA_HEIGHT")

    vehicle_model_path: str = Field(
        default="models/vehicle_model.pt", alias="VEHICLE_MODEL_PATH"
    )
    plate_model_path: str = Field(
        default="models/plate_model.pt", alias="PLATE_MODEL_PATH"
    )
    allow_pretrained_vehicle_fallback: bool = Field(
        default=True, alias="ALLOW_PRETRAINED_VEHICLE_FALLBACK"
    )
    allow_opencv_plate_fallback: bool = Field(
        default=True, alias="ALLOW_OPENCV_PLATE_FALLBACK"
    )
    pretrained_vehicle_model: str = Field(
        default="yolov8n.pt", alias="PRETRAINED_VEHICLE_MODEL"
    )

    vehicle_confidence: float = Field(default=0.40, alias="VEHICLE_CONFIDENCE")
    plate_confidence: float = Field(default=0.40, alias="PLATE_CONFIDENCE")
    ocr_confidence: float = Field(default=0.60, alias="OCR_CONFIDENCE")

    duplicate_cooldown_seconds: int = Field(
        default=10, alias="DUPLICATE_COOLDOWN_SECONDS"
    )
    process_every_n_frames: int = Field(default=2, alias="PROCESS_EVERY_N_FRAMES")
    track_iou_threshold: float = Field(default=0.30, alias="TRACK_IOU_THRESHOLD")
    track_max_age_frames: int = Field(default=20, alias="TRACK_MAX_AGE_FRAMES")
    min_plate_width: int = Field(default=60, alias="MIN_PLATE_WIDTH")
    min_plate_height: int = Field(default=16, alias="MIN_PLATE_HEIGHT")

    database_url: str = Field(
        default="sqlite:///./data/database.db", alias="DATABASE_URL"
    )
    disable_engine: bool = Field(default=False, alias="ANPR_DISABLE_ENGINE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    @field_validator("process_every_n_frames")
    @classmethod
    def _at_least_one_frame(cls, value: int) -> int:
        return max(1, value)

    @property
    def cors_origin_list(self) -> List[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def resolved_vehicle_model_path(self) -> Path:
        return self._resolve_path(self.vehicle_model_path)

    @property
    def resolved_plate_model_path(self) -> Path:
        return self._resolve_path(self.plate_model_path)

    @property
    def data_dir(self) -> Path:
        return PROJECT_ROOT / "data"

    @property
    def vehicle_image_dir(self) -> Path:
        return self.data_dir / "vehicles"

    @property
    def plate_image_dir(self) -> Path:
        return self.data_dir / "plates"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "database.db"

    def resolved_database_url(self) -> str:
        url = self.database_url
        if url.startswith("sqlite:///./"):
            relative = url.replace("sqlite:///./", "", 1)
            return f"sqlite:///{(PROJECT_ROOT / relative).as_posix()}"
        return url

    def parsed_camera_source(self):
        """Return an int for USB indexes, otherwise the original string."""
        source = str(self.camera_source).strip()
        if source.isdigit():
            return int(source)
        return source

    @staticmethod
    def _resolve_path(path_value: str) -> Path:
        path = Path(path_value)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
