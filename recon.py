"""Recon side-outputs — the actual Phase-1 deliverables (Exit Artifact).

§B ROI Variance Map  : per-screenshot ROI bbox + OCR confidence (jsonl)
§C Layout States      : records cheap detection signals (does not over-claim)
§A Taxonomy           : exported from tblPatterns + curated 'stateful' column
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .models import ROIResult
from .workbook import Workbook


class ReconSink:
    def __init__(self, base: Path = config.RECON_DIR):
        self.roi_path = base / "roi_variance.jsonl"
        self.layout_path = base / "layout_states.jsonl"

    def log_roi(self, screenshot_id: str, roi: ROIResult) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "screenshot_id": screenshot_id,
            "roi": roi.name,
            "crop_box": roi.crop_box,
            "n_lines": len(roi.lines),
            "mean_conf": round(roi.mean_conf, 4),
            "line_bboxes": [l.bbox for l in roi.lines],
        }
        with self.roi_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def log_layout_signal(self, screenshot_id: str, rois: dict[str, ROIResult]
                          ) -> None:
        """Record evidence for layout-state enumeration (§C). We log signals;
        we do NOT assert a state we haven't learned yet."""
        rec = {
            "screenshot_id": screenshot_id,
            "log_box_conf": round(rois["event_log_box"].mean_conf, 4),
            "log_box_lines": len(rois["event_log_box"].lines),
            "date_box_conf": round(rois["date_box"].mean_conf, 4),
            "ruler_box_conf": round(rois["ruler_box"].mean_conf, 4),
            # heuristic candidate (provisional, for human review only)
            "candidate_state": _candidate_state(rois),
        }
        with self.layout_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _candidate_state(rois: dict[str, ROIResult]) -> str:
    log_conf = rois["event_log_box"].mean_conf
    top_ok = rois["date_box"].mean_conf > 0.6 and rois["ruler_box"].mean_conf > 0.6
    if log_conf < 0.2 and top_ok:
        return "event_modal?"      # top bar readable, log occluded
    if log_conf < 0.2 and not top_ok:
        return "menu_open|loading?"
    return "main_view?"


def export_taxonomy(dict_path: Path = config.DICT_XLSX) -> list[dict]:
    """Project tblPatterns into the §A taxonomy view (template + stateful)."""
    wb = Workbook(dict_path)
    out = []
    for r in wb.rows("tblPatterns"):
        out.append({
            "action_type": r.get("action_type"),
            "pattern_id": r.get("pattern_id"),
            "stateful": r.get("stateful") or "none",
            "slot_types": r.get("slot_types"),
            "raw_example": r.get("raw_example"),
            "enabled": r.get("enabled"),
        })
    return out
