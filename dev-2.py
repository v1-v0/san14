"""
Parse a 三國志14 (Sangokushi 14) action log and produce two shortlists:

  Shortlist 1 — Contested recruitment targets (中止登庸), counted by target.
  Shortlist 2 — Full acquisition outcome per target (field + prisoner combined).
"""
import os
import re
from collections import defaultdict, Counter


# ---------------------------------------------------------------------------
# 1. Load the "Actions" column
# ---------------------------------------------------------------------------
def load_actions(path: str) -> list[str]:
    """Read the 'Actions' column from an .xlsx (preferred) or .csv file."""
    if path.lower().endswith(".xlsx"):
        import openpyxl  # pip install openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            raise ValueError("No active worksheet found in the workbook.")

        rows_iter = ws.iter_rows(values_only=True)
        header_row = next(rows_iter, None)
        if header_row is None:
            return []

        header = [str(c).strip() if c is not None else "" for c in header_row]
        try:
            col = header.index("Actions")
        except ValueError:
            col = len(header) - 1  # fall back to last column

        rows = []
        for r in rows_iter:
            if r and col < len(r) and r[col]:
                rows.append(str(r[col]).strip())
        return rows
    else:  # CSV fallback
        import csv
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [row["Actions"].strip() for row in reader if row.get("Actions")]


# ---------------------------------------------------------------------------
# 2. Cleaning helpers (handle OCR typos + merged lines)
# ---------------------------------------------------------------------------
ABORT_VARIANTS = ["中北登庸", "中止登廉", "中止登康"]

def normalize(text: str) -> str:
    for v in ABORT_VARIANTS:
        text = text.replace(v, "中止登庸")
    return text

def split_merged(line: str) -> list[str]:
    """
    Split rows that glue two events together, e.g.
      '關純中止登庸王淩田豫中止登庸王淩' -> two separate abort events.
    """
    line = normalize(line)
    parts = re.split(r'(?<=.)(?=[^\s，。]+?中止登庸)', line)
    return [p for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# 3. Regex patterns for each mechanic
# ---------------------------------------------------------------------------
RE_ABORT   = re.compile(r'^(?P<recruiter>.+?)中止登庸(?P<target>.+?)$')
RE_FIELD   = re.compile(r'^(?P<recruiter>.+?)登庸(?P<target>.+?)(?P<result>成功|失敗)$')
RE_CAPTURE = re.compile(r'^成功登庸了俘虜(?P<target>.+?)$')


def analyze(actions: list[str]):
    contested = Counter()                       # target -> # of 中止登庸 events
    contested_who = defaultdict(set)            # target -> set of recruiters
    outcomes = defaultdict(lambda: {"field_success": Counter(),
                                    "field_fail": Counter(),
                                    "captured_by_us": 0})

    for raw in actions:
        for line in split_merged(raw):
            line = line.strip()

            # (B) Prisoner recruitment -- no named recruiter, always success
            m = RE_CAPTURE.match(line)
            if m:
                outcomes[m["target"]]["captured_by_us"] += 1
                continue

            # (1) Aborted recruitment
            m = RE_ABORT.match(line)
            if m:
                tgt = m["target"].strip()
                contested[tgt] += 1
                contested_who[tgt].add(m["recruiter"].strip())
                continue

            # (A) Field / diplomatic recruitment
            m = RE_FIELD.match(line)
            if m and "俘虜" not in line:
                tgt, rec = m["target"].strip(), m["recruiter"].strip()
                if m["result"] == "成功":
                    outcomes[tgt]["field_success"][rec] += 1
                else:
                    outcomes[tgt]["field_fail"][rec] += 1

    return contested, contested_who, outcomes


# ---------------------------------------------------------------------------
# 4. Reporting
# ---------------------------------------------------------------------------
def report(contested, contested_who, outcomes, min_contested=2):
    print("=" * 60)
    print("SHORTLIST 1 - Contested recruitment targets (中止登庸)")
    print(f"(targets aborted by >= {min_contested} recruiters)")
    print("=" * 60)
    for tgt, cnt in contested.most_common():
        if cnt < min_contested:
            continue
        secured = bool(outcomes[tgt]["field_success"] or outcomes[tgt]["captured_by_us"])
        landed = "later secured" if secured else "never secured"
        recruiters = "、".join(sorted(contested_who[tgt]))
        print(f"  {tgt:<6} x{cnt:<2}  [{landed}]  by: {recruiters}")

    print()
    print("=" * 60)
    print("SHORTLIST 2 - Full acquisition outcome per target")
    print("(field recruitment + prisoner recruitment combined)")
    print("=" * 60)
    for tgt in sorted(outcomes):
        o = outcomes[tgt]
        succ = sum(o["field_success"].values())
        fail = sum(o["field_fail"].values())
        cap  = o["captured_by_us"]
        if succ == 0 and fail == 0 and cap == 0:
            continue
        bits = []
        if succ:
            bits.append(f"field_OK x{succ} ({'、'.join(o['field_success'])})")
        if fail:
            bits.append(f"field_FAIL x{fail} ({'、'.join(o['field_fail'])})")
        if cap:
            bits.append(f"captured x{cap}")
        status = "JOINED" if (succ or cap) else "FAILED-ONLY"
        print(f"  {tgt:<6} [{status:<11}]  " + "  |  ".join(bits))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    PATH = os.path.join(os.path.dirname(__file__), "san14_recruitment.xlsx")
    #PATH = os.path.expanduser("~/Downloads/san14_recruitment.xlsx")   # or a .csv with an 'Actions' column
    actions = load_actions(PATH)
    contested, contested_who, outcomes = analyze(actions)
    report(contested, contested_who, outcomes, min_contested=2)