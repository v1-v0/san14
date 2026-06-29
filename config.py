"""Stage-wide configuration. Paths, regexes, thresholds, ROI fractions.

Folders here are RUNTIME CONFIG, not dict sheets (see pipeline.md).
ROI rectangles are FRACTIONAL PLACEHOLDERS — calibrate them from the
Phase-1 ROI Variance Map (recon Exit Artifact §B).
"""
from __future__ import annotations

import re
from pathlib import Path

# --- Workbooks -------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DICT_XLSX = BASE_DIR / "san14_dict.xlsx"
SKELETON_XLSX = BASE_DIR / "san14_skeleton.xlsx"

# --- Runtime folders (NOT dict sheets) ------------------------------------
SCREENSHOTS_DIR = BASE_DIR / "screenshots"   # inbox
PROCESSED_DIR = BASE_DIR / "processed"       # committed OK
QUARANTINE_DIR = BASE_DIR / "quarantine"     # bad image (name/OCR/order)
RECON_DIR = BASE_DIR / "recon"               # recon side-outputs (jsonl)

for _d in (SCREENSHOTS_DIR, PROCESSED_DIR, QUARANTINE_DIR, RECON_DIR):
    _d.mkdir(exist_ok=True)

# --- Ingest ---------------------------------------------------------------
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}
STEM_RE = re.compile(r"^DECK-(?P<d>\d{8})-(?P<t>\d{6})$")

# --- Schema ---------------------------------------------------------------
SCHEMA_VERSION = 4

# tblEvents column order (success MUST land at column M = 13th).
EVENT_COLUMNS = [
    "date", "turn_period", "ruler", "action_type", "subject", "object",
    "issuer", "ambiguous_id", "location", "target_faction", "office",
    "value", "success", "confidence", "raw_text",
]
assert EVENT_COLUMNS[12] == "success", "success must be column M (index 12)"

# --- Vocabulary facts (from loaded dict) ----------------------------------
ISSUER_ONLY_IDS = {1001}            # 獻帝 — referenced by appoint, never an actor
PEOPLE_LEN_BUCKETS = (2, 3, 4)
PLACES_LEN_BUCKETS = (1, 2, 3)

# Offices that, when filled by `appoint`, make the event STATEFUL (ruler case).
# Phase-1 TODO: confirm the exact in-game strings; conservative default below.
RULER_OFFICES = {"君主", "当主", "當主"}

# --- Fuzzy thresholds (rapidfuzz, 0..100) ---------------------------------
FUZZY_THRESHOLD_LONG = 82     # len >= 3 : edit-distance buffer exists
FUZZY_THRESHOLD_SHORT = 96    # len 1-2 : raise threshold, no buffer

# --- OCR ------------------------------------------------------------------
OCR_LANG = "chinese_cht"

# --- ROIs as (x0, y0, x1, y1) fractions of (width, height) ----------------
# PLACEHOLDERS — recon §B replaces these with calibrated, evidence-based boxes.
ROIS = {
    "date_box":      (0.00, 0.00, 0.22, 0.06),
    "ruler_box":     (0.22, 0.00, 0.55, 0.06),
    "event_log_box": (0.62, 0.45, 1.00, 1.00),
}

# Colour-based demotion (Stage 4) stays DISABLED until tblColorBands filled.
COLOR_DEMOTION_ENABLED = False
