"""Plate-image preprocessing for OCR.

Methods are applied selectively based on image statistics. The pipeline
generates a small set of OCR candidates instead of stacking every filter.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - optional at import time for unit tests
    cv2 = None


@dataclass
class OCRCandidate:
    name: str
    image: np.ndarray


def _ensure_cv2():
    if cv2 is None:
        raise RuntimeError("OpenCV is required for plate preprocessing")
    return cv2


def resize_plate(image: np.ndarray, min_width: int = 240, min_height: int = 80) -> np.ndarray:
    cv = _ensure_cv2()
    height, width = image.shape[:2]
    scale = max(min_width / max(width, 1), min_height / max(height, 1), 1.0)
    if scale == 1.0:
        return image
    new_size = (int(width * scale), int(height * scale))
    return cv.resize(image, new_size, interpolation=cv.INTER_CUBIC)


def to_grayscale(image: np.ndarray) -> np.ndarray:
    cv = _ensure_cv2()
    if len(image.shape) == 2:
        return image
    return cv.cvtColor(image, cv.COLOR_BGR2GRAY)


def gaussian_denoise(image: np.ndarray) -> np.ndarray:
    cv = _ensure_cv2()
    return cv.GaussianBlur(image, (3, 3), 0)


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    cv = _ensure_cv2()
    gray = to_grayscale(image)
    clahe = cv.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def adaptive_threshold(image: np.ndarray) -> np.ndarray:
    cv = _ensure_cv2()
    gray = to_grayscale(image)
    return cv.adaptiveThreshold(
        gray, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C, cv.THRESH_BINARY, 21, 7
    )


def sharpen(image: np.ndarray) -> np.ndarray:
    cv = _ensure_cv2()
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharpened = cv.filter2D(image, -1, kernel)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def _noise_estimate(gray: np.ndarray) -> float:
    cv = _ensure_cv2()
    blur = cv.GaussianBlur(gray, (3, 3), 0)
    residual = cv.absdiff(gray, blur)
    return float(residual.mean())


def generate_ocr_candidates(plate_bgr: np.ndarray) -> list[OCRCandidate]:
    """Build a short list of preprocessed images suitable for OCR."""
    if plate_bgr is None or getattr(plate_bgr, "size", 0) == 0:
        return []

    resized = resize_plate(plate_bgr)
    gray = to_grayscale(resized)
    mean = float(gray.mean())
    std = float(gray.std())
    noise = _noise_estimate(gray)

    candidates = [
        OCRCandidate(name="resized_color", image=resized),
        OCRCandidate(name="grayscale", image=gray),
    ]

    if std < 45 or mean < 70 or mean > 190:
        candidates.append(OCRCandidate(name="clahe", image=enhance_contrast(resized)))

    if noise > 8.0:
        denoised = gaussian_denoise(gray)
        candidates.append(OCRCandidate(name="denoise_sharpen", image=sharpen(denoised)))

    if std < 35:
        candidates.append(
            OCRCandidate(name="adaptive_threshold", image=adaptive_threshold(resized))
        )

    # Keep the set small so OCR is not run on every possible filter.
    unique: list[OCRCandidate] = []
    seen = set()
    for candidate in candidates:
        if candidate.name in seen:
            continue
        seen.add(candidate.name)
        unique.append(candidate)
    return unique[:4]
