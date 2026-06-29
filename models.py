"""Plain data carriers passed between stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class GameDate:
    """In-game date — the independent witness for turn order (Stage 1)."""
    year: int
    month: int

    @property
    def key(self) -> tuple[int, int]:
        return (self.year, self.month)

    def __str__(self) -> str:
        return f"{self.year}年{self.month}月"


@dataclass
class ScreenshotJob:
    """One inbox image after ingest (Stage 0.5)."""
    path: Path
    screenshot_id: str          # filename stem, e.g. DECK-20260627-171212
    capture_dt: datetime        # wall-clock parsed from stem (NOT in-game date)


@dataclass
class OCRLine:
    text: str
    conf: float
    bbox: tuple[int, int, int, int]   # x0,y0,x1,y1 in ROI pixel space


@dataclass
class ROIResult:
    name: str
    crop_box: tuple[int, int, int, int]   # pixel box actually cropped
    lines: list[OCRLine] = field(default_factory=list)

    @property
    def mean_conf(self) -> float:
        if not self.lines:
            return 0.0
        return sum(l.conf for l in self.lines) / len(self.lines)

    @property
    def texts(self) -> list[str]:
        return [l.text for l in self.lines]


@dataclass
class CaptureResult:
    """Stage 1 output for one screenshot."""
    job: ScreenshotJob
    rois: dict[str, ROIResult]
    game_date: Optional[GameDate]
    event_log: list[str]        # chronological (already reversed)


@dataclass
class CleanLine:
    """Stage 3 output: normalised text + provenance."""
    raw: str
    cleaned: str
    low_conf: bool = False


@dataclass
class Resolution:
    """Result of resolving a token against PEOPLE / PLACES."""
    name: str
    ids: list[int] = field(default_factory=list)   # >1 => ambiguous
    score: float = 100.0
    low_conf: bool = False

    @property
    def ambiguous(self) -> bool:
        return len(self.ids) > 1


@dataclass
class ParsedEvent:
    """Stage 4 structured record (becomes a tblEvents row in Stage 5)."""
    date: str = ""
    turn_period: str = ""
    ruler: str = ""
    action_type: str = ""
    subject: str = ""
    object: str = ""
    issuer: str = ""
    ambiguous_id: str = ""      # serialised name->ids when a slot is ambiguous
    location: str = ""
    target_faction: str = ""
    office: str = ""
    value: str = ""
    success: Optional[bool] = None
    confidence: float = 1.0
    raw_text: str = ""

    def as_row(self, columns: list[str]) -> list:
        return [getattr(self, c) for c in columns]


@dataclass
class PendingLine:
    screenshot_id: str
    raw_text: str
    reason: str          # 'no_match' | 'deferred_stateful' | 'low_conf'
    skeleton: str = ""

