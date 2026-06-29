"""Stage 1 — Per-Screenshot. Crop ROIs, OCR, verify date monotonicity,
reverse the (newest-on-top) event log to chronological.

[KEEP+] in Phase 2. Emits ROI bbox+confidence to recon §B.
"""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from . import config
from .models import CaptureResult, GameDate, ROIResult, ScreenshotJob
from .ocr import OCREngine, StubOCREngine
from .recon import ReconSink

log = logging.getLogger("san14.capture")

_DATE_RE = re.compile(r"(?P<y>\d{2,4})\s*年\s*(?P<m>\d{1,2})\s*月")


class DateDecrease(Exception):
    pass


class UnreadableDate(Exception):
    pass


def _crop(img: Image.Image, frac) -> tuple[Image.Image, tuple[int, int, int, int]]:
    w, h = img.size
    x0, y0, x1, y1 = frac
    box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
    return img.crop(box), box


def parse_game_date(texts: list[str]) -> Optional[GameDate]:
    for t in texts:
        m = _DATE_RE.search(t.replace(" ", ""))
        if m:
            y = int(m["y"])
            if y < 100:           # tolerate 2-digit OCR; map naively
                y += 100
            return GameDate(year=y, month=int(m["m"]))
    return None


def capture(job: ScreenshotJob, engine: OCREngine, recon: ReconSink,
            running_max: Optional[GameDate]) -> tuple[CaptureResult, GameDate]:
    """Returns (CaptureResult, new running_max). Raises on quarantine cause."""
    img = Image.open(job.path).convert("RGB")

    rois: dict[str, ROIResult] = {}
    for name, frac in config.ROIS.items():
        crop, box = _crop(img, frac)
        if isinstance(engine, StubOCREngine):
            engine.set_context(job.screenshot_id, name)
        lines = engine.read(np.asarray(crop))
        roi = ROIResult(name=name, crop_box=box, lines=lines)
        rois[name] = roi
        recon.log_roi(job.screenshot_id, roi)   # feeds ROI Variance Map (§B)

    # (c) date_box must be readable and non-decreasing
    gd = parse_game_date(rois["date_box"].texts)
    if gd is None:
        raise UnreadableDate("date_box unreadable")
    if running_max is not None and gd.key < running_max.key:
        raise DateDecrease(f"{gd} < {running_max} (out-of-order / missed turn)")
    new_max = gd if running_max is None or gd.key > running_max.key else running_max

    # event log is newest-on-top -> reverse to chronological
    event_log = list(reversed(rois["event_log_box"].texts))

    result = CaptureResult(job=job, rois=rois, game_date=gd, event_log=event_log)
    return result, new_max


def quarantine_image(path: Path, reason: str) -> None:
    log.warning("quarantine %s : %s", path.name, reason)
    shutil.move(str(path), str(config.QUARANTINE_DIR / path.name))