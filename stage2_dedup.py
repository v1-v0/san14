"""Stage 2 — Dedup Across Turns. difflib longest-match against the PREVIOUS
capture's persisted event_log (tblLogRaw, keyed by screenshot_id).

[REPLACE] in Phase 2 by the temporal/positional log-tracker.
0 new lines is VALID (re-snap without scroll).
"""
from __future__ import annotations

import difflib
import logging

log = logging.getLogger("san14.dedup")


def new_lines(prev_lines: list[str], curr_lines: list[str]) -> list[str]:
    """Keep only lines in curr after the last overlap with prev."""
    if not prev_lines:
        return list(curr_lines)
    sm = difflib.SequenceMatcher(a=prev_lines, b=curr_lines, autojunk=False)
    last_b_end = 0
    for blk in sm.get_matching_blocks():
        if blk.size:
            last_b_end = max(last_b_end, blk.b + blk.size)
    fresh = curr_lines[last_b_end:]
    log.info("dedup: %d prev / %d curr -> %d new", len(prev_lines),
             len(curr_lines), len(fresh))
    return fresh

