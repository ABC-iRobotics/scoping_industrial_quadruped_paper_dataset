"""
Stage 1 - remove duplicate records.

WHAT IT DOES
    Deduplicates the pooled search results in two passes:
      1. by normalised title (lowercased, punctuation stripped, whitespace
         collapsed)
      2. by DOI, among the records that survived pass 1 and carry a DOI
    Records with a DOI are sorted first so that when two records share a title,
    the one carrying a DOI is the one kept. Surviving records are renumbered
    from 1.

INPUTS
    work/01_converted_papers.xlsx   output of 00_ris_to_xlsx.py

OUTPUTS
    work/02_deduplicated.xlsx

PAPER REFERENCE
    Section II-D (Study Selection): "Deduplication was performed using a custom
    Python script that identified matching records based on their titles and
    Digital Object Identifiers (DOIs)". Produces the "Duplicate records removed"
    box of the PRISMA-ScR flow diagram in Fig. 1.

NOTE ON RECORD COUNTS
    Run on the original exports this stage removes 219 duplicates, leaving 1371
    records. The paper reports 220 removed. The surviving count of 1371 matches
    the paper exactly. See README.md, "Known discrepancies".
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from _common import WORK_DIR


def deduplicate(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the two-pass title-then-DOI deduplication and renumber survivors."""
    # Normalised title used only for matching; dropped before writing.
    clean_title = frame["Title"].astype(str).str.lower()
    clean_title = clean_title.replace(r"[^\w\s]", "", regex=True)
    clean_title = clean_title.replace(r"\s+", " ", regex=True).str.strip()
    frame = frame.assign(Clean_Title=clean_title, Has_Doi=frame["Doi"] != "na")

    # Records with a DOI first, so drop_duplicates(keep="first") prefers them.
    frame = frame.sort_values(by=["Has_Doi", "N"], ascending=[False, True])

    # Pass 1: by normalised title.
    frame = frame.drop_duplicates(subset=["Clean_Title"], keep="first")

    # Pass 2: by DOI, among records that have one.
    with_doi = frame[frame["Doi"] != "na"].drop_duplicates(subset=["Doi"], keep="first")
    without_doi = frame[frame["Doi"] == "na"]
    frame = pd.concat([with_doi, without_doi])

    # Restore import order, drop the helper columns, renumber from 1.
    frame = frame.sort_values(by="N").drop(columns=["Clean_Title", "Has_Doi"])
    frame["N"] = range(1, len(frame) + 1)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--input",
        default=str(WORK_DIR / "01_converted_papers.xlsx"),
        help="input spreadsheet (default: work/01_converted_papers.xlsx)",
    )
    parser.add_argument(
        "--output",
        default=str(WORK_DIR / "02_deduplicated.xlsx"),
        help="output spreadsheet (default: work/02_deduplicated.xlsx)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"ERROR: input not found: {input_path}\nRun 00_ris_to_xlsx.py first.")

    frame = pd.read_excel(input_path)
    before = len(frame)

    frame = deduplicate(frame)
    after = len(frame)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_excel(output_path, index=False)

    print(f"Records in:       {before}")
    print(f"Duplicates removed: {before - after}")
    print(f"Records out:      {after}")
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
