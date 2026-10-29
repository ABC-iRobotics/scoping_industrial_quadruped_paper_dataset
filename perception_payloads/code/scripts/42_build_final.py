"""Build the final charting table: one row per included study, final codes only.

FINAL CODE RULE, per study and binary item
    - both passes extracted the study completely and agree  -> that code;
    - the passes disagree, or one pass is incomplete         -> the human's
      adjudicated code from adjudication_{rci,cap}.xlsx (final_code);
    - a needed adjudication is still empty                   -> left blank, and
      the study is listed as pending. Nothing is guessed.
    Two human sources take precedence over the rule above:
    - re-adjudication with context (readjudication_yes.xlsx, stage 43): where
      final_code is filled, it replaces the first adjudicated "yes";
    - the blind validation subsample: for the 23 studies P.Z. coded from the
      full text without model output, her codes are the final codes. They are
      the best codes this review has; the accuracy figures are computed from the
      pass and adjudication codes before this replacement.
    `code_source` records which applied to each study.
    The RCI is the sum of the nine final RCI items, computed only where all
    nine are final. `rci3_strict` is the sensitivity version of item 3 that
    also requires at least one onboard compute string naming a specific model
    rather than a product family (codebook_compute.xlsx, family_only).

FREE-TEXT AND ORDINAL FIELDS
    Sensor and computer strings, specificity, evaluation environment kind,
    sector and goal come from pass A, the primary pass. Sensor, compute and
    sector strings are mapped to classes through the human-signed codebooks
    (final_class only); a string the codebook has not classified yet makes the
    study's class field pending.

OUTPUT
    ../data/charting_v2.xlsx - the dataset the paper reports, committed and
    tagged at the freeze (writing_plan.md 6.1). Rewritten on every run; it is
    derived, never edited by hand.

Usage:
    python scripts/42_build_final.py            refuses to write while anything is pending
    python scripts/42_build_final.py --draft    writes work/charting_v2_draft.xlsx anyway
"""
from __future__ import annotations

import argparse
import re

import pandas as pd

from _common import WORK_DIR, cell_text

DATA = WORK_DIR.parent.parent / "data"
VALIDATION = WORK_DIR / "validation" / "validation_coding_baseline_v2.xlsx"
READJ = WORK_DIR / "readjudication_yes.xlsx"


# Studies whose pass-A sector strings name no industrial sector (or no sector at
# all). P.Z. assigned these by hand on 23 October 2026; each is used only when
# the codebook leaves the study without an industrial class.
SECTOR_OVERRIDE = {
    "paper024": ("general_industrial", "no sector string in pass A; pass B 'industrial environments'; prior review 'General Industrial setting'"),
    "paper043": ("general_industrial", "unreadable PDF, no extraction; prior review 'General Industrial setting'"),
    "r2-1031": ("general_industrial", "no sector string in pass A; pass B 'industrial scenes'; workplace safety monitoring"),
    "paper067": ("mining", "no sector string; DARPA SubT exploration of mines and tunnels, as paper013 and r2-0192"),
    "r2-1169": ("general_industrial", "only 'urban environments' in pass A; the tests were in a warehouse, a garage and an obstacle pile"),
}
NON_SECTOR = {"not_industrial", ""}


def as_bool(v):
    t = cell_text(v).lower()
    if t in ("yes", "true", "1", "1.0"):
        return True
    if t in ("no", "false", "0", "0.0"):
        return False
    return None


def codebook(name: str) -> dict[str, str]:
    p = WORK_DIR / f"codebook_{name}.xlsx"
    if not p.exists():
        return {}
    c = pd.read_excel(p)
    return {str(r.raw_string): cell_text(r.final_class) for r in c.itertuples()}


def classes_for(raw, book: dict[str, str]) -> tuple[str, bool]:
    """Return ('; '-joined classes, complete?) for a free-text field value."""
    if pd.isna(raw) or not str(raw).strip():
        return "", True
    out, complete = [], True
    for part in re.split(r"[,;](?!\d)", str(raw)):
        key = " ".join(part.split()).lower().strip('"')
        if not key:
            continue
        cls = book.get(key, "")
        if not cls:
            complete = False
            continue
        out += [c.strip() for c in cls.split(";") if c.strip()]
    return "; ".join(sorted(set(out))), complete


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", action="store_true")
    args = ap.parse_args()

    pending = []
    tables = {}
    for tool in ("rci", "cap"):
        a = pd.read_excel(WORK_DIR / f"{tool}_A_all_records.xlsx").set_index("Pdf name")
        b = pd.read_excel(WORK_DIR / f"{tool}_B_all_records.xlsx").set_index("Pdf name")
        adj = WORK_DIR / f"adjudication_{tool}.xlsx"
        decided = {}
        if adj.exists():
            for r in pd.read_excel(adj).itertuples():
                v = as_bool(getattr(r, "final_code"))
                if v is not None:
                    decided[(r.pdf_name, r.item)] = v
        if READJ.exists():
            for r in pd.read_excel(READJ).itertuples():
                v = as_bool(r.final_code)
                if v is not None and (r.pdf_name, r.item) in decided:
                    decided[(r.pdf_name, r.item)] = v
        prefix = "rci" if tool == "rci" else "cap_"
        items = [c for c in a.columns if c.startswith(prefix) and "__" not in c
                 and c not in ("rci_total", "n_capabilities")]
        out = pd.DataFrame(index=a.index)
        out["search_round"] = a["search_round"]
        for item in items:
            vals = []
            for sid in a.index:
                ok_a = cell_text(a.at[sid, "status"]).lower() == "ok"
                ok_b = cell_text(b.at[sid, "status"]).lower() == "ok"
                va, vb = as_bool(a.at[sid, item]), as_bool(b.at[sid, item])
                if ok_a and ok_b and va is not None and va == vb:
                    vals.append(va)
                elif (sid, item) in decided:
                    vals.append(decided[(sid, item)])
                elif not ok_a and not ok_b:
                    vals.append(None)          # unreadable document: not coded
                else:
                    vals.append(None)
                    pending.append((sid, item))
            out[item] = vals
        tables[tool] = (out, a)

    rci, a_rci = tables["rci"]
    cap, a_cap = tables["cap"]
    final = rci.join(cap.drop(columns="search_round"))
    rci_items = [c for c in rci.columns if c.startswith("rci")]

    final["code_source"] = "passes + adjudication"
    human = pd.read_excel(VALIDATION).set_index("record_id")
    human = human[human["rci1_platform_model"].map(as_bool).notna()]
    for sid in human.index:
        if sid not in final.index:
            continue
        for item in rci_items + [c for c in cap.columns if c.startswith("cap_")]:
            if item in human.columns and as_bool(human.at[sid, item]) is not None:
                final.at[sid, item] = as_bool(human.at[sid, item])
        final.at[sid, "code_source"] = "human (blind validation coding)"
        pending[:] = [p for p in pending if p[0] != sid or p[1].startswith("codebook")]
    print(f"human codes used for {int((final['code_source'] != 'passes + adjudication').sum())} validation studies")
    final["rci_total"] = final[rci_items].apply(
        lambda r: int(sum(bool(x) for x in r)) if all(x is not None and not pd.isna(x) for x in r) else None, axis=1)

    for col in ("optical_sensors_raw", "onboard_computer_raw", "sensor_specificity",
                "compute_specificity", "eval_environment_kind", "status", "doc_pages"):
        final[col] = a_rci[col]
    for col in ("industry_sector_raw", "high_level_goal_raw", "ai_ml_solutions_raw"):
        final[col] = a_cap[col]

    # Sensor and compute strings: the blind human coding where it exists (the
    # 23 validation studies, consistent with their human codes above), else
    # pass A, else pass B when pass A listed nothing. The source is recorded.
    b_rci = pd.read_excel(WORK_DIR / "rci_B_all_records.xlsx").set_index("Pdf name")
    for col in ("optical_sensors_raw", "onboard_computer_raw"):
        src = []
        for sid in final.index:
            if sid in human.index and cell_text(human.at[sid, col]):
                final.at[sid, col] = cell_text(human.at[sid, col]); src.append("human")
            elif cell_text(final.at[sid, col]):
                src.append("pass A")
            elif sid in b_rci.index and cell_text(b_rci.at[sid, col]):
                final.at[sid, col] = cell_text(b_rci.at[sid, col]); src.append("pass B (pass A listed none)")
            else:
                src.append("none")
        final[col.replace("_raw", "_source")] = src

    for name, field, target in (("sensors", "optical_sensors_raw", "sensor_classes"),
                                ("compute", "onboard_computer_raw", "compute_classes"),
                                ("sector", "industry_sector_raw", "sector_classes")):
        book = codebook(name)
        res = [classes_for(v, book) for v in final[field]]
        final[target] = [r[0] for r in res]
        for sid, (_, complete) in zip(final.index, res):
            if not complete:
                pending.append((sid, f"codebook:{name}"))

    flags = pd.read_excel(WORK_DIR / "codebook_compute.xlsx")
    family = {str(r.raw_string) for r in flags.itertuples() if cell_text(getattr(r, "family_only", "")).lower() == "yes"}
    book = codebook("compute")
    def specific(raw) -> bool:
        for part in re.split(r"[,;](?!\d)", str(raw)) if not pd.isna(raw) else []:
            key = " ".join(part.split()).lower().strip('"')
            if key and key not in family and book.get(key, "") not in ("", "unspecified", "not_onboard"):
                return True
        return False
    final["rci3_strict"] = [bool(v) and specific(raw) if v is not None and not pd.isna(v) else None
                            for v, raw in zip(final["rci3_compute_model"], final["onboard_computer_raw"])]

    final["sector_source"] = "codebook"
    for sid, (cls, why) in SECTOR_OVERRIDE.items():
        if sid not in final.index:
            continue
        current = {c.strip() for c in str(final.at[sid, "sector_classes"]).split(";")}
        if current - NON_SECTOR:
            raise SystemExit(f"ERROR: {sid} has an industrial sector from the codebook; drop its override")
        final.at[sid, "sector_classes"] = cls
        final.at[sid, "sector_source"] = f"manual (P.Z., 23 Oct 2026): {why}"
        pending[:] = [p for p in pending if p != (sid, "codebook:sector")]
    for sid in final.index:
        current = {c.strip() for c in str(final.at[sid, "sector_classes"]).split(";")}
        if not current - NON_SECTOR and (sid, "codebook:sector") not in pending:
            pending.append((sid, "sector:none"))

    base = pd.read_excel(WORK_DIR.parent.parent / "data" / "full_text_screening_results.xlsx")
    meta = base.set_index("Pdf name")[["Author", "Year", "Title", "Doi", "Journal", "Reproducable?"]]
    r2 = pd.concat([pd.read_excel(WORK_DIR / f) for f in ("r2_06_fulltext_needed.xlsx", "r2_06b_fulltext_recheck.xlsx")])
    r2 = r2.set_index("record_id")[["Author", "Year", "Title", "Doi", "Journal"]]
    final = final.join(pd.concat([meta, r2]), how="left")
    final.index.name = "record_id"
    if final["Title"].isna().any():
        raise SystemExit(f"ERROR: no bibliographic record for {sorted(final.index[final['Title'].isna()])}")

    # Baseline studies that would not pass the eligibility criteria as applied
    # in round 2 (P.Z.'s review of the stage-13 audit, 28 Oct 2026; amendment
    # A12). They stay in the corpus; every main result is also reported without them.
    audit = pd.read_excel(WORK_DIR / "baseline_audit_review.xlsx")
    fails = set(audit.loc[audit["meets_criteria_today"].astype(str).str.strip().str.lower() == "no", "record_id"])
    final["fails_current_criteria"] = [sid in fails for sid in final.index]
    print(f"flagged for the sensitivity analysis: {len(fails)}")

    print(f"studies: {len(final)}; pending decisions: {len(pending)}")
    if pending:
        kinds = pd.Series([p[1].split(':')[0] if ':' in p[1] else 'adjudication' for p in pending]).value_counts()
        print(kinds.to_string())
    if pending and not args.draft:
        raise SystemExit("Not written: finish adjudication and codebook sign-off, or use --draft.")
    out = (WORK_DIR / "charting_v2_draft.xlsx") if args.draft else (DATA / "charting_v2.xlsx")
    final.to_excel(out)
    print(f"written {out}")


if __name__ == "__main__":
    main()
