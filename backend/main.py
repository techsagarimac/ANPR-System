"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import dashboard, stream, vehicles
from backend.config import PROJECT_ROOT, settings
from backend.database import init_db
from backend.logging_config import configure_logging
from backend.services.engine import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    init_db()
    if not settings.disable_engine:
        try:
            engine.start()
        except Exception:
            logging.getLogger(__name__).exception("Live camera engine failed to start")
    yield
    if engine.running:
        engine.stop()


app = FastAPI(
    title="ANPR System API",
    description=(
        "Authorized educational Automatic Number Plate Recognition API. "
        "It stores plate text and vehicle crops only; it does not identify owners."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stream.router, prefix="/api", tags=["health-stream"])
app.include_router(vehicles.router, prefix="/api", tags=["vehicles"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])

data_dir = PROJECT_ROOT / "data"
data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")

frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=True)
