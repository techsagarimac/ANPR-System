"""Bounding-box helpers used by tracking and annotation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def centroid(self) -> tuple[float, float]:
        return (self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0

    def clip(self, width: int, height: int) -> "BBox":
        return BBox(
            x1=max(0, min(self.x1, width - 1)),
            y1=max(0, min(self.y1, height - 1)),
            x2=max(0, min(self.x2, width)),
            y2=max(0, min(self.y2, height)),
        )

    def iou(self, other: "BBox") -> float:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        inter_w = max(0, ix2 - ix1)
        inter_h = max(0, iy2 - iy1)
        inter = inter_w * inter_h
        union = self.area + other.area - inter
        if union <= 0:
            return 0.0
        return inter / union

    def as_xyxy(self) -> tuple[int, int, int, int]:
        return self.x1, self.y1, self.x2, self.y2
