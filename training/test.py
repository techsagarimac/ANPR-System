#!/usr/bin/env python3
"""Evaluate or run inference with a trained plate detector.

Examples:

    python training/test.py --weights models/plate_model.pt --source path/to/images
    python training/test.py --weights models/plate_model.pt --data training/dataset.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test a YOLO plate detector")
    parser.add_argument("--weights", default=str(ROOT / "models" / "plate_model.pt"))
    parser.add_argument("--data", default=str(ROOT / "training" / "dataset.yaml"))
    parser.add_argument("--source", default=None, help="Image, folder, or video for predict()")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install ultralytics before testing: pip install ultralytics") from exc

    weights = Path(args.weights)
    if not weights.exists():
        raise SystemExit(
            f"Weights not found: {weights}\n"
            "Train a detector with python training/train.py or copy plate_model.pt into models/."
        )

    model = YOLO(str(weights))
    if args.source:
        results = model.predict(source=args.source, imgsz=args.imgsz, conf=args.conf)
        print(f"Inference complete on {len(results)} item(s)")
        return

    metrics = model.val(data=args.data, imgsz=args.imgsz, conf=args.conf)
    print(metrics)


if __name__ == "__main__":
    main()
