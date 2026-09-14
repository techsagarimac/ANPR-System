#!/usr/bin/env python3
"""Start the ANPR FastAPI backend from the project root."""

from __future__ import annotations

import uvicorn

from backend.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
