"""Swappable OCR engine. Real PaddleOCR adapter + a stub for dev/CI.

Phase-1 reality: OCR behaviour on this UI is itself under study, so the
engine is injectable and every read returns confidence for the recon §B map.
"""
from __future__ import annotations

import numpy as np

from .models import OCRLine


class OCREngine:
    def read(self, image: np.ndarray) -> list[OCRLine]:  # pragma: no cover
        raise NotImplementedError


class PaddleOCREngine(OCREngine):
    def __init__(self, lang: str = "chinese_cht"):
        from paddleocr import PaddleOCR
        self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    def read(self, image: np.ndarray) -> list[OCRLine]:
        result = self._ocr.ocr(image, cls=True)
        lines: list[OCRLine] = []
        if not result or result[0] is None:
            return lines
        for box, (text, conf) in result[0]:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            bbox = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            lines.append(OCRLine(text=text, conf=float(conf), bbox=bbox))
        # PaddleOCR returns top->bottom already; keep as-is.
        return lines


class StubOCREngine(OCREngine):
    """Returns scripted lines keyed by ROI for tests / dry runs.

    Inject a dict: {screenshot_id: {roi_name: [(text, conf), ...]}}.
    Call set_context(screenshot_id, roi_name) before each read, OR use the
    higher-level test harness. Kept minimal here.
    """
    def __init__(self, script: dict | None = None):
        self.script = script or {}
        self._key: tuple[str, str] | None = None

    def set_context(self, screenshot_id: str, roi_name: str) -> None:
        self._key = (screenshot_id, roi_name)

    def read(self, image: np.ndarray) -> list[OCRLine]:
        if self._key is None:
            return []
        sid, roi = self._key
        scripted = self.script.get(sid, {}).get(roi, [])
        return [OCRLine(text=t, conf=c, bbox=(0, i * 20, 100, i * 20 + 18))
                for i, (t, c) in enumerate(scripted)]


def make_engine(lang: str = "chinese_cht", stub: bool = False,
                script: dict | None = None) -> OCREngine:
    if stub:
        return StubOCREngine(script)
    return PaddleOCREngine(lang=lang)

