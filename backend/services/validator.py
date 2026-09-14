"""Indian-style registration-plate validation and OCR normalization.

Validation is a quality signal only. It is not proof of vehicle ownership
or identity, and it does not look up owner records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Standard private/commercial: MH12AB1234, DL1CAB1234, KA03M1234
STANDARD_PLATE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")
# Bharat series: 22BH1234AA
BHARAT_SERIES = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")
# Older / special-series flexible alnum used as a weak signal, not a hard rule
FLEXIBLE_ALNUM = re.compile(r"^[A-Z0-9]{6,12}$")

INVALID_CHARS = re.compile(r"[^A-Z0-9]")
CONFUSION_TO_DIGIT = str.maketrans({"O": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6"})
CONFUSION_TO_LETTER = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"})


@dataclass
class ValidationResult:
    original: str
    normalized: str
    is_valid_format: bool
    quality_score: float
    reason: str


def normalize_ocr_text(text: str) -> str:
    """Uppercase, strip spaces, and drop characters that cannot appear on a plate."""
    if not text:
        return ""
    cleaned = text.upper().replace(" ", "").replace("-", "").replace(".", "")
    cleaned = INVALID_CHARS.sub("", cleaned)
    return cleaned


def _positional_standard_fix(text: str) -> str | None:
    """Apply 0/O-style substitutions only in positions implied by a standard layout."""
    if not (8 <= len(text) <= 11):
        return None

    # Guess the digit-run after the state code: 1 or 2 digits.
    for district_len in (2, 1):
        series_max = len(text) - 2 - district_len - 4
        if series_max < 1 or series_max > 3:
            continue
        letters = text[:2]
        district = text[2 : 2 + district_len]
        series = text[2 + district_len : 2 + district_len + series_max]
        number = text[-4:]
        if len(letters + district + series + number) != len(text):
            continue
        candidate = (
            letters.translate(CONFUSION_TO_LETTER)
            + district.translate(CONFUSION_TO_DIGIT)
            + series.translate(CONFUSION_TO_LETTER)
            + number.translate(CONFUSION_TO_DIGIT)
        )
        if STANDARD_PLATE.match(candidate):
            return candidate
    return None


def _bharat_fix(text: str) -> str | None:
    if not (8 <= len(text) <= 10):
        return None
    if "BH" not in text and "8H" not in text and "B4" not in text:
        return None
    year = text[:2].translate(CONFUSION_TO_DIGIT)
    marker = "BH"
    rest = text[4:]
    if len(rest) < 5:
        return None
    digits = rest[:4].translate(CONFUSION_TO_DIGIT)
    suffix = rest[4:].translate(CONFUSION_TO_LETTER)
    candidate = year + marker + digits + suffix
    if BHARAT_SERIES.match(candidate):
        return candidate
    return None


def validate_plate(raw_text: str) -> ValidationResult:
    original = (raw_text or "").strip()
    normalized = normalize_ocr_text(original)

    if not normalized:
        return ValidationResult(original, "", False, 0.0, "empty")
    if len(normalized) < 6 or len(normalized) > 12:
        return ValidationResult(original, normalized, False, 0.15, "length")
    if len(set(normalized)) == 1:
        return ValidationResult(original, normalized, False, 0.05, "repeated_char")
    if not any(ch.isdigit() for ch in normalized):
        return ValidationResult(original, normalized, False, 0.1, "no_digits")
    if not any(ch.isalpha() for ch in normalized):
        return ValidationResult(original, normalized, False, 0.1, "no_letters")

    if STANDARD_PLATE.match(normalized) or BHARAT_SERIES.match(normalized):
        return ValidationResult(original, normalized, True, 1.0, "exact_format")

    fixed = _positional_standard_fix(normalized) or _bharat_fix(normalized)
    if fixed:
        return ValidationResult(original, fixed, True, 0.92, "positional_normalization")

    if FLEXIBLE_ALNUM.match(normalized) and 7 <= len(normalized) <= 11:
        return ValidationResult(original, normalized, False, 0.62, "plausible_alnum")

    return ValidationResult(original, normalized, False, 0.25, "malformed")


def is_acceptable_ocr(result: ValidationResult, ocr_confidence: float, min_ocr: float) -> bool:
    if not result.normalized:
        return False
    if result.quality_score < 0.5:
        return False
    if ocr_confidence < min_ocr and not result.is_valid_format:
        return False
    if result.is_valid_format and ocr_confidence >= max(0.35, min_ocr - 0.15):
        return True
    return ocr_confidence >= min_ocr and result.quality_score >= 0.6
