"""Form and consistency checks on the human validation coding.

Checks only what the coding rules make mechanical - never whether a code is
right, because the human coding is the reference standard and must not be
nudged by anything derived from model output. Reads only the coding sheet and
the PDFs.

Flags: empty or non-yes/no codes; yes without a quote; specificity that
contradicts its RCI item; raw fields that contradict their specificity; AI/ML
field holding a sentence or a bare "no"; holistic note that argues only from
code availability (that is rci9, not the holistic question); quotes that cannot
be found in the PDF text (4-word shingle overlap below 80%).

Usage:
    python scripts/35_check_validation.py work/validation/validation_coding_baseline_v2.xlsx
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from _common import pdf_text

PDF_DIR = Path(__file__).resolve().parent.parent / "work" / "validation" / "pdf"


def s(v) -> str:
    return "" if pd.isna(v) else str(v).strip()


def words(t: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", t.lower().replace("ﬁ", "fi").replace("ﬂ", "fl"))


def main() -> None:
    d = pd.read_excel(sys.argv[1], sheet_name="coding")
    yn = [c for c in d.columns
          if (c.startswith(("rci", "cap_")) or c == "reproducible_holistic") and "__" not in c]
    coded = d[d[yn].notna().any(axis=1)]
    print(f"coded studies: {len(coded)}")
    total = 0
    for _, r in coded.iterrows():
        issues = []
        for c in yn:
            v = s(r[c]).lower()
            q = s(r.get(c + "__quote", ""))
            if v == "":
                issues.append(f"{c} empty")
            elif v not in ("yes", "no"):
                issues.append(f"{c}={v!r} is not yes/no")
            elif c != "reproducible_holistic" and v == "yes" and not q:
                issues.append(f"{c} yes without quote")
        for c in ("sensor_specificity", "compute_specificity", "eval_environment_kind"):
            if not s(r[c]):
                issues.append(f"{c} empty")
        if (s(r.sensor_specificity) == "model") != (s(r.rci2_sensors_model) == "yes"):
            issues.append("sensor_specificity and rci2 disagree")
        if s(r.compute_specificity) != "model" and s(r.rci3_compute_model) == "yes":
            issues.append("rci3 yes but compute_specificity is not model")
        if s(r.sensor_specificity) in ("model", "modality") and not s(r.optical_sensors_raw):
            issues.append("sensor specificity set but optical_sensors_raw empty")
        if s(r.compute_specificity) in ("model", "modality") and not s(r.onboard_computer_raw):
            issues.append("compute specificity set but onboard_computer_raw empty")
        a = s(r.ai_ml_solutions_raw)
        if a.lower() in ("no", "none", "n/a") or len(a) > 80:
            issues.append(f"ai_ml_solutions_raw should be method names or empty: {a[:50]!r}")
        n = s(r.reproducible_holistic__note).lower()
        if not n:
            issues.append("reproducible_holistic__note empty")
        elif re.search(r"code|github", n) and not re.search(r"hardware|software|descri|parameter|sensor|detail|setup", n):
            issues.append("holistic note argues from code only")
        for c in ("industry_sector_raw", "high_level_goal_raw"):
            if not s(r[c]):
                issues.append(f"{c} empty")

        pdf = PDF_DIR / f"{r.record_id}.pdf"
        if pdf.exists():
            text = " ".join(words(pdf_text(pdf)))
            for c in [c for c in d.columns if c.endswith("__quote")]:
                q = s(r[c])
                if not q or re.fullmatch(r"(?i)\s*(fig|table)\.?\s*\w+\s*", q):
                    continue
                w = words(q)
                sh = [" ".join(w[i:i + 4]) for i in range(max(1, len(w) - 3))]
                frac = sum(x in text for x in sh) / len(sh)
                if frac < 0.8:
                    issues.append(f"{c}: quote not found in PDF ({frac:.0%}): {q[:60]!r}")
        total += len(issues)
        print(f"== {r.record_id}: {'OK' if not issues else ''}")
        for i in issues:
            print("   -", i)
    print(f"\n{total} issue(s)")


if __name__ == "__main__":
    main()
