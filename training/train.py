#!/usr/bin/env python3
"""Train a YOLO license-plate detector with Ultralytics.

Example:

    python training/train.py --data training/dataset.yaml --epochs 80 --model yolov8n.pt
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a YOLO plate detector")
    parser.add_argument("--data", default=str(ROOT / "training" / "dataset.yaml"))
    parser.add_argument("--model", default="yolov8n.pt", help="Base YOLO checkpoint")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default=None, help="cuda:0, cpu, or mps")
    parser.add_argument(
        "--project",
        default=str(ROOT / "training" / "runs"),
        help="Ultralytics project directory",
    )
    parser.add_argument("--name", default="plate")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Install ultralytics before training: pip install ultralytics") from exc

    data_path = Path(args.data)
    if not data_path.exists():
        raise SystemExit(f"Dataset yaml not found: {data_path}")

    print(f"Loading base model: {args.model}")
    model = YOLO(args.model)
    model.train(
        data=str(data_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        exist_ok=True,
    )
    best = Path(args.project) / args.name / "weights" / "best.pt"
    target = ROOT / "models" / "plate_model.pt"
    if best.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(best.read_bytes())
        print(f"Copied best weights to {target}")
    else:
        print("Training finished but best.pt was not found. Check the Ultralytics run folder.")


if __name__ == "__main__":
    main()
