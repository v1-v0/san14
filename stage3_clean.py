"""Stage 3 — Clean + Entity Correction.

Line cleaning (noise strip, 隊/軍/的 normalise, 港口 suffix strip in code)
happens here. The fuzzy snap to PEOPLE/PLACES needs the slot's vocab type,
so EntityResolver lives here but is CALLED from Stage 4 during slot-fill.
No alias table by design.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz, process

from . import config
from .models import CleanLine, Resolution
from .stage0_load import Vocab

# strip obvious OCR junk; keep CJK, digits, a few separators
_JUNK_RE = re.compile(r"[^\u4e00-\u9fff0-9（）()・･…→\-]")
_PORT_RE = re.compile(r"港$")


def clean_line(raw: str, low_conf: bool = False) -> CleanLine:
    s = raw.strip()
    s = s.replace("隊", "軍")            # normalise 隊 -> 軍 (one vocabulary)
    s = s.replace("的", "")             # drop possessive noise
    s = _JUNK_RE.sub("", s)
    s = re.sub(r"\s+", "", s)
    return CleanLine(raw=raw, cleaned=s, low_conf=low_conf)


class EntityResolver:
    def __init__(self, vocab: Vocab):
        self.v = vocab

    # --- public: called per slot by Stage 4 ---------------------------
    def resolve_people(self, token: str) -> Resolution:
        token = self._strip_unit_suffix(token)   # …軍 / …隊 already normalised
        return self._snap(token, kind="people")

    def resolve_places(self, token: str) -> Resolution:
        token = self._port_strip(token)
        return self._snap(token, kind="places")

    # --- internals ----------------------------------------------------
    @staticmethod
    def _strip_unit_suffix(token: str) -> str:
        # "…軍" tokens snap to PEOPLE; trailing 軍 is decoration
        return token[:-1] if token.endswith("軍") and len(token) > 2 else token

    def _port_strip(self, token: str) -> str:
        # 港口 suffix strip in code (高唐港 -> 高唐) only if result is a place
        if _PORT_RE.search(token):
            stem = token[:-1]
            if stem in self.v.places:
                return stem
        return token

    def _snap(self, token: str, kind: str) -> Resolution:
        if not token:
            return Resolution(name=token, ids=[], score=0.0, low_conf=True)

        L = len(token)
        threshold = (config.FUZZY_THRESHOLD_SHORT if L <= 2
                     else config.FUZZY_THRESHOLD_LONG)

        if kind == "people":
            # exact first (names not unique -> may return many ids)
            if token in self.v.people_by_name:
                ids = list(self.v.people_by_name[token])
                return Resolution(name=token, ids=ids, score=100.0)
            bucket = self.v.people_by_len.get(L, set())
            # short tokens: only exact/near-exact within bucket
            best = self._best(token, bucket, threshold)
            if best is None:
                return Resolution(name=token, ids=[], score=0.0, low_conf=True)
            name, score = best
            ids = list(self.v.people_by_name.get(name, []))
            return Resolution(name=name, ids=ids, score=score,
                              low_conf=score < config.FUZZY_THRESHOLD_LONG)

        # places
        if token in self.v.places:
            return Resolution(name=token, ids=[], score=100.0)
        bucket = self.v.places_by_len.get(L, set())
        best = self._best(token, bucket, threshold)
        if best is None:
            return Resolution(name=token, ids=[], score=0.0, low_conf=True)
        name, score = best
        return Resolution(name=name, ids=[], score=score,
                          low_conf=score < config.FUZZY_THRESHOLD_LONG)

    @staticmethod
    def _best(token: str, bucket: set[str], threshold: float):
        if not bucket:
            return None
        hit = process.extractOne(token, bucket, scorer=fuzz.ratio,
                                 score_cutoff=threshold)
        if hit is None:
            return None
        name, score, _ = hit
        return name, float(score)
    