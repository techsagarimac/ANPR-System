"""Health checks and live MJPEG / websocket streams."""

from __future__ import annotations

import asyncio
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse

from backend.schemas import HealthResponse, LiveStatus, StreamStartRequest
from backend.services.engine import engine, placeholder_frame

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    pipeline = engine.pipeline
    if not engine.started:
        camera_state = "disabled"
    elif engine.camera.connected:
        camera_state = "connected"
    else:
        camera_state = "disconnected"
    engine_state = "running" if engine.running else "stopped"
    overall = "ok"
    if pipeline.status.vehicle_model == "missing" or pipeline.status.ocr == "unavailable":
        overall = "degraded"
    if engine.started and not engine.camera.connected:
        overall = "degraded"
    return HealthResponse(
        status=overall,
        camera=camera_state,
        vehicle_model=pipeline.status.vehicle_model,
        plate_model=pipeline.status.plate_model,
        ocr=pipeline.status.ocr,
        engine=engine_state,
        detail=pipeline.status.detail or engine.status().last_error,
    )


@router.get("/stream/status", response_model=LiveStatus)
def stream_status() -> LiveStatus:
    return engine.status()


@router.post("/stream/start", response_model=LiveStatus)
def start_stream(payload: StreamStartRequest | None = None) -> LiveStatus:
    body = payload or StreamStartRequest()
    engine.start(body.source)
    return engine.status()


@router.post("/stream/stop", response_model=LiveStatus)
def stop_stream() -> LiveStatus:
    engine.stop()
    return engine.status()


@router.get("/stream/snapshot")
def snapshot():
    frame = engine.get_annotated_frame()
    if frame is None:
        message = engine.status().last_error or "Waiting for camera frame"
        frame = placeholder_frame(message)
    try:
        import cv2

        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            return Response(status_code=503)
        return Response(
            encoded.tobytes(),
            media_type="image/jpeg",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    except Exception:
        logger.exception("Snapshot encode failed")
        return Response(status_code=500)


@router.get("/stream/mjpeg")
def mjpeg_stream():
    def generate():
        while True:
            frame = engine.get_annotated_frame()
            if frame is None:
                message = engine.status().last_error or "Waiting for camera frame"
                frame = placeholder_frame(message)
            try:
                import cv2

                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if not ok:
                    time.sleep(0.05)
                    continue
                payload = encoded.tobytes()
            except Exception:
                logger.exception("MJPEG encode failed")
                time.sleep(0.1)
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"
            )
            time.sleep(0.04)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws/detections")
async def detections_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            status = engine.status()
            payload = {
                "camera_connected": status.camera_connected,
                "fps": status.fps,
                "frame_index": status.frame_index,
                "overlays": [item.model_dump() for item in status.overlays],
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.4)
    except WebSocketDisconnect:
        return
    except Exception:
        logger.exception("Live websocket closed unexpectedly")
