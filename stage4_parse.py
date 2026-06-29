"""Stage 4 — Parse Grammar. Data-driven by tblPatterns, tried low->high
priority. Fills slots by declared vocab type; defers multi-id people with
ambiguous_id (NEVER guesses). NO MATCH -> skeleton-cluster -> CONFIRM queue.
Ruler events update FactionState.

[KEEP] in Phase 2 — the stateful side-effect gate is the prime reusable asset.
"""
from __future__ import annotations

import json
import logging
import re

from . import config
from .models import CleanLine, ParsedEvent, PendingLine
from .stage0_load import CompiledPattern, Vocab
from .stage3_clean import EntityResolver

log = logging.getLogger("san14.parse")

_DIGIT_RE = re.compile(r"\d+")


class Stage4:
    def __init__(self, vocab: Vocab, resolver: EntityResolver):
        self.v = vocab
        self.r = resolver

    # --- main entry ---------------------------------------------------
    def parse(self, line: CleanLine, ruler_name: str, date_str: str
              ) -> tuple[ParsedEvent | None, PendingLine | None]:
        text = line.cleaned
        for pat in self.v.patterns:                 # already sorted low->high
            if not pat.enabled:
                continue
            m = pat.regex.search(text)
            if not m:
                continue
            ev = self._fill(pat, m, line, ruler_name, date_str)
            # multi-id people slot that couldn't be disambiguated -> defer,
            # but still emit the event row carrying ambiguous_id.
            return ev, None

        # NO MATCH -> skeleton + confirm queue
        skel = self._skeletonize(text)
        pend = PendingLine(screenshot_id="", raw_text=line.raw,
                           reason="no_match", skeleton=skel)
        return None, pend

    # --- slot filling -------------------------------------------------
    def _fill(self, pat: CompiledPattern, m: re.Match, line: CleanLine,
              ruler_name: str, date_str: str) -> ParsedEvent:
        ev = ParsedEvent(date=date_str, ruler=ruler_name,
                         action_type=pat.action_type, raw_text=line.raw,
                         success=True)
        ambiguous: dict[str, list[int]] = {}
        scores: list[float] = []
        low_conf = line.low_conf

        for group, vocab_type in pat.slot_types.items():
            if group not in m.groupdict() or m.group(group) is None:
                continue
            token = m.group(group)

            if vocab_type == "raw":
                self._set_slot(ev, group, token)
                continue

            if vocab_type == "people":
                res = self.r.resolve_people(token)
                scores.append(res.score)
                low_conf = low_conf or res.low_conf
                self._set_slot(ev, group, res.name)
                if res.ambiguous:
                    # keep name, defer — do NOT guess (dedup_key deferred)
                    ambiguous[res.name] = res.ids
                continue

            if vocab_type == "places":
                res = self.r.resolve_places(token)
                scores.append(res.score)
                low_conf = low_conf or res.low_conf
                self._set_slot(ev, group, res.name)

        if ambiguous:
            ev.ambiguous_id = json.dumps(ambiguous, ensure_ascii=False)
        ev.confidence = (min(scores) / 100.0) if scores else 1.0
        if low_conf:
            ev.confidence = min(ev.confidence, 0.5)

        # stateful side-effect (returns nothing; mutates FactionState lazily
        # via apply_state_effect, called by pipeline after row is accepted)
        ev.value = ev.value or ""
        return ev

    @staticmethod
    def _set_slot(ev: ParsedEvent, group: str, value: str) -> None:
        if hasattr(ev, group):
            setattr(ev, group, value)

    # --- stateful gate ------------------------------------------------
    def apply_state_effect(self, pat_stateful: str, ev: ParsedEvent
                           ) -> bool:
        """Mutate FactionState for ruler events. Returns True if applied.

        'cond' (appoint) is stateful only when office marks a ruler.
        Territory/destroy/succession handlers are conservative — several are
        marked (verify) in the Exit Artifact §A; confirm semantics before
        trusting them in Phase 2.
        """
        st = self.v.factions
        kind = pat_stateful

        if kind == "cond":  # appoint
            if ev.office in config.RULER_OFFICES:
                kind = "ruler"
            else:
                return False

        if kind == "none":
            return False

        if kind == "destroy":               # 滅止
            fid = self._faction_id(ev.target_faction)
            if fid is not None:
                st.destroy(fid)
                return True

        elif kind in ("ruler", "succession"):   # 登庸 ruler / 当主交代
            fid = self._faction_id(ev.target_faction or ev.ruler)
            new_ruler = ev.subject or ev.object
            ids = self.v.people_by_name.get(new_ruler, [])
            rid = ids[0] if len(ids) == 1 else None   # do not guess if ambiguous
            if fid is not None:
                st.set_ruler(fid, rid, new_ruler)
                return True

        elif kind == "territory":            # capture -> location changes hands
            # Phase-1 (verify): territory model not fully tracked here.
            log.debug("territory effect noted for %s (not persisted)",
                      ev.location)
            return False

        return False

    def _faction_id(self, name: str):
        for fid, f in self.v.factions.by_id.items():
            if f.get("faction_name") == name:
                return fid
        return None

    # --- skeleton clustering ------------------------------------------
    def _skeletonize(self, text: str) -> str:
        s = _DIGIT_RE.sub("<NUM>", text)
        # mask known entities longest-first (cheap; Phase-1 volume is small)
        for nm in sorted(self.v.people_by_name.keys(), key=len, reverse=True):
            if nm and nm in s:
                s = s.replace(nm, "<P>")
        for nm in sorted(self.v.places, key=len, reverse=True):
            if nm and nm in s:
                s = s.replace(nm, "<L>")
        return s
    
    