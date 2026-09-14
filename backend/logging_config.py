"""Central logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.config import settings


def configure_logging() -> None:
    """Configure console and rotating file logging."""
    log_dir: Path = settings.data_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "anpr.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    logging.getLogger("ultralytics").setLevel(logging.WARNING)
    logging.getLogger("ppocr").setLevel(logging.WARNING)
    logging.getLogger("paddle").setLevel(logging.WARNING)
