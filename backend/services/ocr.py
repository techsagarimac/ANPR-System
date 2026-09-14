"""Plate-text recognition: PaddleOCR first, then RapidOCR if Paddle is unavailable."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from backend.config import settings
from backend.services.preprocessing import OCRCandidate, generate_ocr_candidates
from backend.services.validator import is_acceptable_ocr, validate_plate

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    raw_text: str
    normalized: str
    confidence: float
    is_valid_format: bool
    quality_score: float
    preprocessor: str
    accepted: bool


class PlateOCR:
    """Lazy OCR client. Prefers PaddleOCR; RapidOCR is a real ONNX fallback."""

    def __init__(self) -> None:
        self._ocr = None
        self._api = None
        self.status = "unloaded"
        self.detail: Optional[str] = None

    def load(self) -> None:
        if self._load_paddle() or self._load_rapid():
            return
        self.status = "unavailable"
        self.detail = "PaddleOCR and RapidOCR are not installed"
        logger.error("OCR unavailable: %s", self.detail)
        raise RuntimeError(self.detail)

    def _load_paddle(self) -> bool:
        try:
            from paddleocr import PaddleOCR
        except ImportError:
            logger.info("PaddleOCR is not installed; trying RapidOCR")
            return False
        try:
            try:
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang="en",
                    show_log=False,
                    use_gpu=False,
                )
                self._api = "paddle_v2"
            except TypeError:
                self._ocr = PaddleOCR(lang="en")
                self._api = "paddle_v3"
            self.status = "ready"
            self.detail = self._api
            logger.info("PaddleOCR ready (api=%s)", self._api)
            return True
        except Exception:
            logger.exception("Failed to initialize PaddleOCR")
            return False

    def _load_rapid(self) -> bool:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError:
            try:
                from rapidocr import RapidOCR
            except ImportError:
                return False
        try:
            self._ocr = RapidOCR()
            self._api = "rapidocr"
            self.status = "ready"
            self.detail = "rapidocr-onnxruntime"
            logger.info("RapidOCR ready (PaddleOCR ONNX models)")
            return True
        except Exception:
            logger.exception("Failed to initialize RapidOCR")
            return False

    def recognize(self, plate_bgr: np.ndarray) -> Optional[OCRResult]:
        if self._ocr is None:
            logger.error("OCR called before successful initialization")
            return None
        if plate_bgr is None or getattr(plate_bgr, "size", 0) == 0:
            logger.warning("Skipping OCR on empty plate image")
            return None

        best: Optional[OCRResult] = None
        try:
            candidates = generate_ocr_candidates(plate_bgr)
        except Exception:
            logger.exception("Plate preprocessing failed")
            candidates = [OCRCandidate(name="raw", image=plate_bgr)]

        for candidate in candidates[:3]:
            parsed = self._run_ocr(candidate.image)
            if not parsed:
                continue
            raw_text, confidence = parsed
            validation = validate_plate(raw_text)
            result = OCRResult(
                raw_text=raw_text,
                normalized=validation.normalized,
                confidence=confidence,
                is_valid_format=validation.is_valid_format,
                quality_score=validation.quality_score,
                preprocessor=candidate.name,
                accepted=is_acceptable_ocr(
                    validation, confidence, settings.ocr_confidence
                ),
            )
            logger.info(
                "OCR result text=%s conf=%.3f valid=%s preprocessor=%s",
                result.normalized or result.raw_text,
                result.confidence,
                result.is_valid_format,
                result.preprocessor,
            )
            if best is None or _score(result) > _score(best):
                best = result
            if result.accepted and result.is_valid_format and result.confidence >= 0.9:
                break
        return best

    def _run_ocr(self, image: np.ndarray) -> Optional[tuple[str, float]]:
        try:
            if self._api == "rapidocr":
                return _parse_rapid(self._ocr(image))
            if self._api == "paddle_v3" and hasattr(self._ocr, "predict"):
                return _parse_v3(self._ocr.predict(image))
            return _parse_v2(self._ocr.ocr(image, cls=True))
        except Exception:
            logger.exception("OCR inference failed")
            return None


def _score(result: OCRResult) -> float:
    bonus = 0.25 if result.is_valid_format else 0.0
    return result.confidence * 0.7 + result.quality_score * 0.3 + bonus


def _parse_rapid(output: Any) -> Optional[tuple[str, float]]:
    rows = output[0] if isinstance(output, tuple) else output
    if not rows:
        return None
    best_text = ""
    best_conf = -1.0
    for item in rows:
        try:
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("txt") or "").strip()
                conf = float(item.get("score") or item.get("confidence") or 0.0)
            elif isinstance(item, (list, tuple)) and len(item) >= 3:
                text = str(item[1]).strip()
                conf = float(item[2])
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                text = str(item[0]).strip()
                conf = float(item[1])
            else:
                continue
            if text and conf > best_conf:
                best_text, best_conf = text, conf
        except Exception:
            continue
    if best_conf < 0 or not best_text:
        return None
    return best_text, best_conf


def _parse_v2(output: Any) -> Optional[tuple[str, float]]:
    if not output:
        return None
    lines = output[0] if isinstance(output, list) and output and isinstance(output[0], list) else output
    if not lines:
        return None
    best_text = ""
    best_conf = -1.0
    for item in lines:
        try:
            text, conf = item[1]
            conf = float(conf)
            text = str(text).strip()
            if conf > best_conf and text:
                best_text, best_conf = text, conf
        except Exception:
            continue
    if best_conf < 0 or not best_text:
        return None
    return best_text, best_conf


def _parse_v3(output: Any) -> Optional[tuple[str, float]]:
    if not output:
        return None
    first = output[0] if isinstance(output, list) else output
    if isinstance(first, dict):
        texts = first.get("rec_text") or first.get("rec_texts") or first.get("text")
        scores = first.get("rec_score") or first.get("rec_scores") or first.get("score")
        if isinstance(texts, str):
            conf = float(scores) if scores is not None else 0.0
            return texts, conf
        if isinstance(texts, list) and texts:
            if isinstance(scores, list) and scores:
                paired = sorted(
                    zip(texts, scores),
                    key=lambda item: float(item[1]),
                    reverse=True,
                )
                return str(paired[0][0]), float(paired[0][1])
            return str(texts[0]), 0.0
    return None
