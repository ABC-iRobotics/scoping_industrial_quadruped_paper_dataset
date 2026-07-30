"""
Stage 5 - build the published dataset from the full local extraction.

WHAT IT DOES
    Reads the full extraction, keeps only the columns on the PUBLISHED_COLUMNS
    allowlist, normalises a handful of data-entry inconsistencies, and writes the
    public spreadsheet.

INPUTS
    work/06_extraction.xlsx     the full extraction (34 columns), or any
                                spreadsheet passed with --input

OUTPUTS
    data/SISY2026_ScopingIndustrialQuadruped.xlsx   the published dataset

PAPER REFERENCE
    Section VI (Data Availability).

WHY AN ALLOWLIST AND NOT A DROP-LIST
    The published dataset is deliberately a subset of the full extraction. The
    withheld columns are not reported anywhere in the paper and are reserved for
    follow-up work. An allowlist fails safe: if a new column is added to the
    extraction later, it stays unpublished until someone deliberately adds it
    here. A drop-list would leak it by default. Do not replace this with a
    drop-list.

WHY THE ABSTRACT COLUMN IS NOT PUBLISHED
    The Abstract column WAS used, and it matters methodologically: both screening
    rounds consumed title + abstract, so the abstracts are the actual input to
    the LLM screening described in Section II-D. They are nevertheless not
    redistributed here, because the abstracts are the publishers' copyrighted
    material, retrieved from Scopus and IEEE Xplore exports.

    This follows PRISMA-S (Rethlefsen et al., Systematic Reviews, 2021), which
    states that "abstracts are copyrighted materials and should be removed from
    files before sharing them publicly", and PRISMA 2020 item 27, which notes
    that records exported from bibliographic databases typically include
    copyrighted material.

    06_rehydrate_abstracts.py retrieves abstracts from OpenAlex and Semantic
    Scholar for the published DOIs, so that the screening inputs can be
    reconstructed locally where those sources carry them.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from _common import DATA_DIR, WORK_DIR

# --------------------------------------------------------------------------
# The allowlist. Exactly these columns, in exactly this order, are published.
# Adding a column here is a deliberate act of publication - check first that it
# contains nothing withheld on purpose and nothing third-party copyrighted.
# --------------------------------------------------------------------------
PUBLISHED_COLUMNS = [
    "Pdf name",
    "N",
    "Source",
    "Author",
    "Year",
    "Journal",
    "Type",
    "Title",
    "Keywords",
    "Reference",
    "Doi",
    "Decision (gpt-oss:120b)",
    "Final decision",
    "Robot platform",
    "Industry sector",
    "High-level goal",
    "Real-world validation?",
    "Open source?",
]

# Columns in the full extraction whose published name differs. The published
# "Decision (gpt-oss:120b)" column holds the SECOND screening round's decision;
# the first round's letter (Y/N/U) is not published.
COLUMN_RENAMES = {
    "Second decision (gpt-oss:120b)": "Decision (gpt-oss:120b)",
    # The original working files labelled the first round in Hungarian.
    "Döntés (gpt-oss:120b)": "Decision round 1 (gpt-oss:120b)",
}

# Columns whose values are free-text and were typed by hand, so they contain
# case and whitespace variants of the same value.
NORMALIZE_COLUMNS = ["Source", "Industry sector", "Robot platform", "High-level goal"]


def derive_source(value: str) -> str:
    """
    Map a raw RIS export filename onto the source database name.

    The full extraction records the export filename each record came from; the
    published dataset names the database instead.
    """
    lowered = str(value).lower()
    if "scopus" in lowered:
        return "Scopus"
    if "ieee" in lowered:
        return "IEEE Xplore"
    return str(value).strip()


def normalize_case_variants(series: pd.Series) -> tuple[pd.Series, dict[str, str]]:
    """
    Collapse values that differ only in case or surrounding whitespace.

    For each group of values that are equal when casefolded and stripped, the
    most frequent spelling wins. This fixes data-entry variants such as
    "Chemical Industry" / "Chemical industry" and "Oil & gas" / "Oil & Gas"
    without merging anything that is genuinely a different value.

    Returns the normalised series and a mapping of the changes made, so the
    caller can report them rather than applying them silently.
    """
    stripped = series.astype(str).str.strip()
    canonical: dict[str, str] = {}
    for key, group in stripped.groupby(stripped.str.casefold()):
        canonical[key] = group.value_counts().idxmax()

    normalized = stripped.map(lambda value: canonical[value.casefold()])
    changes = {
        original: new
        for original, new in zip(series.astype(str), normalized)
        if original != new
    }
    return normalized, changes


def build(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, str]]]:
    """Apply renames, derive Source, normalise variants, then project the allowlist."""
    frame = frame.rename(columns=COLUMN_RENAMES)

    if "Source" in frame.columns:
        frame["Source"] = frame["Source"].map(derive_source)

    all_changes: dict[str, dict[str, str]] = {}
    for column in NORMALIZE_COLUMNS:
        if column in frame.columns:
            frame[column], changes = normalize_case_variants(frame[column])
            if changes:
                all_changes[column] = changes

    missing = [column for column in PUBLISHED_COLUMNS if column not in frame.columns]
    if missing:
        raise SystemExit(
            "ERROR: the input is missing columns required by PUBLISHED_COLUMNS:\n  "
            + "\n  ".join(missing)
        )

    return frame[PUBLISHED_COLUMNS].copy(), all_changes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--input",
        default=str(WORK_DIR / "06_extraction.xlsx"),
        help="the full extraction (default: work/06_extraction.xlsx)",
    )
    parser.add_argument(
        "--output",
        default=str(DATA_DIR / "SISY2026_ScopingIndustrialQuadruped.xlsx"),
        help="published dataset (default: data/SISY2026_ScopingIndustrialQuadruped.xlsx)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"ERROR: input not found: {input_path}")

    source_frame = pd.read_excel(input_path)
    published, changes = build(source_frame)

    withheld = [
        column
        for column in source_frame.rename(columns=COLUMN_RENAMES).columns
        if column not in set(PUBLISHED_COLUMNS)
    ]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    published.to_excel(output_path, index=False)

    print(f"Input:     {input_path}  ({len(source_frame)} rows, {len(source_frame.columns)} columns)")
    print(f"Published: {output_path}  ({len(published)} rows, {len(published.columns)} columns)")

    print(f"\nWithheld columns ({len(withheld)}):")
    for column in withheld:
        print(f"  - {column}")

    if changes:
        print("\nNormalisation applied:")
        for column, mapping in changes.items():
            for original, new in sorted(mapping.items()):
                print(f"  {column}: {original!r} -> {new!r}")
    else:
        print("\nNormalisation applied: none needed.")


if __name__ == "__main__":
    main()
