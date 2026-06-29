"""Stage 0.5 — Ingest. Scan inbox -> ordered, resumed worklist.

[REPLACE] in Phase 2 by frame-reduction. Lexicographic stem order ==
chronological. Resume on meta.last_screenshot high-water mark.
"""
from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from . import config
from .models import ScreenshotJob

log = logging.getLogger("san14.ingest")


def _quarantine(path: Path, reason: str) -> None:
    log.warning("quarantine %s : %s", path.name, reason)
    shutil.move(str(path), str(config.QUARANTINE_DIR / path.name))


def build_worklist(last_screenshot: str | None) -> list[ScreenshotJob]:
    candidates: list[ScreenshotJob] = []

    for p in sorted(config.SCREENSHOTS_DIR.iterdir()):
        if not p.is_file():
            continue
        # (a) skip hidden / non-image
        if p.name.startswith(".") or p.suffix.lower() not in config.IMAGE_EXTS:
            log.debug("skip non-image %s", p.name)
            continue
        # (b) parse stem; non-conforming -> quarantine + warn
        m = config.STEM_RE.match(p.stem)
        if not m:
            _quarantine(p, "non-conforming filename")
            continue
        try:
            dt = datetime.strptime(m["d"] + m["t"], "%Y%m%d%H%M%S")
        except ValueError:
            _quarantine(p, "unparseable datetime in stem")
            continue
        candidates.append(ScreenshotJob(path=p, screenshot_id=p.stem, capture_dt=dt))

    # (c) sort lexicographically by stem (big-endian -> chronological)
    candidates.sort(key=lambda j: j.screenshot_id)

    # detect same-second collisions -> warn (stable sort keeps arbitrary order)
    for a, b in zip(candidates, candidates[1:]):
        if a.screenshot_id == b.screenshot_id:
            log.warning("same-second collision: %s (arbitrary tie order)",
                        a.screenshot_id)

    # (d) resume: skip stems <= last_screenshot; warn on older straggler
    worklist: list[ScreenshotJob] = []
    if last_screenshot:
        for j in candidates:
            if j.screenshot_id <= last_screenshot:
                log.warning("straggler with older/seen stem dropped in inbox: %s",
                            j.screenshot_id)
                continue
            worklist.append(j)
    else:
        worklist = candidates

    log.info("ingest: %d image(s) queued (resume cursor=%s)",
             len(worklist), last_screenshot or "<fresh>")
    return worklist
