"""Stage 0 — Load & Derive. Build the in-memory vocab/state from the dict.

PEOPLE name->[ids] (names NOT unique), PLACES set, compiled patterns
(sorted by priority), FactionState, ColorBands (uncalibrated => disabled).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from . import config
from .workbook import Workbook


@dataclass
class CompiledPattern:
    pattern_id: str
    action_type: str
    priority: int
    regex: re.Pattern
    slot_types: dict[str, str]      # group_name -> 'people'|'places'|'raw'
    stateful: str                   # 'none'|'ruler'|'territory'|'destroy'|'cond'
    enabled: bool
    raw_example: str = ""


@dataclass
class FactionState:
    """Live state seeded from tblFactions; mutated by Stage 4 ruler events."""
    by_id: dict = field(default_factory=dict)        # faction_id -> dict
    ruler_ids: set[int] = field(default_factory=set)

    @classmethod
    def from_rows(cls, rows: list[dict]) -> "FactionState":
        st = cls()
        for r in rows:
            fid = r.get("faction_id")
            rid = r.get("ruler_id")
            st.by_id[fid] = {
                "faction_name": r.get("faction_name"),
                "ruler_id": rid,
                "ruler_name": r.get("ruler_name"),
                "active": bool(r.get("active", True)),
            }
            if rid is not None:
                st.ruler_ids.add(rid)
        return st

    def is_ruler(self, person_id: int) -> bool:
        return person_id in self.ruler_ids

    def set_ruler(self, faction_id, ruler_id, ruler_name) -> None:
        f = self.by_id.setdefault(faction_id, {})
        old = f.get("ruler_id")
        if old in self.ruler_ids:
            self.ruler_ids.discard(old)
        f.update(ruler_id=ruler_id, ruler_name=ruler_name, active=True)
        if ruler_id is not None:
            self.ruler_ids.add(ruler_id)

    def destroy(self, faction_id) -> None:
        f = self.by_id.get(faction_id)
        if f:
            f["active"] = False
            self.ruler_ids.discard(f.get("ruler_id"))


@dataclass
class Vocab:
    people_by_name: dict[str, list[int]]
    people_by_len: dict[int, set[str]]
    places: set[str]
    places_by_len: dict[int, set[str]]
    patterns: list[CompiledPattern]          # sorted low->high priority
    factions: FactionState
    color_bands_calibrated: bool


def _bucket(names, lengths) -> dict[int, set[str]]:
    out = {n: set() for n in lengths}
    for nm in names:
        L = len(nm)
        if L in out:
            out[L].add(nm)
    return out


def load_vocab(dict_path=config.DICT_XLSX) -> tuple[Vocab, Workbook]:
    wb = Workbook(dict_path)

    # PEOPLE — names NOT unique => name -> [ids]
    people_by_name: dict[str, list[int]] = {}
    for r in wb.rows("tblPeople"):
        nm, pid = r.get("name"), r.get("id")
        if nm is None or pid is None:
            continue
        people_by_name.setdefault(str(nm), []).append(pid)
        
    people_by_len = _bucket(people_by_name.keys(), config.PEOPLE_LEN_BUCKETS)

    # PLACES — set + buckets 1..3 (single-char 據點 exist)
    places = {str(r["name"]) for r in wb.rows("tblGeo") if r.get("name")}
    places_by_len = _bucket(places, config.PLACES_LEN_BUCKETS)

    # PATTERNS — compile, sort by priority ascending (try low->high)
    patterns: list[CompiledPattern] = []
    for r in wb.rows("tblPatterns"):
        if not r.get("regex"):
            continue
        slot_types = json.loads(r.get("slot_types") or "{}")
        patterns.append(CompiledPattern(
            pattern_id=str(r.get("pattern_id")),
            action_type=str(r.get("action_type")),
            priority=int(r.get("priority", 100)),
            regex=re.compile(str(r["regex"])),
            slot_types=slot_types,
            stateful=str(r.get("stateful") or "none"),
            enabled=bool(r.get("enabled", True)),
            raw_example=str(r.get("raw_example") or ""),
        ))
    patterns.sort(key=lambda p: p.priority)

    # FactionState
    factions = FactionState.from_rows(wb.rows("tblFactions"))

    # ColorBands — calibrated only if no empty HSV cells
    cb_rows = wb.rows("tblColorBands")
    calibrated = bool(cb_rows) and all(
        all(r.get(k) not in (None, "") for k in
            ("h_lo", "h_hi", "s_lo", "s_hi", "v_lo", "v_hi"))
        for r in cb_rows
    )

    vocab = Vocab(
        people_by_name=people_by_name,
        people_by_len=people_by_len,
        places=places,
        places_by_len=places_by_len,
        patterns=patterns,
        factions=factions,
        color_bands_calibrated=calibrated,
    )
    return vocab, wb
