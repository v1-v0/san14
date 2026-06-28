# Pipeline (Phase 1 — Screenshot Reconnaissance)

## Phase Context

**Phase 1 is reconnaissance, not production.** The screenshot pipeline below runs to study
the problem space ahead of Phase 2 (live/recorded video). Its **real deliverable is the
Phase-1 Exit Artifact** (taxonomy · ROI variance · layout states) at the end of this doc —
the extracted `tblEvents` is a byproduct that proves the study, not the goal.

▸ **"Done" = coverage criteria met** (every event type catalogued, every ROI variance
characterised, every layout state enumerated) — **not** "the pipeline runs clean."
▸ **Reuse legend** — each stage is marked for Phase 2: **[KEEP]** survives unchanged ·
**[KEEP+]** survives and is _improved_ by video's wall-clock · **[REPLACE]** is
screenshot-specific and gets superseded by Phase-2 upstream stages (frame-reduction +
log-tracker).
▸ **Out of scope for Phase 1 (the temporal axis).** Static captures cover _what_ and _where_
toward ~100% and the _when / how-it-moves_ axis toward ~0%. Animation/settle timing, scroll
dynamics, manual-scrollback appearance, line-persistence and date-advance _rate_, and the
live-vs-recorded scope decision are **known unknowns** requiring a dedicated Phase-2 video
recon pass. **This statement is held and reviewed after Phase 1 progress.**

## Pipeline Overview

Workbooks:
• **san14_dict.xlsx** — live data (1001 people · 218 places · patterns · factions · color_bands)
• **san14_skeleton.xlsx** — regenerable structure from `build_skeleton.py` (schema v4)
All sheets are named tables. Loaded vocab feeds Stage 0.

Folders (runtime config, **not** dict sheets):
• **`screenshots/`** — inbox; drop captures here. Filename = `DECK-yyyymmdd-hhmmss.jpg` (stem is the `screenshot_id`)
• **`processed/`** — archived after successful commit (clean out manually)
• **`quarantine/`** — images that failed ingest/OCR/monotonicity (manual review)

| Stage               | Name                                                               | Details                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **0** _[KEEP]_      | **Load & Derive** _(san14_dict.xlsx → in-memory)_                  | Read sheets: `tblPeople`, `tblGeo`, `tblPatterns`, `tblFactions`, `tblColorBands`<br/>Build in-memory:<br/>• **PEOPLE**: `name → [id,…]` map (names are **NOT** unique — see ⚠️) + length buckets **2–4**<br/>• **PLACES**: set + length buckets **1–3** (⚠️ single-char 據點 exist: 薊·吳·鄴·郯·魯…)<br/>• compiled regex rules (sorted by `priority`)<br/>• **FactionState** seeded from `tblFactions` (rulers ⊆ PEOPLE)<br/>• **ColorBands**: HSV ranges per role — ⚠️ **currently uncalibrated (empty cells)**; colour-based demotion in Stage 4 stays **disabled** until filled<br/>▸ Factions are **NOT** a separate dict — a "…軍" token snaps to PEOPLE; ruler status is answered by FactionState (state, not vocabulary)<br/>▸ 獻帝 (id 1001) is **issuer-only** — referenced by `appoint`, not an actor                                                                                                                                                                                                                                                                    |
| **0.5** _[REPLACE]_ | **Ingest** _(scan `screenshots/` → ordered worklist)_              | **a.** Scan inbox; **skip** hidden/non-image files (`.DS_Store`, wrong ext)<br/>**b.** Parse stem `DECK-(?P<d>\d{8})-(?P<t>\d{6})` → `screenshot_id` + capture-datetime; **non-conforming name → `quarantine/` + warn**<br/>**c.** **Sort lexicographically** = chronological (big-endian stem; no integer-pad trap)<br/>**d.** **Resume**: skip stems ≤ `meta.last_screenshot` (cross-run high-water mark); a straggler with an _older_ stem dropped into the inbox → warn<br/>⚠️ same-second collision (equal `hhmmss`) → stable sort, **warn** (arbitrary tie order)<br/>▸ hand ordered paths to Stage 1; capture-time order is the _assumed_ turn order, **verified** against in-game date in Stage 1<br/>▸ **Phase 2:** replaced by frame-reduction (sample → per-ROI perceptual-hash gate → candidate frames + wall-clock ts)                                                                                                                                                                                                                                                  |
| **1** _[KEEP+]_     | **Per-Screenshot** _(in turn order)_                               | **a.** Crop 3 ROIs: `date_box` · `ruler_box` · `event_log_box`<br/>**b.** OCR each (PaddleOCR `chinese_cht`) → raw lines<br/>**c.** ⚠️ **in-game date must be non-decreasing** across the worklist (multi-capture/turn → equal dates are **normal**). A _decrease_ = out-of-order/missed turn → **whole image to `quarantine/`**, halt-or-skip; unreadable `date_box` → quarantine<br/>⚠️ event log newest-on-top → `reverse()` to chronological<br/>▸ **Recon side-output:** log each ROI's detected bounding box + OCR confidence → feeds **ROI Variance Map**<br/>▸ **Phase 2:** ROI-crop/OCR kept; monotonicity check _improved_ — wall-clock disambiguates a date-decrease (replay/scrollback vs. genuine regression)                                                                                                                                                                                                                                                                                                                                                           |
| **2** _[REPLACE]_   | **Dedup Across Turns** _(log scrolls / repeat captures)_           | • align with **previous capture's** `event_log` (difflib longest-match)<br/>• keep only NEW lines<br/>▸ previous capture read from **persisted state** (`tblLogRaw` keyed by `screenshot_id`), **not** disk adjacency — archiving moves files out of the inbox<br/>▸ several captures of one turn overlap heavily → **0 new lines is valid** (re-snap without scroll), not an error<br/>▸ **Phase 2:** superseded by the **log-tracker** — content-dedup alone is unsafe in video (temporal-dup ≠ content-dup: a _recurring_ event produces an identical line). Tracker emits on **confirmed fresh insertion** (absence-gap / scroll-structure), not on text-visibility                                                                                                                                                                                                                                                                                                                                                                                                              |
| **3** _[KEEP]_      | **Clean + Entity Correction** _(key step)_                         | • strip noise, normalise 隊 / 軍 / 的<br/>• **港口 suffix strip** (e.g. 高唐港 → 高唐) done **in code** — no alias table by design<br/>• rapidfuzz snap → nearest PEOPLE / PLACES (length-bucketed)<br/>• "…軍" and "…隊" both snap to PEOPLE (one vocabulary)<br/>• ⚠️ **len-1 / len-2 tokens**: require exact or near-exact match (raise threshold) — short strings have no edit-distance buffer<br/>• record match score → `low_conf` flag                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **4** _[KEEP]_      | **Parse Grammar** _(data-driven by `tblPatterns`, priority order)_ | For each line, try compiled rules low→high priority:<br/>• **MATCH** → fill slots by declared vocab type (`people` / `places` / `raw`) → structured record<br/>• `appoint` fills `issuer` (people) + `office` (raw); `capture` parenthetical 所屬於… is matched non-capturing (validation only, not persisted)<br/>• ⚠️ if a `people` slot resolves to **multiple ids** → keep name, set `ambiguous_id`, defer to ruler/faction context (**do not guess**)<br/>• ▸ `dedup_key` for same-name disambiguation is **deferred** — `ambiguous_id` carries the load until colour inputs are calibrated<br/>• **NO MATCH** → skeleton-cluster (mask names+digits) → CONFIRM queue → human approves → append row to `tblPatterns` (learned, never re-asked)<br/>▸ Side-effect: ruler events (登庸 ruler / 滅止) update FactionState → `tblFactions`<br/>▸ **Recon side-output:** the CONFIRM queue _is_ the taxonomy-discovery loop — every new approved pattern is a new Taxonomy row (Stateful? curated by hand). ▸ **Phase 2:** the stateful side-effect gate is the prime reusable asset |
| **5** _[KEEP]_      | **Output & Commit**                                                | append → `tblEvents` (schema v4)<br/>columns: `date` · `turn_period` · `ruler` · `action_type` · `subject` · `object` · `issuer` · `ambiguous_id` · `location` · `target_faction` · `office` · `value` · `success` · `confidence` · `raw_text`<br/>⚠️ `success` boolean at **column M**<br/>unresolved lines → `tblPending` for batch review<br/>▸ **Commit order (per image, last step):** write `tblEvents` → advance `meta.last_screenshot` → **move image to `processed/`**. Crash before the move = inbox retains image, next run reprocesses (Stage 2 absorbs duplication). **Never move before commit.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |

### Stage Reuse Map (Phase 1 → Phase 2)

- **[KEEP]** Stage 0 (vocab + FactionState), Stage 3 (clean/correct), Stage 4 (grammar + **stateful gate**), Stage 5 (commit discipline) — carry over unchanged.
- **[KEEP+]** Stage 1 ROI-crop/OCR + monotonicity — kept, and the date watermark is _strengthened_ by video's independent monotonic wall-clock.
- **[REPLACE]** Stage 0.5 (folder ingest) → **frame-reduction**; Stage 2 (difflib content-dedup) → **log-tracker** (temporal/positional). These two are the only net-new Phase-2 upstream stages.

### Reconnaissance Capture Obligations

Phase 1 must accumulate, as it runs, the evidence that fills the Exit Artifact:

- **Taxonomy** — largely a projection of `tblPatterns` (template lives there already); Phase 1 _adds_ the hand-curated **Stateful?** flag per pattern. Drive coverage by deliberately seeking captures of _every_ event type, **weighted toward rare stateful events** (滅止, ruler-succession) that a convenience-sampled pile under-represents.
- **ROI variance** — Stage 1 logs each detected ROI box + OCR confidence per screenshot; mine these to classify each ROI STATIC / SHIFTING / VOLATILE.
- **Layout states** — quarantine reasons + OCR-failure clusters surface UI configurations that occlude/relocate ROIs; record each with a cheap detection signal.

### Feedback Loops

- **Stage 4 confirm** ──► `tblPatterns` _(grammar grows)_ ──► **Taxonomy table** _(recon)_
- **Stage 4 ruler events** ──► `tblFactions` _(rulers change)_

### Ingest & Ordering Notes

- Filename stem `DECK-yyyymmdd-hhmmss` is **capture wall-clock**, not in-game date. Stem order = _assumed_ turn order; in-game `date_box` (Stage 1) is the independent witness. Disagreement (a date _decrease_) flags out-of-order capture or a double-shot — quarantine, don't proceed.
- Multiple captures per turn is expected ⇒ in-game date check is **non-decreasing**; Stage 2 expects high overlap and may legitimately emit **zero** new lines.
- `meta.last_screenshot` holds the **last committed stem** (e.g. `DECK-20260627-171212`); empty/sentinel for a fresh DB. Role: cross-run high-water mark + resume cursor.
- Three sinks, distinct meanings: **`processed/`** = committed OK · **`quarantine/`** = bad _image_ (name/OCR/order) · **`tblPending`** = unresolved _lines_ within a good image.

### Data-Driven Constraints (derived from loaded dict)

| Vocab  | Count | Length range | Notes                                                                                                                                     |
| ------ | ----- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| people | 1001  | 2–4          | names **not unique**: 韓忠×2, 張承×2, 張南×2, 馬忠×2, 李豐×3 → resolve via `id`; defer with `ambiguous_id`. 獻帝 (id 1001) is issuer-only |
| places | 218   | 1–3          | many single-char 據點 (薊·吳·鄴·郯·魯·宋·陳·燕·代·黃…) raise OCR/fuzzy risk                                                               |

### Schema Notes

- **schema_version: 4** — people +1 (獻帝, id 1001, issuer-only); `tblEvents` gained `issuer` (after `object`) and `office` (after `target_faction`); `success` boolean now at column **M**; new `tblColorBands` sheet (HSV calibration **TODO**); `meta_kv` gained `pattern_count`.
- `meta_kv` exposes derived counts: `people_count`, `places_count`, `faction_count`, `pattern_count`, plus documented buckets `people_len_buckets=2-4`, `places_len_buckets=1-3`.
- `meta.last_screenshot` is now a **filename stem** (`DECK-…`), repurposed from the old `0000` sequence placeholder — value change only, **no schema bump** (ingestion is runtime config, not vocabulary).
- Place slots in `capture` / `march` / `besiege` / `explore` patterns use `.{1,3}?` to match the real 1–3 char place range.
- No `aliases` sheet — surface variants (e.g. 港口 suffixes) are normalised in Stage 3 code.
- `dedup_key` intentionally **not** in schema yet — blocked on `tblColorBands` calibration; `ambiguous_id` is the interim mechanism.
- ▸ **Phase-2 carry-overs (recorded now, not yet implemented):** `tblEvents` will gain `source_kind` (screenshot/video); video events carry a monotonic `video_ts` alongside in-game `date`; `tblPending` gains a `pending_kind` discriminator (`unresolved_line` / `deferred_stateful`). **No Phase-1 schema bump** — listed so they aren't relitigated.

---

# Phase-1 Exit Artifact (Handoff to Phase 2)

Phase 1 is **formally complete** when the three maps below are populated and their coverage
rules met. Status legend: ✅ confirmed (≥1 clean capture analysed) · ⚠️ partial (seen but
under-sampled/ambiguous) · ❌ missing (no capture yet). Values below are the **current
in-progress seed** — update as captures accrue.

## A. Event Taxonomy

The matching dictionary for Phase 2's log-tracker + gate. Template lives in `tblPatterns`;
**Stateful?** is the curated addition. ⚠️ Stateful-ness can be **conditional on slot
resolution** — see `appoint`.

| action_type            | Trigger Template (from tblPatterns)                     | Captured slots                               | Stateful?                                                          | Status |
| ---------------------- | ------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------ | ------ |
| appoint (登庸)         | `{issuer} が {subject} を登庸 …`                        | issuer(people), subject(people), office(raw) | **Y — only when subject is/becomes a ruler**; ordinary recruit = N | ✅     |
| 滅止 (faction destroy) | `{target_faction} 滅亡 …`                               | target_faction                               | **Y**                                                              | ✅     |
| capture (城/據點攻略)  | `{subject} … {location} 攻略 (所屬於 {target_faction})` | subject, location, target_faction            | **Y _(verify — territory change)_**                                | ⚠️     |
| march (進軍)           | `{subject} … {location} へ進軍`                         | subject, location                            | N _(verify)_                                                       | ⚠️     |
| besiege (包圍)         | `{subject} … {location} 包圍`                           | subject, location                            | N                                                                  | ⚠️     |
| explore (探索)         | `{subject} … 探索 …`                                    | subject, location                            | N                                                                  | ⚠️     |
| succession (当主交代)  | `{target_faction} 当主 → {subject}`                     | target_faction, subject                      | **Y**                                                              | ⚠️     |
| (further types)        | — discovered via Stage 4 CONFIRM                        | —                                            | TBD                                                                | ❌     |

**Verify before handoff:** `capture` and `succession` likely mutate FactionState
(territory / ruler) and would join {appoint-ruler, 滅止} in the gated set — confirm by
observation, don't assume. The `appoint` conditional-stateful case is a **direct input to
Phase 2's gate design**: the gate must key on _resolved slots_, not action_type alone.

**Coverage rule:** a row for every emittable type; every Stateful? flag observation-confirmed;
all _(verify)_ items resolved.

## B. ROI Variance Map

Phase 2 inherits these regions, so the asset is the **stability class**, not the rectangle.
A box assumed STATIC that actually SHIFTS will silently false-trigger Phase-2 hash-diff.

| ROI           | Nominal location | Content                  | Variance behaviour                                                                      | Stability class       | Occluded by        | Status          |
| ------------- | ---------------- | ------------------------ | --------------------------------------------------------------------------------------- | --------------------- | ------------------ | --------------- |
| date_box      | top bar, left    | in-game date             | **VERIFY** width-drift as string lengthens (era/2- vs 3-digit)                          | ⚠️ SHIFTING (assumed) | full-screen modals | ✅ loc / ⚠️ var |
| ruler_box     | top bar          | active faction/ruler     | content changes per turn; position likely fixed                                         | STATIC (verify)       | full-screen modals | ⚠️              |
| event_log_box | lower region     | scrolling multi-line log | **CRITICAL — verify resize when side-panel/modal opens; fixed vs. variable line count** | ⚠️ SHIFTING (assumed) | modals, menus      | ✅ loc / ❌ var |

**Must resolve before handoff:** (1) `date_box` width-drift bounds (capture min- and
max-length date strings); (2) `event_log_box` resize behaviour; (3) fixed vs. variable log
line-count (decides whether the tracker reads a known N-row grid or detects rows dynamically).

**Coverage rule:** every ROI given an evidence-based class; the three questions above answered.

## C. Layout-State Enumeration

Tells Phase-2 frame-reduction when **not** to trust an ROI. Without it, occluded regions get
OCR'd → phantom events.

| Layout state                    | Cheap detection signal | ROI validity                           | Status |
| ------------------------------- | ---------------------- | -------------------------------------- | ------ |
| main_view                       | no overlay             | all valid                              | ✅     |
| event_modal (major-event popup) | centre dialog present  | date/ruler valid; **log_box occluded** | ⚠️     |
| menu_open (command/strategy)    | side/full panel        | log_box **resized or hidden**          | ❌     |
| map_zoom / sub-view             | map fills frame        | top bar may persist; log hidden        | ❌     |
| loading / transition            | (signal TBD)           | **all invalid — skip**                 | ❌     |
| dialog_text / paused            | story-text overlay     | most occluded                          | ❌     |

**Coverage rule:** every state listed with a detection signal + ROI-validity row; all states
that occlude/relocate `event_log_box` or `date_box` identified. `loading/transition` and
animation states bridge to the temporal axis — record their _signature_ so Phase 2 can detect
them; do **not** attempt to time them here (out of scope, §Phase Context).

## D. Sign-Off Criteria

Phase 1 is complete when **A + B + C** coverage rules are met and the Phase-Context
out-of-scope statement is carried into Phase-2 planning as _required recon_, not assumed-done.
Confirmed-reusable into Phase 2 unchanged: **Stage 0, 3, 4 (stateful gate), 5, and the Stage 1
date watermark.** Only frame-reduction and the log-tracker are net-new.
