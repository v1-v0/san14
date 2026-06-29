"""Orchestrator. Wires Stage 0 -> 5 in turn order with the commit discipline
and the recon side-outputs. Halt-or-skip behaviour on quarantine is
configurable (default: skip and continue)."""
from __future__ import annotations

import json
import logging

from . import config
from .models import GameDate
from .ocr import OCREngine, make_engine
from .recon import ReconSink
from .stage0_load import load_vocab
from .stage05_ingest import build_worklist
from .stage1_capture import (DateDecrease, UnreadableDate, capture,
                             quarantine_image)
from .stage2_dedup import new_lines
from .stage3_clean import EntityResolver, clean_line
from .stage4_parse import Stage4
from .stage5_commit import commit

log = logging.getLogger("san14.pipeline")


def _parse_last_date(s) -> GameDate | None:
    if not s:
        return None
    import re
    m = re.match(r"(\d+)年(\d+)月", str(s))
    return GameDate(int(m[1]), int(m[2])) if m else None


def _prev_log(dict_wb) -> list[str]:
    """Previous capture's event_log from persisted tblLogRaw (latest sid)."""
    rows = dict_wb.rows("tblLogRaw")
    if not rows:
        return []
    last_sid = max(r["screenshot_id"] for r in rows)
    seq = [r for r in rows if r["screenshot_id"] == last_sid]
    seq.sort(key=lambda r: r.get("seq", 0))
    return [r["line"] for r in seq]


def run(engine: OCREngine | None = None, halt_on_quarantine: bool = False
        ) -> dict:
    vocab, dict_wb = load_vocab()
    if not vocab.color_bands_calibrated:
        log.info("ColorBands uncalibrated -> Stage 4 colour demotion DISABLED")

    resolver = EntityResolver(vocab)
    stage4 = Stage4(vocab, resolver)
    recon = ReconSink()
    engine = engine or make_engine(config.OCR_LANG)

    last_sid = dict_wb.get_meta("last_screenshot")
    running_max = _parse_last_date(dict_wb.get_meta("last_date"))

    worklist = build_worklist(last_sid)
    prev_log = _prev_log(dict_wb)

    stats = {"committed": 0, "quarantined": 0, "events": 0, "pending": 0}

    for job in worklist:
        # --- Stage 1 ---------------------------------------------------
        try:
            cap, running_max = capture(job, engine, recon, running_max)
        except (DateDecrease, UnreadableDate) as e:
            quarantine_image(job.path, str(e))
            stats["quarantined"] += 1
            if halt_on_quarantine:
                log.error("halt: %s", e)
                break
            continue

        recon.log_layout_signal(job.screenshot_id, cap.rois)

        ruler_name = cap.rois["ruler_box"].texts[0] if cap.rois["ruler_box"].texts else ""
        date_str = str(cap.game_date)

        # --- Stage 2 ---------------------------------------------------
        fresh = new_lines(prev_log, cap.event_log)   # 0 new is valid

        # --- Stage 3 + 4 ----------------------------------------------
        events, pending, writebacks = [], [], []
        for raw in fresh:
            cl = clean_line(raw)
            if not cl.cleaned:
                continue
            ev, pend = stage4.parse(cl, ruler_name, date_str)
            if ev is None:
                assert pend is not None
                pend.screenshot_id = job.screenshot_id
                pending.append(pend)
                continue
            # find the matched pattern's stateful flag to drive the gate
            stateful = _stateful_for(vocab, ev.action_type)
            if stage4.apply_state_effect(stateful, ev):
                fid = stage4._faction_id(ev.target_faction or ev.ruler)
                if fid is not None:
                    writebacks.append({
                        "faction_id": fid,
                        **vocab.factions.by_id[fid],
                    })
            events.append(ev)

        # --- Stage 5 (commit, then move) ------------------------------
        commit(dict_wb, cap, events, pending, writebacks)
        stats["committed"] += 1
        stats["events"] += len(events)
        stats["pending"] += len(pending)

        prev_log = cap.event_log   # next iteration's "previous capture"

    log.info("run complete: %s", stats)
    return stats


def _stateful_for(vocab, action_type: str) -> str:
    for p in vocab.patterns:
        if p.action_type == action_type:
            return p.stateful
    return "none"
