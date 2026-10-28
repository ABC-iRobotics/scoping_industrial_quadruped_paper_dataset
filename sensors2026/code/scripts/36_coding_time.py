"""Human coding time per validation study, from ActivityWatch.

P.Z. coded the blind validation subsample by reading each PDF and filling the
coding workbook. ActivityWatch (local server, host DESKTOP-G4O63EI) logs the
focused window and whether the user is active. This script asks it for window
events intersected with not-AFK time and attributes them to studies:

- time on a window whose title names a study (`paper042.pdf`, `r2-0704`, ...)
  goes to that study;
- time on the coding workbook (`validation_coding...`) goes to the study whose
  PDF was focused most recently before it, because the sheet is filled while
  reading that paper;
- time spent on the rules or before any study was opened is reported
  separately as setup, not spread over studies.

The figures are active-window time, so reading a printout or thinking away from
the keyboard is not counted; they are a lower bound on effort, and are reported
as such.

Usage:
    python scripts/36_coding_time.py --start 2026-09-26 --end 2026-10-15
writes work/validation/coding_time.csv and prints a summary.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

AW = "http://localhost:5600/api/0/query/"
HOST = "DESKTOP-G4O63EI"
OUT = Path(__file__).resolve().parent.parent / "work" / "validation" / "coding_time.csv"
STUDY = re.compile(r"\b(paper\d{3}|r2-\d{4})\b", re.I)
SHEET = re.compile(r"validation_coding", re.I)
ROOT = Path(__file__).resolve().parent.parent

# Acrobat sometimes shows a PDF's embedded document title instead of its file
# name (paper045 and paper057 appear only as their article titles). Match those
# windows by the first words of the study's title as well.
_ALIASES: dict[str, str] = {}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load_aliases() -> None:
    import pandas as pd
    base = pd.read_excel(ROOT.parent / "data" / "full_text_screening_results.xlsx",
                         usecols=["Pdf name", "Title"])
    pairs = list(zip(base["Pdf name"], base["Title"]))
    r2 = ROOT / "work" / "r2_06_fulltext_needed.xlsx"
    if r2.exists():
        x = pd.read_excel(r2, usecols=["record_id", "Title"])
        pairs += list(zip(x["record_id"], x["Title"]))
    for sid, title in pairs:
        key = _norm(str(title))[:40]
        if len(key) >= 25:
            _ALIASES[key] = str(sid).lower()


def match_study(title: str) -> str | None:
    m = STUDY.search(title)
    if m:
        return m.group(1).lower()
    nt = _norm(title)
    for key, sid in _ALIASES.items():
        if nt.startswith(key):
            return sid
    return None


def relevant(title: str) -> bool:
    return bool(SHEET.search(title)) or match_study(title) is not None


def query(start: str, end: str) -> list[dict]:
    q = (f"w = query_bucket('aw-watcher-window_{HOST}');"
         f"a = query_bucket('aw-watcher-afk_{HOST}');"
         "a = filter_keyvals(a, 'status', ['not-afk']);"
         "w = filter_period_intersect(w, a);"
         "RETURN = sort_by_timestamp(w);")
    body = json.dumps({"timeperiods": [f"{start}/{end}"], "query": [q]}).encode()
    req = urllib.request.Request(AW, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return [e for e in json.load(r)[0] if relevant(e["data"].get("title", ""))]


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def from_export(path: str, start: str, end: str) -> list[dict]:
    """Same filtering as query(), done locally on an ActivityWatch bucket export.

    P.Z. coded most studies on a second machine (DESKTOP-00I2HT7) whose
    ActivityWatch server is not reachable from here; its buckets were exported
    from the web UI and uploaded. Window events are clipped to not-AFK periods,
    exactly what filter_period_intersect does on the server.
    """
    data = json.load(open(path, encoding="utf-8"))
    buckets = data.get("buckets", data)
    win = next(v for k, v in buckets.items() if k.startswith("aw-watcher-window_"))
    afk = next(v for k, v in buckets.items() if k.startswith("aw-watcher-afk_"))
    lo, hi = _ts(start + "T00:00:00+00:00"), _ts(end + "T00:00:00+00:00")
    active = sorted(
        (_ts(e["timestamp"]), _ts(e["timestamp"]) + timedelta(seconds=e["duration"]))
        for e in afk["events"] if e["data"].get("status") == "not-afk"
    )
    out = []
    for e in win["events"]:
        title = e["data"].get("title", "")
        if not relevant(title):
            continue
        s = _ts(e["timestamp"])
        f = s + timedelta(seconds=e["duration"])
        if f <= lo or s >= hi:
            continue
        overlap = sum(max(0.0, (min(f, a1) - max(s, a0)).total_seconds()) for a0, a1 in active
                      if a0 < f and a1 > s)
        if overlap > 0:
            out.append({"timestamp": e["timestamp"], "duration": overlap, "data": e["data"]})
    return sorted(out, key=lambda e: e["timestamp"])


def attribute(events: list[dict], pdf_s: dict, sheet_s: dict) -> float:
    setup_s = 0.0
    last = None
    for e in events:
        title = e["data"].get("title", "")
        dur = float(e["duration"])
        sid = None if SHEET.search(title) else match_study(title)
        if sid:
            last = sid
            pdf_s[last] = pdf_s.get(last, 0.0) + dur
        elif SHEET.search(title):
            if last:
                sheet_s[last] = sheet_s.get(last, 0.0) + dur
            else:
                setup_s += dur
    return setup_s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--studies", default="", help="comma-separated ids to report; default all seen")
    ap.add_argument("--export", action="append", default=[],
                    help="ActivityWatch bucket export (JSON) from another machine; repeatable")
    ap.add_argument("--no-local", action="store_true", help="skip the local ActivityWatch server")
    args = ap.parse_args()

    load_aliases()
    pdf_s, sheet_s, setup_s = {}, {}, 0.0
    sources = [] if args.no_local else [query(args.start, args.end)]
    sources += [from_export(p, args.start, args.end) for p in args.export]
    # Attribute per machine: the sheet on one machine follows the PDF on that machine.
    for events in sources:
        setup_s += attribute(events, pdf_s, sheet_s)
    wanted = [s for s in args.studies.split(",") if s] or sorted(set(pdf_s) | set(sheet_s))
    rows = []
    for sid in wanted:
        p, s = pdf_s.get(sid, 0.0) / 60, sheet_s.get(sid, 0.0) / 60
        rows.append((sid, round(p, 1), round(s, 1), round(p + s, 1)))
    OUT.write_text("record_id,pdf_min,sheet_min,total_min\n"
                   + "\n".join(",".join(map(str, r)) for r in rows) + "\n", encoding="utf-8")
    for r in rows:
        print(*r)
    totals = [r[3] for r in rows if r[3] > 0]
    if totals:
        print(f"\nstudies with time: {len(totals)}; total {sum(totals):.0f} min; "
              f"median {statistics.median(totals):.1f} min; "
              f"IQR {statistics.quantiles(totals, n=4)[0]:.1f}-{statistics.quantiles(totals, n=4)[2]:.1f} min; "
              f"setup (before first study) {setup_s/60:.1f} min")
    print(f"written {OUT}")


if __name__ == "__main__":
    main()
