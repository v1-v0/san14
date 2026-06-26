# 三國志14登庸

# 三國志14 Recruitment Log Analyzer

A small Python tool that reads a _Sangokushi 14_ (三國志14) action log, cleans up OCR noise and merged lines, and produces two recruitment shortlists in a tidy multi-sheet Excel workbook. It's built to answer two practical questions about an in-progress campaign:

- **Who is everyone fighting over?** — which officers are being actively contested (中止登庸, "recruitment aborted"), and by how many of your recruiters.
- **How did our recruitment efforts actually go?** — per-target field recruitment success and failure, with the names of the recruiters involved.

The game is KOEI TECMO's _Romance of the Three Kingdoms XIV_ — Traditional Chinese product page: https://www.gamecity.com.tw/sangokushi14/index.html

---

## What's in the box

| File                        | Role                                                                                   |
| --------------------------- | -------------------------------------------------------------------------------------- |
| `dev-3.py`                  | The analyzer script.                                                                   |
| `sangokushi14_officers.csv` | Officer dictionary — the full 1000-name roster used to split merged lines correctly.   |
| `san14_recruitment.xlsx`    | **Your input.** A spreadsheet with an `Actions` column holding the raw game-log lines. |
| `san14_report.xlsx`         | **The output.** A four-sheet workbook the script generates.                            |

The officer dictionary mirrors the in-game 武將一覧 (officer list): https://www.gamecity.com.tw/sangokushi14/officers-list.html — all 1000 playable characters, the largest roster in the series.

---

## Why the officer dictionary matters

Game logs are often captured by OCR, and long sessions produce two recurring problems: individual lines get visually glued together, and characters get misread. The dictionary is what lets the tool recover cleanly from the first problem.

When two complete abort events end up on one line — for example `關純中止登庸王淩田豫中止登庸王淩` — the script can't just split on the 中止登庸 marker, because it wouldn't know where one officer's name ends and the next begins. Instead it walks the line greedily, matching the **longest known name** from the dictionary at each step. Because 王淩, 田豫, 關純 and the rest are all in the roster, the line splits into two correct events without ever cutting a name in half.

The dictionary is combined with names the script auto-harvests from your own unambiguous log lines, so even officers who only appear in clean single-event rows are recognized. Together they drive the greedy splitter.

---

## Input format

`san14_recruitment.xlsx` should have a header row containing a column named `Actions`. Each subsequent row is one raw log line, exactly as captured. (If no `Actions` column is found, the script falls back to the last column.) A `.csv` file with the same `Actions` column also works.

The tool understands three log mechanics:

- **Contested recruitment** — lines of the form `〈recruiter〉中止登庸〈target〉`, meaning a recruiter's attempt on that target was aborted (usually because someone else got there first).
- **Field recruitment** — lines of the form `〈recruiter〉登庸〈target〉成功/失敗`, a direct success or failure.
- **Prisoner recruitment** — lines beginning `成功登庸了俘虜…`. These carry **no recruiter name**, so by design they are recognized and skipped rather than shortlisted.

---

## OCR cleanup

Before analysis, the script normalizes three known OCR misreadings of the abort marker 中止登庸 back to the correct form:

| Misread  | Corrected |
| -------- | --------- |
| 中北登庸 | 中止登庸  |
| 中止登廉 | 中止登庸  |
| 中止登康 | 中止登庸  |

Every row that needed correcting is logged on the **Issues** sheet so you can audit exactly what was changed.

---

## The output report

`san14_report.xlsx` contains four sheets.

**1. Original** — the raw `Actions` column exactly as ingested, with row numbers, so the report is self-contained and traceable back to your source.

**2. Issues** — every row that needed OCR normalization or that was split out of a merged line. Each entry shows the row number, the kind of issue, the specific OCR variants found, the original text, and what it was split into. If a merged line contains a name absent from both the dictionary and the harvested set, it's flagged as `UNPARSED merge - unknown name?` so you know which name to add.

**3. Approaching** — _Shortlist 1, contested targets._ For each officer aborted by at least two recruiters: the abort count, whether they were ever **Secured** by field recruitment (`later` / `never`), the **Secured by** column naming the successful recruiter(s), and the **Aborted by** column listing everyone whose attempt was aborted. This is your "hot prospects" view — who's in demand and whether you ultimately landed them.

**4. Efforts** — _Shortlist 2, recruitment outcomes._ For each target touched by field recruitment: the overall status (`JOINED` / `FAILED-ONLY`), field success and failure counts, and the names of the **successful** and **failed** recruiters. Where a recruiter tried more than once, the count is shown inline (e.g. `荀諶 x2`).

The console prints a condensed version of both shortlists when you run the script.

---

## Requirements

- Python 3.10 or newer (the code uses `str | None` type hints).
- `openpyxl` for reading and writing `.xlsx` files:

```
pip install openpyxl
```

---

## Usage

Place `dev-3.py`, `sangokushi14_officers.csv`, and your `san14_recruitment.xlsx` in the same folder, then run:

```
python dev-3.py
```

The script reads the log, merges the officer dictionary with names harvested from your data, analyzes everything, prints the shortlists to the console, and writes `san14_report.xlsx` alongside the inputs. On finishing it reports how many rows were processed and how many issues were logged.

All paths are resolved relative to the script's own location, so it can be run from any working directory.

---

## Customization

A few things you may want to adjust:

The **minimum contest threshold** controls who appears on the _Approaching_ sheet. It defaults to 2 (a target must be aborted by at least two recruiters). Change the `min_contested=2` arguments in the `__main__` block to widen or narrow the shortlist.

The **OCR variant list** (`ABORT_VARIANTS` near the top of the script) is where you add any new misreadings of 中止登庸 that show up in future captures.

If your logs mix simplified and traditional forms of a name — for instance 牵招 alongside the roster's 牽招 — extend the `normalize()` function with a character fold such as `text = text.replace("牵", "牽")` so both forms match the dictionary and don't get flagged as unparsed merges.

---

## Notes and limitations

Prisoner-recruitment lines (`成功登庸了俘虜…`) are intentionally excluded from both shortlists because the log records no recruiter for them; they're still recognized so they're never miscounted as something else. A target who was _only_ ever captured — never contested, never field-recruited — will therefore not appear in either shortlist. And the greedy splitter is only as complete as its name set: if a genuinely merged line contains an officer missing from both the dictionary and your data, that line is left intact and flagged on the Issues sheet for manual review.
