"""
Stage 60 - assemble the public release for the Sensors paper.

The release goes into a new folder, sensors2026/, of the existing dataset
repository (ABC-iRobotics/scoping_industrial_quadruped_paper_dataset), and the
paper cites a tag of that repository. This script builds the folder locally;
pushing and tagging are done by hand, after review.

WHAT GOES IN
    code/       every script that produced a reported number, the prompts, the
                run scripts, requirements
    protocol/   the registered protocol, the amendment log, the search
                strategy as executed, the validation-sample draw
    data/       the frozen charting table and every human decision that fed it:
                codebooks, adjudication and re-adjudication logs, the blind
                validation coding, full-text decisions, the title-scan recheck,
                the baseline eligibility audit, per-pass extraction records
                with their evidence quotes, and the files that amendments
                refer to as retained (pre-amendment pass A, the withdrawn
                pass-B model)
    results/    agreement and accuracy tables, PRISMA counts, the generated
                numbers, figures and LaTeX tables

WHAT STAYS OUT
    full texts (copyright); database exports and abstracts (providers' terms,
    as in the SISY release - the Abstract and Keywords columns are dropped);
    raw ActivityWatch logs (personal data; only the derived minutes ship);
    archives and exploratory runs that feed no reported number.

USAGE
    python scripts/60_build_release.py [--out ../../ZsoP_MDPI_Sensors_quadruped_release/sensors2026]
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

ANALYSIS = Path(__file__).resolve().parent.parent
ROOT = ANALYSIS.parent
WORK = ANALYSIS / "work"
DROP_COLUMNS = {"Abstract", "Keywords", "Reference", "abstract", "keywords"}

CODE = ["scripts/*.py", "prompts/*.md", "run_*.sh", "requirements.txt", "README.md", "data_dictionary.md", "LICENSE"]
CODE_EXCLUDE = {"probe_context.py", "probe_pdf_window.py"}
PROTOCOL = ["protocol/*.md", "search/*.md"]
DATA_ROOT = ["data/charting_v2.xlsx"]
DATA_WORK = [
    "codebook_sensors.xlsx", "codebook_compute.xlsx", "codebook_sector.xlsx",
    "adjudication_rci.xlsx", "adjudication_cap.xlsx", "adjudication_rci.html", "adjudication_cap.html",
    "readjudication_yes.xlsx", "readjudication_yes.html",
    "validation/validation_coding_baseline_v2.xlsx",
    "fulltext_decisions.xlsx", "ta_exclusion_scan.xlsx", "ta_recheck_decisions.xlsx",
    "baseline_audit_review.xlsx", "fte_A_baseline_audit_records.xlsx",
    "fte_A_records.xlsx", "fte_B_records.xlsx", "fte_A_recheck_records.xlsx", "fte_B_recheck_records.xlsx",
    "rci_A_all_records.xlsx", "rci_B_all_records.xlsx", "cap_A_all_records.xlsx", "cap_B_all_records.xlsx",
    "rci_A_v1_records.xlsx", "rci_B_qwen36_records.xlsx", "cap_B_qwen36_records.xlsx", "fte_A_v1_records.xlsx",
    "r2_03_to_screen.xlsx", "r2_04_screening_round1.xlsx", "r2_05_screening_round2.xlsx",
    "r2_06_fulltext_needed.xlsx", "r2_06b_fulltext_recheck.xlsx", "validation/coding_time.csv",
]
RESULTS_WORK = [
    "agreement_rci_pass_A_vs_B_all.csv", "agreement_cap_pass_A_vs_B_all.csv", "agreement_amendment_A1_effect.csv",
    "validation_accuracy.csv", "validation_accuracy.md", "pipeline_vs_human.csv", "prisma_counts.csv",
    "results_numbers.csv", "pipeline_numbers.csv", "review_time_numbers.csv", "results_sensitivity.csv",
    "results_tables.md", "class_validation.csv", "recall_baseline_round1.xlsx", "recall_baseline_round2.xlsx",
]
RESULTS_ROOT = ["figures/*.pdf", "tables/*.tex", "numbers.tex", "supplementary/supplementary.tex", "supplementary/supplementary.pdf"]


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix == ".xlsx":
        sheets = pd.read_excel(src, sheet_name=None)
        visible = {}
        for name, frame in sheets.items():
            if name.startswith("v1_archive"):
                continue
            visible[name] = frame.drop(columns=[c for c in frame.columns if c in DROP_COLUMNS])
        with pd.ExcelWriter(dst) as writer:
            for name, frame in visible.items():
                frame.to_excel(writer, sheet_name=name, index=False)
    else:
        shutil.copy2(src, dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT.parent / "ZsoP_MDPI_Sensors_quadruped_release" / "sensors2026"))
    args = ap.parse_args()
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"ERROR: {out} exists; remove it or choose another --out")

    plan: list[tuple[Path, Path]] = []
    for pattern in CODE:
        for src in sorted(ANALYSIS.glob(pattern)):
            if src.name not in CODE_EXCLUDE:
                plan.append((src, out / "code" / src.relative_to(ANALYSIS)))
    for pattern in PROTOCOL:
        for src in sorted(ANALYSIS.glob(pattern)):
            plan.append((src, out / "protocol" / src.name))
    for rel in DATA_ROOT:
        plan.append((ROOT / rel, out / "data" / Path(rel).name))
    for rel in DATA_WORK:
        plan.append((WORK / rel, out / "data" / "pipeline" / Path(rel).name))
    for rel in RESULTS_WORK:
        plan.append((WORK / rel, out / "results" / Path(rel).name))
    for pattern in RESULTS_ROOT:
        for src in sorted(ROOT.glob(pattern)):
            plan.append((src, out / "results" / src.relative_to(ROOT)))

    missing = [str(s) for s, _ in plan if not s.exists()]
    if missing:
        raise SystemExit("ERROR: missing inputs:\n  " + "\n  ".join(missing))
    for src, dst in plan:
        copy(src, dst)
    print(f"{len(plan)} files -> {out}")


if __name__ == "__main__":
    main()
