# Model files

Place YOLO weights in this directory. Weight files are not shipped with the repository because they are large binary artifacts.

## Vehicle detection

Recommended filename (matches `.env`):

```
models/vehicle_model.pt
```

If this file is missing and `ALLOW_PRETRAINED_VEHICLE_FALLBACK=true`, the backend loads Ultralytics `yolov8n.pt` (COCO) and keeps only `car`, `motorcycle`, `bus`, and `truck`.

To use your own detector, train or export a YOLO model whose class names include those vehicle types, then set:

```
VEHICLE_MODEL_PATH=models/vehicle_model.pt
```

## Plate detection

Recommended filename:

```
models/plate_model.pt
```

Train a single-class YOLO detector (`license_plate`) using `training/train.py`. If the custom plate model is missing and `ALLOW_OPENCV_PLATE_FALLBACK=true`, the backend uses an OpenCV morphological candidate finder on each vehicle crop. That fallback is a real computer-vision heuristic, not a substitute for a trained plate detector.

Disable fallbacks if you want the service to refuse to start without custom weights:

```
ALLOW_PRETRAINED_VEHICLE_FALLBACK=false
ALLOW_OPENCV_PLATE_FALLBACK=false
```
