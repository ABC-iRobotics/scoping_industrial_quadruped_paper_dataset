"""PRISMA-ScR flow counts and Fig. 1, derived from the screening files.

Every number is computed from the files the pipeline wrote; none is typed in.
The prior paper's flow diagram did not balance precisely because its numbers
were transcribed, so this script also checks that every box adds up and stops
if one does not.

Layout follows the PRISMA 2020 template for updated reviews: a "previous
studies" column (the 88-study round-1 baseline) beside the database column for
the new search round, both feeding the total.

INPUTS
    work/charting_v2_prisma.md is NOT read - it is a report. The counts come from:
    work/r2_01_converted.xlsx        records identified, per database
    work/r2_02_deduplicated.xlsx     after within-round deduplication
    work/r2_03_to_screen.xlsx        after removing records already in the baseline
    work/r2_04_screening_round1.xlsx title/abstract pass 1
    work/r2_05_screening_round2.xlsx title/abstract pass 2
    work/r2_06_fulltext_needed.xlsx  reports sought for retrieval
    work/r2_06b_fulltext_recheck.xlsx records reinstated at the human title recheck
    work/fulltext_decisions.xlsx     full-text decisions (P.Z.)
    work/rci_include_list.xlsx       the 88 baseline studies

OUTPUTS
    work/prisma_counts.csv, work/prisma_counts.md
    ../figures/fig1_prisma.pdf (and .png for preview)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from _common import WORK_DIR

FIG_DIR = WORK_DIR.parent.parent / "figures"
REASON_LABEL = {
    "no_industrial_use_case": "No industrial use case",
    "simulation_only": "Simulation only",
    "low_level_control_only": "Low-level control only",
    "not_primary_study_or_excluded_type": "Not a primary study",
    "non_quadruped_platform": "Non-quadruped platform",
    "duplicate_or_companion_report": "Duplicate or companion report",
    "non_english": "Not in English",
    "other": "Other",
}


def db_counts(frame: pd.DataFrame) -> dict[str, int]:
    src = frame["Source"].astype(str).str.lower()
    out = {}
    for name, key in (("IEEE Xplore", "ieee"), ("Scopus", "scopus"), ("Web of Science", "wos|web of science|savedrecs")):
        out[name] = int(src.str.contains(key).sum())
    return out


def main() -> None:
    c: dict[str, int] = {}
    conv = pd.read_excel(WORK_DIR / "r2_01_converted.xlsx")
    dbs = db_counts(conv)
    c["identified_total"] = len(conv)
    if sum(dbs.values()) != c["identified_total"]:
        raise SystemExit(f"ERROR: per-database counts {dbs} do not sum to {len(conv)}")
    for k, v in dbs.items():
        c[f"identified_{k}"] = v
    dedup = pd.read_excel(WORK_DIR / "r2_02_deduplicated.xlsx")
    c["duplicates_within_round"] = len(conv) - len(dedup)
    screen = pd.read_excel(WORK_DIR / "r2_03_to_screen.xlsx")
    c["already_in_baseline"] = len(dedup) - len(screen)
    c["screened"] = len(screen)

    s1 = pd.read_excel(WORK_DIR / "r2_04_screening_round1.xlsx")
    s2 = pd.read_excel(WORK_DIR / "r2_05_screening_round2.xlsx")
    need = pd.read_excel(WORK_DIR / "r2_06_fulltext_needed.xlsx")
    model_excl = c["screened"] - len(need)
    c["excluded_ta_pass1"] = int((s1["Decision round 1 (gpt-oss:120b)"] == "N").sum())
    c["excluded_ta_pass2"] = int((s2["Decision (gpt-oss:120b)"] == "Exclude").sum())
    if c["excluded_ta_pass1"] + c["excluded_ta_pass2"] != model_excl:
        raise SystemExit("ERROR: title/abstract exclusions do not add up")
    # P.Z. re-read every model exclusion by title (ta_exclusion_scan.xlsx) and
    # sent some back to full text; those leave the exclusion box.
    recheck_path = WORK_DIR / "r2_06b_fulltext_recheck.xlsx"
    recheck = pd.read_excel(recheck_path) if recheck_path.exists() else need.iloc[0:0]
    if set(recheck["record_id"]) & set(need["record_id"]):
        raise SystemExit("ERROR: a recheck record was already sought")
    c["excluded_ta_model"] = model_excl
    c["reinstated_on_recheck"] = len(recheck)
    c["excluded_title_abstract"] = model_excl - len(recheck)
    need = pd.concat([need, recheck], ignore_index=True)
    c["sought"] = len(need)

    dec = pd.read_excel(WORK_DIR / "fulltext_decisions.xlsx")
    fd = dec["final_decision"].astype(str).str.strip().str.lower()
    if set(dec["record_id"]) != set(need["record_id"]):
        raise SystemExit("ERROR: decision sheet and sought list differ")
    if fd.isin(["include", "exclude", "not_retrieved"]).sum() != len(dec):
        raise SystemExit("ERROR: undecided rows in fulltext_decisions.xlsx")
    c["not_retrieved"] = int((fd == "not_retrieved").sum())
    c["assessed"] = c["sought"] - c["not_retrieved"]
    excl = dec[fd == "exclude"]
    c["excluded_full_text"] = len(excl)
    reasons = excl["final_reason"].astype(str).value_counts()
    for k, v in reasons.items():
        c[f"reason_{k}"] = int(v)
    if reasons.sum() != c["excluded_full_text"]:
        raise SystemExit("ERROR: every full-text exclusion needs exactly one reason")
    c["included_new"] = int((fd == "include").sum())
    if c["assessed"] - c["excluded_full_text"] != c["included_new"]:
        raise SystemExit("ERROR: full-text box does not balance")
    c["previous_studies"] = len(pd.read_excel(WORK_DIR / "rci_include_list.xlsx"))
    c["included_total"] = c["previous_studies"] + c["included_new"]

    chain = (c["identified_total"] - c["duplicates_within_round"] - c["already_in_baseline"]
             == c["screened"]) and (c["screened"] - c["excluded_title_abstract"] == c["sought"])
    if not chain:
        raise SystemExit("ERROR: identification/screening chain does not balance")

    pd.Series(c).to_csv(WORK_DIR / "prisma_counts.csv", header=["n"])
    lines = ["# PRISMA-ScR counts (generated by 39_prisma_flow.py; all boxes balance)", "",
             "| Quantity | n |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in c.items()]
    (WORK_DIR / "prisma_counts.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    draw(c, reasons)


def draw(c: dict[str, int], reasons: pd.Series) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5})
    fig, ax = plt.subplots(figsize=(7.2, 7.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ink, rule, side = "#1f1f1f", "#8a8a8a", "#f2f2f2"

    def box(x, y, w, h, text, fill="white", bold_first=False):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8",
                                    linewidth=0.8, edgecolor=ink, facecolor=fill))
        ax.text(x + 1.4, y + h - 1.4, text, va="top", ha="left", color=ink, linespacing=1.35)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", lw=0.8, color=ink, shrinkA=0, shrinkB=0))

    def band(y, h, label):
        ax.add_patch(FancyBboxPatch((0, y), 4.2, h, boxstyle="round,pad=0.1,rounding_size=0.6",
                                    linewidth=0, facecolor="#dfe7f0"))
        ax.text(2.1, y + h / 2, label, rotation=90, ha="center", va="center", fontweight="bold")

    # headers
    box(6, 93, 24, 5.5, "Previous studies", fill=side)
    box(33, 93, 66, 5.5, "New studies via databases (round 2, cut-off 3 September 2026)", fill=side)

    band(72.5, 19, "Identification")
    band(40.5, 29, "Screening")
    band(3.5, 31, "Included")

    box(6, 73, 24, 18, f"Studies included in the\nprevious review\n(round 1, searched\n21 May 2026)\n(n = {c['previous_studies']})")
    box(33, 73, 30, 18,
        "Records identified from\ndatabases (n = {:,}):\n  IEEE Xplore (n = {:,})\n  Scopus (n = {:,})\n  Web of Science (n = {:,})".format(
            c["identified_total"], c["identified_IEEE Xplore"], c["identified_Scopus"], c["identified_Web of Science"]))
    box(66, 73, 33, 18,
        "Records removed before\nscreening:\n  Duplicates within round 2\n  (n = {:,})\n  Already in previous review\n  (n = {:,})".format(
            c["duplicates_within_round"], c["already_in_baseline"]))
    arrow(63, 82, 66, 82)

    box(33, 61, 30, 8, f"Records screened\n(title and abstract)\n(n = {c['screened']:,})")
    box(66, 61, 33, 8, f"Records excluded\n(n = {c['excluded_title_abstract']:,})")
    arrow(48, 73, 48, 69)
    arrow(63, 65, 66, 65)

    box(33, 51, 30, 7, f"Reports sought for retrieval\n(n = {c['sought']})")
    box(66, 51, 33, 7, f"Reports not retrieved\n(n = {c['not_retrieved']})")
    arrow(48, 61, 48, 58)
    arrow(63, 54.5, 66, 54.5)

    box(33, 41, 30, 7, f"Reports assessed for eligibility\n(n = {c['assessed']})")
    reason_text = "\n".join(f"  {REASON_LABEL.get(k, k)} (n = {v})" for k, v in reasons.items())
    box(66, 27, 33, 21, f"Reports excluded\n(n = {c['excluded_full_text']}):\n{reason_text}")
    arrow(48, 51, 48, 48)
    arrow(63, 44.5, 66, 44.5)

    box(33, 25, 30, 9, f"New studies included\n(n = {c['included_new']})")
    arrow(48, 41, 48, 34)

    box(6, 4, 57, 10, f"Total studies included in this review\n(n = {c['included_total']})", fill="#eef3f8")
    arrow(18, 73, 18, 14)
    arrow(48, 25, 48, 14)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / "fig1_prisma.pdf", bbox_inches="tight")
    fig.savefig(FIG_DIR / "fig1_prisma.png", dpi=200, bbox_inches="tight")
    print(f"written {FIG_DIR / 'fig1_prisma.pdf'}")


if __name__ == "__main__":
    main()
