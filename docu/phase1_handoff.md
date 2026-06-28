_Thinking..._

> I need to create a formal phase-1 exit checklist as a handoff document for phase 2, structured around three key deliverables: a taxonomy table mapping event types to templates and stateful properties, an ROI variance map, and a layout-state enumeration. I'll organize this as a clean technical document with tables since that's the appropriate format for a structured handoff artifact.
>
> Now I'm building out the full framework with concrete sections: the event taxonomy (capturing event types like ruler appointment and faction destruction with their templates, stateful flags, and ROI sources), the ROI variance map (showing where each ROI appears, how it behaves under different conditions, and when it gets occluded), the layout-state enumeration (defining which ROIs are valid or relocated in each UI state), and explicit coverage exit criteria that are checkable against actual captures rather than just pipeline execution. I'm also marking the temporal axis as explicitly out-of-scope to establish clear boundaries for phase 1.

# Phase 1 Exit Artifact — Reconnaissance Handoff to Phase 2

**Purpose.** This document is the formal boundary between phase 1 (screenshot-based study) and phase 2 (live/recorded video ingest). Phase 1 is **complete when this artifact is fully populated and its coverage criteria are met** — _not_ when the extraction pipeline runs cleanly. The deliverable is knowledge about the problem space, captured in three maps below, plus an explicit statement of what phase 1 structurally could not learn.

Each table carries a **Status** column so "done" is checkable against coverage rather than against a passing run. Status values: ✅ confirmed (≥1 clean capture analyzed), ⚠️ partial (seen but under-sampled or ambiguous), ❌ missing (no capture yet).

---

## A. Event Taxonomy Table

The single most valuable handoff. In phase 2 this becomes the **matching dictionary** the log tracker uses to (a) recognize a line as a known event type and (b) decide whether its ordering matters. The **Stateful?** column is load-bearing: it determines whether an out-of-order observation triggers the FactionState side-effect gate (deferred to `tblPending`) or flows through append-only.

Columns:

- **Event Type** — canonical internal name.
- **Trigger Template** — the OCR'd log-line pattern; literal text with `{placeholders}` for variable fields (faction, person, city, value).
- **Captured Fields** — structured data the line yields.
- **Stateful?** — does it mutate FactionState/`tblFactions`? (`Y` = order-sensitive, gated; `N` = append-only, order-independent.)
- **Source ROI** — which region the line is read from (almost always `event_log_box`, but note exceptions).
- **Status**

| Event Type              | Trigger Template                     | Captured Fields     | Stateful?              | Source ROI    | Status |
| ----------------------- | ------------------------------------ | ------------------- | ---------------------- | ------------- | ------ |
| ruler_appoint (登庸)    | `{person} が {faction} に登庸された` | person, faction     | **Y**                  | event_log_box | ✅     |
| faction_destroy (滅止)  | `{faction} が滅亡した`               | faction             | **Y**                  | event_log_box | ✅     |
| succession              | `{faction} の当主が {person} に交代` | faction, person_new | **Y**                  | event_log_box | ⚠️     |
| city_capture            | `{faction} が {city} を攻略`         | faction, city       | **Y** _(verify)_       | event_log_box | ⚠️     |
| alliance_form           | `{factionA} と {factionB} が同盟`    | factionA, factionB  | **Y** _(verify)_       | event_log_box | ❌     |
| battle_result           | `{city} の戦い: {winner} 勝利`       | city, winner        | N                      | event_log_box | ⚠️     |
| birth / death (natural) | `{person} が死去`                    | person              | N _(verify vs. ruler)_ | event_log_box | ❌     |
| construction / dev      | `{city} で {facility} 完成`          | city, facility      | N                      | event_log_box | ❌     |
| diplomacy_misc          | (various)                            | —                   | N                      | event_log_box | ❌     |

**Note rows above are a seed, not the final set.** Phase 1 is not closed until every event type the game can emit has a row, and every row's **Stateful?** value is _confirmed by observation_ (not guessed). Two specific verification tasks flagged with _(verify)_:

- **city_capture / alliance** — these _may_ mutate faction state (territory, relations) in ways later turns consume. If so they join 登庸/滅止 in the gated set, which materially expands the side-effect logic. Resolve before handoff.
- **death events** — a natural death of a _ruler_ is implicitly stateful (forces succession); a death of a non-ruler is not. Confirm whether the game emits these as one template or two.

**Coverage rule for Section A:** ≥1 clean capture of _every_ event type, with **priority weighting toward rare stateful events** (succession, destroy) since those are the ones phase 2's gate exists to protect and the ones a convenience-sampled screenshot pile will under-represent.

---

## B. ROI Variance Map

Phase 2 inherits these regions directly, so the asset is not the nominal rectangle — it's the **stability characterization**: does the box move, resize, or get occluded, and under what conditions? A box assumed static that actually shifts will silently corrupt phase 2's hash-diff frame-reduction.

Columns:

- **ROI** — region name.
- **Nominal Location** — described relative to frame (e.g., "top-left, ~5% margin"), _not_ absolute pixels, since resolution varies.
- **Content Type** — what it holds / how it's parsed.
- **Variance Behavior** — observed movement/resize/reflow under different states.
- **Stability Class** — `STATIC` (safe to hash-diff directly), `SHIFTING` (anchor-relative re-detect each frame), `VOLATILE` (must re-locate before every read).
- **Occluded By** — which layout states (Section C) hide or invalidate it.
- **Status**

| ROI            | Nominal Location       | Content Type                 | Variance Behavior                                                                             | Stability Class       | Occluded By        | Status               |
| -------------- | ---------------------- | ---------------------------- | --------------------------------------------------------------------------------------------- | --------------------- | ------------------ | -------------------- |
| date_box       | top bar, left          | in-game date string          | Does it shift right as the string lengthens (era change, 2- vs 3-digit year)? **MUST VERIFY** | ⚠️ SHIFTING (assumed) | full-screen modals | ✅ loc / ⚠️ variance |
| ruler_box      | top bar, right of date | active faction/ruler context | Changes content on turn pass; position likely fixed                                           | STATIC (verify)       | full-screen modals | ⚠️                   |
| event_log_box  | lower region           | scrolling multi-line log     | Does it resize when a side panel opens? Fixed line count or variable? **CRITICAL**            | ⚠️ SHIFTING (assumed) | modals, menus      | ✅ loc / ❌ variance |
| turn_indicator | (TBD)                  | whose turn / phase           | unknown                                                                                       | ❌                    | unknown            | ❌                   |

**Three variance questions that must be answered before handoff** (each is a phase-2 frame-reduction landmine if left open):

1. **date_box width drift** — if the box's bounding region moves when the date string grows, phase 2's per-ROI hash will false-trigger on layout, not content. Capture min-length and max-length date strings to bound the region.
2. **event_log_box resize** — confirm whether the log region is fixed or reflows when other UI opens. The whole "is this ROI valid right now?" gate depends on it.
3. **Fixed vs. variable line count** in the log — determines whether the tracker reads a known N-row grid or must detect row boundaries dynamically.

**Coverage rule for Section B:** every ROI classified `STATIC`/`SHIFTING`/`VOLATILE` _from evidence_, with the date-width and log-resize questions explicitly resolved.

---

## C. Layout-State Enumeration

The set of distinct UI configurations and, for each, which ROIs are **valid / invalid / relocated**. Phase 2's frame-reduction stage needs this to know when _not_ to trust an ROI (e.g., "log region is garbage while this modal is up"). Without it, phase 2 will OCR occluded regions and emit phantom events.

Columns:

- **Layout State** — the UI configuration.
- **How Detected** — the cheap visual signal that identifies this state (for phase 2's per-frame classification).
- **ROI Validity** — which Section-B regions are readable / blocked / moved in this state.
- **Status**

| Layout State                                 | How Detected              | ROI Validity                           | Status |
| -------------------------------------------- | ------------------------- | -------------------------------------- | ------ |
| main_view (default)                          | no overlay present        | all ROIs valid                         | ✅     |
| event_modal (popup announcing a major event) | center dialog box present | date/ruler valid; **log_box occluded** | ⚠️     |
| menu_open (command/strategy menu)            | side or full menu panel   | log_box may be **resized or hidden**   | ❌     |
| map_zoom / sub-view                          | map fills frame           | top bar may persist; log likely hidden | ❌     |
| loading / transition                         | (TBD signal)              | **all ROIs invalid** — skip frame      | ❌     |
| paused / dialog_text                         | story/event text overlay  | most ROIs occluded                     | ❌     |

**Handoff note:** the `loading/transition` and animation states are the bridge to the temporal axis below — phase 1 can confirm they _exist_ and roughly what they look like, but cannot characterize their _duration or dynamics_. Record their visual signature so phase 2 knows what to detect; do not attempt to time them.

**Coverage rule for Section C:** every layout state the game can enter is listed, with a detection signal and an ROI-validity row. The critical entries are any state that **occludes or relocates `event_log_box` or `date_box`**, since those directly gate event extraction.

---

## D. Explicit Out-of-Scope — The Temporal Axis (phase-1 blind spot, by construction)

This section exists so phase 2 does **not** inherit a false sense of coverage. Phase 1 de-risks the content/spatial axis toward ~100% and the **temporal axis toward ~0%.** The following are _known unknowns_ that require a dedicated phase-2 recon pass on a few captured video clips, and must not be assumed answered by phase 1:

- **Animation/settle timing** — how long fade-ins/slide-ins take before a line is cleanly rendered (drives "settle-then-read").
- **Scroll dynamics** — how new events enter, auto-scroll behavior, and the frame-to-frame appearance of _manual scrollback_ (the temporal-dup ≠ content-dup problem).
- **Line persistence & date-advance rate in real time** — sets the phase-2 sampling frequency.
- **Live-vs-recorded scope decision** — whether phase 2 has lookahead (recorded) or only a trailing window (live). This shapes the tracker's robustness and is a phase-2 opening question, not a phase-1 output.

---

## E. Handoff Sign-Off Criteria

Phase 1 is formally complete when:

- **A.** Taxonomy table has a row for every emittable event type; every **Stateful?** flag is observation-confirmed; all _(verify)_ items resolved.
- **B.** Every ROI has an evidence-based stability class; date-width drift and log-box resize questions answered.
- **C.** Every layout state enumerated with a detection signal and ROI-validity row; all log/date-occluding states identified.
- **D.** This out-of-scope section is acknowledged and carried into phase 2 planning as required recon, not assumed-done.

Two downstream-schema carry-overs already settled in prior design, recorded here so they aren't relitigated: events will carry `source_kind` (screenshot/video) and video events a monotonic `video_ts`; `tblPending` carries a `pending_kind` discriminator (`unresolved_line` / `deferred_stateful`). The **stateful side-effect gate and date watermark are confirmed reusable** into phase 2 unchanged — only the upstream frame-reduction and log-tracker stages are net-new.

---

Want me to turn Section A into a strict machine-readable schema (e.g., a YAML/JSON event-definition file with `template`, `fields`, `stateful`, `roi`) so it can be loaded directly as phase 2's matching dictionary rather than re-transcribed from this table? That would make the most valuable artifact executable instead of just documentary.
