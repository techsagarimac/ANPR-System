"""Preprocessing tests. Require OpenCV."""

from __future__ import annotations

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from backend.services.preprocessing import generate_ocr_candidates, resize_plate


def test_generate_candidates_from_synthetic_plate():
    image = np.full((40, 160, 3), 40, dtype=np.uint8)
    cv2.putText(image, "MH12AB", (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 1)
    candidates = generate_ocr_candidates(image)
    names = {item.name for item in candidates}
    assert "resized_color" in names
    assert "grayscale" in names
    assert len(candidates) <= 4


def test_resize_increases_small_plates():
    tiny = np.zeros((20, 50, 3), dtype=np.uint8)
    resized = resize_plate(tiny, min_width=240, min_height=80)
    assert resized.shape[1] >= 240
    assert resized.shape[0] >= 80
