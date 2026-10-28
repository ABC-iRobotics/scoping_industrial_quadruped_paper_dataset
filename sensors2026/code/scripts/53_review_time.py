"""
Stage 53 - human time spent on the LLM-assisted route, from ActivityWatch.

36_coding_time.py measures the manual route: blind coding of the validation
studies. This stage measures the human steps of the pipeline route, so the two
can be compared on the same instrument: active-window time (AFK excluded) on
the files of each step.

    codebook          codebook_{sensors,compute,sector}.xlsx
    adjudication      adjudication_{rci,cap}.xlsx and its HTML reading copy
    readjudication    readjudication_yes.xlsx / .html
    baseline review   baseline_audit_review.xlsx (and the PDFs opened for it
                      are not separable from other reading, so they are not
                      counted - the figure is a lower bound)
    title scan        ta_exclusion_scan.xlsx, ta_recheck_decisions.xlsx
                      (screening, reported separately from charting)

INPUT   work/validation/activitywatch/*.json (filtered exports; events are
        de-duplicated across files by timestamp and title)
OUTPUT  work/review_time_numbers.csv  macro,value for 40_emit_numbers.py;
        a step with no recorded time is left out, so its macro stays \\numTODO.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta

import pandas as pd

from _common import WORK_DIR

AW_DIR = WORK_DIR / "validation" / "activitywatch"
STEPS = {
    "TimeCodebookMin": r"codebook_",
    "TimeAdjMin": r"(?<!re)adjudication_(rci|cap)|^Adjudication —",
    "TimeReadjMin": r"readjudication|Re-adjudication with context",
    "TimeBaselineReviewMin": r"baseline_audit_review",
    "TimeTitleScanMin": r"ta_exclusion|ta_recheck",
}


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> None:
    windows, active = {}, []
    for path in sorted(AW_DIR.glob("*.json")):
        buckets = json.loads(path.read_text(encoding="utf-8"))["buckets"]
        for name, b in buckets.items():
            for e in b["events"]:
                if name.startswith("aw-watcher-window"):
                    windows[(e["timestamp"], e["data"].get("title", ""))] = e
                elif name.startswith("aw-watcher-afk") and e["data"].get("status") == "not-afk":
                    s = ts(e["timestamp"]); active.append((s, s + timedelta(seconds=e["duration"])))
    # Exports overlap in time, and an AFK event still open at export time comes
    # back with different durations; merge into disjoint intervals so no
    # active second is counted twice.
    merged = []
    for s, e in sorted(active):
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    active = merged

    def overlap(a: datetime, b: datetime) -> float:
        return sum(max(0.0, (min(b, y) - max(a, x)).total_seconds()) for x, y in active)

    out = {}
    for macro, pat in STEPS.items():
        rx = re.compile(pat, re.I)
        sec = 0.0
        for e in windows.values():
            if rx.search(str(e["data"].get("title", ""))):
                s = ts(e["timestamp"]); sec += overlap(s, s + timedelta(seconds=e["duration"]))
        if sec > 0:
            out[macro] = f"{sec / 60:.0f}"
    # Projection: the manual rate (median minutes per study on the validation
    # subsample) times the readable corpus, against the human minutes of the
    # pipeline's charting steps. Only when every step has been recorded.
    ct = WORK_DIR / "validation" / "coding_time.csv"
    steps = ("TimeCodebookMin", "TimeAdjMin", "TimeReadjMin")
    if ct.exists() and all(s in out for s in steps):
        t = pd.read_csv(ct); t = t[t["total_min"] > 0]
        n = int((pd.read_excel(WORK_DIR.parent.parent / "data" / "charting_v2.xlsx")["status"] == "ok").sum())
        manual = t["total_min"].median() * n
        pipe = sum(float(out[s]) for s in steps)
        val = t["total_min"].sum()
        out.update(ManualProjectedH=f"{manual / 60:.0f}", PipelineHumanH=f"{pipe / 60:.1f}",
                   TimeRatio=f"{manual / pipe:.0f}", TimeRatioWithVal=f"{manual / (pipe + val):.1f}")
    pd.Series(out, dtype=str).to_csv(WORK_DIR / "review_time_numbers.csv", header=["value"])
    print(out, "| missing:", [m for m in STEPS if m not in out])


if __name__ == "__main__":
    main()
