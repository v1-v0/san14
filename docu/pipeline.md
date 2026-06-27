## Pipeline Overview

Workbooks:
• **san14_dict.xlsx** — live data (1000 people · 218 places · patterns · factions)
• **san14_skeleton.xlsx** — regenerable structure from `build_skeleton.py` (schema v3)
All sheets are named tables. Loaded vocab feeds Stage 0.

| Stage | Name                                                               | Details                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ----- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **0** | **Load & Derive** _(san14_dict.xlsx → in-memory)_                  | Read sheets: `tblPeople`, `tblGeo`, `tblPatterns`, `tblFactions`<br/>Build in-memory:<br/>• **PEOPLE**: `name → [id,…]` map (names are **NOT** unique — see ⚠️) + length buckets **2–4**<br/>• **PLACES**: set + length buckets **1–3** (⚠️ single-char 據點 exist: 薊·吳·鄴·郯·魯…)<br/>• compiled regex rules (sorted by `priority`)<br/>• **FactionState** seeded from `tblFactions` (rulers ⊆ PEOPLE)<br/>▸ Factions are **NOT** a separate dict — a "…軍" token snaps to PEOPLE; ruler status is answered by FactionState (state, not vocabulary) |
| **1** | **Per-Screenshot** _(in turn order)_                               | **a.** Crop 3 ROIs: `date_box` · `ruler_box` · `event_log_box`<br/>**b.** OCR each (PaddleOCR `chinese_cht`) → raw lines<br/>⚠️ event log newest-on-top → `reverse()` to chronological                                                                                                                                                                                                                                                                                                                                                                 |
| **2** | **Dedup Across Turns** _(log scrolls)_                             | • align with previous capture (difflib longest-match)<br/>• keep only NEW lines                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **3** | **Clean + Entity Correction** _(key step)_                         | • strip noise, normalise 隊 / 軍 / 的<br/>• rapidfuzz snap → nearest PEOPLE / PLACES (length-bucketed)<br/>• "…軍" and "…隊" both snap to PEOPLE (one vocabulary)<br/>• ⚠️ **len-1 / len-2 tokens**: require exact or near-exact match (raise threshold) — short strings have no edit-distance buffer<br/>• record match score → `low_conf` flag                                                                                                                                                                                                       |
| **4** | **Parse Grammar** _(data-driven by `tblPatterns`, priority order)_ | For each line, try compiled rules low→high priority:<br/>• **MATCH** → fill slots by declared vocab type → structured record<br/>• ⚠️ if a `people` slot resolves to **multiple ids** → keep name, set `ambiguous_id`, defer to ruler/faction context (do not guess)<br/>• **NO MATCH** → skeleton-cluster (mask names+digits) → CONFIRM queue → human approves → append row to `tblPatterns` (learned, never re-asked)<br/>▸ Side-effect: ruler events (登庸 ruler / 滅止) update FactionState → `tblFactions`                                        |
| **5** | **Output**                                                         | append → `tblEvents` (schema v3)<br/>columns: `date` · `turn_period` · `ruler` · `action_type` · `subject` · `object` · `ambiguous_id` · `location` · `target_faction` · `value` · `success` · `confidence` · `raw_text`<br/>unresolved lines → `tblPending` for batch review                                                                                                                                                                                                                                                                          |

### Feedback Loops

- **Stage 4 confirm** ──► `tblPatterns` _(grammar grows)_
- **Stage 4 ruler events** ──► `tblFactions` _(rulers change)_

### Data-Driven Constraints (derived from loaded dict)

| Vocab  | Count | Length range | Notes                                                                                                      |
| ------ | ----- | ------------ | ---------------------------------------------------------------------------------------------------------- |
| people | 1000  | 2–4          | names **not unique**: 韓忠×2, 張承×2, 張南×2, 馬忠×2, 李豐×3 → resolve via `id`; defer with `ambiguous_id` |
| places | 218   | 1–3          | many single-char 據點 (薊·吳·鄴·郯·魯·宋·陳·燕·代·黃…) raise OCR/fuzzy risk                                |

### Schema Notes

- **schema_version: 3** — `tblEvents` gained `ambiguous_id` (after `object`); `success` boolean shifts to events column **K**.
- `meta_kv` exposes derived counts: `people_count`, `places_count`, `faction_count`, plus documented buckets `people_len_buckets=2-4`, `places_len_buckets=1-3`.
- Place slots in `capture` / `march` patterns use `.{1,3}?` to match the real 1–3 char place range.
