# ANPR System

Authorized educational Automatic Number Plate Recognition (ANPR) for sites where camera use is lawful and approved.

The system reads a camera or video source, detects vehicles, localizes number plates, recognizes plate text with PaddleOCR, suppresses duplicate reads, stores accepted events in SQLite, and serves a React operations dashboard. It does **not** identify vehicle owners, scrape registration databases, or perform facial recognition.

## Project overview

This repository is a production-style teaching stack:

- **Backend:** FastAPI, SQLAlchemy, SQLite, OpenCV, Ultralytics YOLO, PaddleOCR
- **Frontend:** React, Vite, Tailwind CSS, Axios
- **Storage:** `data/database.db`, vehicle crops in `data/vehicles/`, plate crops in `data/plates/`

Use it only with video you are authorized to process.

## Architecture

```
Camera / video / RTSP
        │
        ▼
 OpenCV capture  ── frame skip (PROCESS_EVERY_N_FRAMES)
        │
        ▼
 YOLO vehicle detector  (car, motorcycle, bus, truck)
        │
        ▼
 IoU tracker + duplicate cooldown
        │
        ▼
 Plate detector (custom YOLO, or OpenCV fallback)
        │
        ▼
 Selective preprocessing → PaddleOCR → normalize/validate
        │
        ▼
 SQLite + JPEG crops (accepted detections only)
        │
        ▼
 FastAPI  (/api/*, MJPEG, CSV)  →  React dashboard
```

Modules stay independent so a GPU device string can be added later in Ultralytics `predict(device=...)` without rewriting the pipeline.

## Features

- USB webcam, video file, and RTSP URL via `CAMERA_SOURCE`
- YOLO vehicle detection with a configurable confidence threshold
- Separate plate detector with a graceful missing-model path
- OCR candidate generation (resize, grayscale, denoise, CLAHE, sharpen, adaptive threshold) applied from image statistics, not blindly stacked
- Indian-style plate normalization as a **quality signal**, not identity proof
- Track-based deduplication with `DUPLICATE_COOLDOWN_SECONDS`
- SQLite history, search, date filters, vehicle-type filters, CSV export
- Live annotated MJPEG feed and dashboard statistics
- Structured logging to the console and `data/anpr.log`

## Requirements

- Python 3.11 or 3.12 recommended for Ultralytics and PaddleOCR wheels (3.13 may not have Paddle/PyTorch packages yet)
- Node.js 18+
- A camera, RTSP URL, or video file for live mode
- Optional NVIDIA GPU for faster YOLO/OCR (CPU works)

## Installation

```bash
git clone <this-repo> ANPR-System
cd ANPR-System
```

## Python environment setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux users may need a PaddlePaddle wheel that matches the platform:

```bash
python -m pip install paddlepaddle
pip install paddleocr
```

If PaddleOCR cannot be installed, the API still starts. Live OCR is marked `unavailable` until PaddleOCR loads.

## Dependencies

See `requirements.txt`. Core runtime:

| Package | Role |
| --- | --- |
| fastapi, uvicorn | HTTP API |
| sqlalchemy | SQLite ORM |
| opencv-python | camera, preprocessing, MJPEG |
| ultralytics | YOLO vehicle/plate models |
| paddleocr | plate text recognition |
| pydantic-settings | `.env` configuration |

Frontend dependencies are installed with `npm install` in `frontend/`.

## Model setup

Weight files are **not** committed. Place them here:

```
models/vehicle_model.pt
models/plate_model.pt
```

### Vehicle model

If `models/vehicle_model.pt` is missing and `ALLOW_PRETRAINED_VEHICLE_FALLBACK=true`, the backend loads Ultralytics `yolov8n.pt` (downloaded on first use) and keeps COCO classes `car`, `motorcycle`, `bus`, and `truck`. That fallback is a real detector, not a stub.

Disable it if you require a custom checkpoint:

```
ALLOW_PRETRAINED_VEHICLE_FALLBACK=false
```

### Plate model

Train a single-class `license_plate` detector (see below) and copy `best.pt` to `models/plate_model.pt`.

If the custom plate model is missing and `ALLOW_OPENCV_PLATE_FALLBACK=true`, plate localization uses OpenCV morphology on each vehicle crop. That is a real heuristic, not random boxes. Accuracy will be much lower than a trained YOLO plate model.

If both custom plate weights and the OpenCV fallback are disabled, plate detection is skipped and the logs explain how to add the model.

## Database setup

SQLite is created automatically on backend startup:

```
data/database.db
```

The `vehicle_detections` table includes indexes on `plate_number`, `timestamp`, vehicle type, and camera. No separate migration step is required for a fresh install.

## Configuration

Copy `.env.example` to `.env` (a default `.env` is included for local development):

```
CAMERA_SOURCE=0
VEHICLE_MODEL_PATH=models/vehicle_model.pt
PLATE_MODEL_PATH=models/plate_model.pt
VEHICLE_CONFIDENCE=0.40
PLATE_CONFIDENCE=0.40
OCR_CONFIDENCE=0.60
DUPLICATE_COOLDOWN_SECONDS=10
DATABASE_URL=sqlite:///./data/database.db
PROCESS_EVERY_N_FRAMES=2
```

`CAMERA_SOURCE` examples:

```
CAMERA_SOURCE=0
CAMERA_SOURCE=/path/to/traffic.mp4
CAMERA_SOURCE=rtsp://user:pass@192.168.1.20:554/stream
```

Do not hard-code the source in Python. API-only mode (no camera thread):

```
ANPR_DISABLE_ENGINE=true
```

## Backend startup

From the project root:

```bash
source .venv/bin/activate
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

or:

```bash
PYTHONPATH=. python run_backend.py
```

OpenAPI docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Health: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Frontend startup

```bash
cd frontend
npm install
npm run dev
```

Dashboard: [http://127.0.0.1:5173](http://127.0.0.1:5173)

Vite proxies `/api` and `/data` to the backend.

Production-style frontend build:

```bash
cd frontend
npm run build
```

If `frontend/dist` exists, FastAPI also serves it from `/`.

## Camera configuration

| Source | `CAMERA_SOURCE` |
| --- | --- |
| Default USB webcam | `0` |
| Second webcam | `1` |
| Video file | `/absolute/path/video.mp4` |
| RTSP | `rtsp://...` |

The live page shows `GET /api/stream/mjpeg` with OpenCV overlays: vehicle box, plate box, plate text, and confidence. If the camera cannot open, the API stays up and the stream shows a status frame.

## Training a custom plate detector

1. Label plates in YOLO format (`class x_center y_center width height`, all normalized).
2. Arrange files as described in `training/dataset.yaml`.
3. Train:

```bash
PYTHONPATH=. python training/train.py --data training/dataset.yaml --epochs 80 --model yolov8n.pt
```

Successful runs copy `best.pt` to `models/plate_model.pt`.

Evaluate:

```bash
PYTHONPATH=. python training/test.py --weights models/plate_model.pt --data training/dataset.yaml
```

Inference on a folder:

```bash
PYTHONPATH=. python training/test.py --weights models/plate_model.pt --source path/to/images
```

## API documentation

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Camera, model, OCR, and engine status |
| GET | `/api/vehicles` | Paginated detections (`skip`, `limit`, filters) |
| GET | `/api/vehicles/{id}` | Single detection |
| GET | `/api/search` | Search by `plate_number`, `date`, `vehicle_type`, `date_from`, `date_to` |
| GET | `/api/dashboard/stats` | Totals, unique plates, type counts, hourly series |
| POST | `/api/detection` | Insert a structured detection from an authorized node |
| POST | `/api/detection/image` | Run the real pipeline on an uploaded still image |
| GET | `/api/export/csv` | CSV: ID, plate, type, timestamp, camera, confidence |
| GET | `/api/stream/mjpeg` | Annotated live JPEG stream |
| GET | `/api/stream/status` | Current overlays and FPS |
| WS | `/api/ws/detections` | Live overlay JSON |

`GET /api/vehicles` query parameters: `plate_number`, `vehicle_type`, `date`, `date_from`, `date_to`, `camera_id`, `skip`, `limit`.

Example search:

```bash
curl "http://127.0.0.1:8000/api/search?plate_number=MH12&vehicle_type=car"
```

Example CSV:

```bash
curl -OJ "http://127.0.0.1:8000/api/export/csv?date=2026-09-14"
```

## Testing

```bash
source .venv/bin/activate
PYTHONPATH=. ANPR_DISABLE_ENGINE=true pytest -q
```

Tests cover plate validation, tracking, preprocessing, and API routes. They do not download YOLO/OCR weights and do not invent OCR strings.

Still-image smoke test (requires loaded models/OCR):

```bash
curl -F "file=@plate_photo.jpg" http://127.0.0.1:8000/api/detection/image
```

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `Unable to open camera source` | `CAMERA_SOURCE`, permissions, RTSP URL, file path |
| Vehicle model missing | Put `vehicle_model.pt` in `models/` or keep the pretrained fallback enabled |
| Plate model missing | Train with `training/train.py` or keep OpenCV fallback enabled |
| OCR unavailable | Install `paddlepaddle` + `paddleocr`; watch `data/anpr.log` |
| Empty OCR / no DB rows | Plate crop too small, confidence below `OCR_CONFIDENCE`, or malformed text rejected |
| Duplicate flood | Increase `DUPLICATE_COOLDOWN_SECONDS` or `PROCESS_EVERY_N_FRAMES` |
| Frontend cannot reach API | Backend on port 8000; Vite proxy; CORS origins in `.env` |
| Slow CPU | Raise frame skip, use a smaller YOLO model, GPU device later |

## Deployment notes

- Run behind HTTPS if the dashboard is reachable beyond localhost.
- Restrict CORS and do not expose SQLite or `/data` on the public internet without access control.
- Use a process manager (systemd, supervisord) for `uvicorn`.
- Put YOLO/Paddle on a machine with enough RAM; first model download can be large.
- Back up `data/database.db` and the image folders together.
- For production, add authentication in front of FastAPI (reverse proxy SSO, VPN, or app-level auth). This teaching stack does not ship login on purpose.

## Privacy and legal considerations

This project is for **authorized** educational or operational vehicle monitoring only.

Operators must:

- Comply with applicable privacy, data-protection, and surveillance laws
- Obtain permission before deploying cameras
- Limit retention of plate images and text to a lawful purpose
- Avoid using this software to identify people, owners, or households
- Not connect the pipeline to external vehicle-registration owner lookup services

The validator only checks whether OCR text *looks like* a common Indian registration pattern. A match is not evidence of ownership, identity, or a traffic offence.

## How the pipeline works

1. **Capture.** `CameraService` opens the configured source and yields BGR frames.
2. **Skip.** Only every *n*th frame is processed (`PROCESS_EVERY_N_FRAMES`).
3. **Vehicles.** Ultralytics YOLO returns boxes; non-vehicle classes are discarded.
4. **Tracks.** An IoU tracker assigns stable IDs so the same vehicle is not treated as a new object every frame. Direction is estimated from centroid motion.
5. **Plates.** Each vehicle crop is passed to the plate YOLO model, or to the OpenCV candidate finder if that model is absent.
6. **Preprocess.** Contrast, noise, and size decide which OCR variants to try (never all filters on every crop).
7. **OCR.** PaddleOCR returns text and confidence. Output is uppercased and stripped of invalid characters. Conservative positional 0/O-style fixes run only when they produce a known plate layout. Characters are not invented.
8. **Accept.** Format quality and OCR confidence must both pass. Garbage strings are dropped.
9. **Dedupe.** The same plate or track cannot be written again until the cooldown elapses.
10. **Store.** SQLite gets the row; JPEGs are named `vehicle_YYYYMMDD_HHMMSS_ID.jpg` and `plate_...jpg`. No image is written for skipped frames.

## Next recommended improvements

- ByteTrack/BoT-SORT instead of greedy IoU tracking
- GPU selection and TensorRT/ONNX export
- Multi-camera workers with a shared database
- Authentication and role-based access for the dashboard
- Retention jobs that delete images older than a policy window
- Night-time plate enhancement and motion-triggered capture
- Automated evaluation set with labeled plates (precision/recall, not demo screenshots)

## License and use

Use only where you have the right to capture and process vehicle imagery. The authors of this teaching project are not responsible for unlawful surveillance deployments.
