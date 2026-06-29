"""Stage 5 — Output & Commit.

COMMIT ORDER (per image, last step): write tblEvents -> advance
meta.last_screenshot -> move image to processed/. NEVER move before commit.
A crash before the move leaves the image in the inbox; the next run
reprocesses and Stage 2 absorbs the duplication.
"""
from __future__ import annotations

import logging
import shutil

from . import config
from .models import CaptureResult, ParsedEvent, PendingLine
from .workbook import Workbook

log = logging.getLogger("san14.commit")


def commit(dict_wb: Workbook, capture: CaptureResult,
           events: list[ParsedEvent], pending: list[PendingLine],
           faction_writebacks: list[dict]) -> None:
    sid = capture.job.screenshot_id

    # 1) write tblEvents
    if events:
        rows = [e.as_row(config.EVENT_COLUMNS) for e in events]
        dict_wb.append_rows("tblEvents", rows)

    # persist raw log for Stage 2 of the NEXT capture (keyed by screenshot_id)
    log_rows = [[sid, i, txt] for i, txt in enumerate(capture.event_log)]
    if log_rows:
        dict_wb.append_rows("tblLogRaw", log_rows)

    # unresolved lines -> tblPending (batch review)
    if pending:
        prows = [[sid, p.raw_text, p.reason, p.skeleton] for p in pending]
        dict_wb.append_rows("tblPending", prows)

    # faction state writeback (ruler events)
    for wb in faction_writebacks:
        dict_wb.upsert("tblFactions", "faction_id", wb["faction_id"], wb)

    # refresh derived meta counts
    dict_wb.set_meta("pattern_count", len(dict_wb.rows("tblPatterns")))

    # 2) advance high-water mark, then SAVE (this is the durable commit point)
    dict_wb.set_meta("last_screenshot", sid)
    if capture.game_date is not None:
        dict_wb.set_meta("last_date", str(capture.game_date))
    dict_wb.save()
    log.info("committed %s : %d event(s), %d pending", sid,
             len(events), len(pending))

    # 3) ONLY now move the image
    src = capture.job.path
    if src.exists():
        shutil.move(str(src), str(config.PROCESSED_DIR / src.name))

