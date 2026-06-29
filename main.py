"""CLI entrypoint.

Commands:
  run                 process the inbox (Stage 0->5)
  export-taxonomy     dump §A taxonomy (tblPatterns projection) as JSON
  approve <pat.json>  append a human-approved pattern row to tblPatterns
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from . import config
from .pipeline import run
from .recon import export_taxonomy
from .workbook import Workbook


def _approve(pattern_json: str) -> None:
    """Append a CONFIRM-approved pattern; learned, never re-asked."""
    with open(pattern_json, encoding="utf-8") as f:
        rec = json.load(f)
    wb = Workbook(config.DICT_XLSX)
    hdr = wb.headers("tblPatterns")
    wb.append_rows("tblPatterns", [[rec.get(h) for h in hdr]])
    wb.set_meta("pattern_count", len(wb.rows("tblPatterns")))
    wb.save()
    print(f"appended pattern {rec.get('pattern_id')}")


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(prog="san14")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--stub", action="store_true",
                       help="use StubOCREngine (no PaddleOCR)")
    p_run.add_argument("--halt-on-quarantine", action="store_true")

    sub.add_parser("export-taxonomy")

    p_ap = sub.add_parser("approve")
    p_ap.add_argument("pattern_json")

    args = ap.parse_args(argv)

    if args.cmd == "run":
        engine = None
        if args.stub:
            from .ocr import make_engine
            engine = make_engine(stub=True, script={})
        stats = run(engine=engine, halt_on_quarantine=args.halt_on_quarantine)
        print(json.dumps(stats, ensure_ascii=False))
    elif args.cmd == "export-taxonomy":
        print(json.dumps(export_taxonomy(), ensure_ascii=False, indent=2))
    elif args.cmd == "approve":
        _approve(args.pattern_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

