"""Combine baseline and round-2 extraction records into one file per pass.

Baseline and round 2 were extracted into separate files (pass labels A/B,
A_r2/B_r2, and A_r2b/B_r2b for the studies reinstated at the title-scan recheck) so that the round-2 run could never overwrite the baseline. Every
downstream step - agreement, adjudication, codebook, analysis - works on the
included corpus as a whole, so this writes

    work/{rci,cap}_{A,B}_all_records.xlsx

restricted to the included studies: the 88 baseline studies plus the round-2
records P.Z. included at full text (fulltext_decisions.xlsx, final_decision ==
include). Round-2 studies extracted but later excluded (r2-0234, r2-0581) are
dropped here, so they cannot leak into any count. A `search_round` column is
added (1 = baseline, 2 = round 2).

Usage:
    python scripts/38_combine_records.py
"""
from __future__ import annotations

import pandas as pd

from _common import WORK_DIR


def included() -> tuple[set[str], set[str]]:
    base = set(pd.read_excel(WORK_DIR / "rci_include_list.xlsx")["Pdf name"].astype(str))
    dec = pd.read_excel(WORK_DIR / "fulltext_decisions.xlsx")
    r2 = set(dec.loc[dec["final_decision"].astype(str).str.strip().str.lower() == "include",
                     "record_id"].astype(str))
    return base, r2


def main() -> None:
    base, r2 = included()
    print(f"included: {len(base)} baseline + {len(r2)} round 2 = {len(base) + len(r2)}")
    for tool in ("rci", "cap"):
        for label in ("A", "B"):
            parts = []
            for suffixes, ids, rnd in ((("",), base, 1), (("_r2", "_r2b"), r2, 2)):
                frames = []
                for suffix in suffixes:
                    p = WORK_DIR / f"{tool}_{label}{suffix}_records.xlsx"
                    if p.exists():
                        frames.append(pd.read_excel(p))
                    elif suffix != "_r2b":
                        raise SystemExit(f"ERROR: {p} missing")
                f = pd.concat(frames, ignore_index=True)
                f = f[f["Pdf name"].astype(str).isin(ids)].copy()
                if f["Pdf name"].duplicated().any():
                    raise SystemExit(f"ERROR: a study is extracted in more than one {tool}_{label} file")
                missing = ids - set(f["Pdf name"].astype(str))
                if missing:
                    raise SystemExit(f"ERROR: {tool}_{label} records lack included studies: {sorted(missing)}")
                f.insert(1, "search_round", rnd)
                parts.append(f)
            out = WORK_DIR / f"{tool}_{label}_all_records.xlsx"
            combined = pd.concat(parts, ignore_index=True)
            combined.to_excel(out, index=False)
            status = combined["status"].value_counts().to_dict() if "status" in combined else {}
            print(f"{out.name}: {len(combined)} studies, status {status}")


if __name__ == "__main__":
    main()
