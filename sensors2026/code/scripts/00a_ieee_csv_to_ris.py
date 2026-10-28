"""
Stage 0a - convert an IEEE Xplore "Download Results" CSV into RIS.

WHY THIS EXISTS
    IEEE Xplore offers two ways out of a result set. The Citations tab emits
    RIS but is capped per batch, which is why search round 1 needed seven
    separate files for 617 records. The Results tab emits the *entire* set as
    one CSV, abstracts included - 729 records in a single file for round 2.

    The second is plainly better: one file, one download, no pagination
    boundaries to get wrong. But stage 0 (`00_ris_to_xlsx.py`) ingests RIS,
    and that script produced the round-1 baseline. Forking its parser to also
    read CSV would mean the two search rounds entered the corpus through
    different code - exactly the split provenance this project reuses the
    upstream pipeline to avoid.

    So convert instead. The CSV becomes RIS, lands in the same input folder as
    the Scopus and Web of Science exports, and stage 0 runs unchanged.

WHAT IT DOES
    Maps the IEEE CSV columns onto the RIS tags stage 0 actually reads:
    TY, AU, PY, TI, T2, AB, KW, DO, VL, IS, SP, EP.

    Every field is written on ONE line. Stage 0 treats a line beginning with
    six spaces as a continuation of the preceding title or abstract, so an
    embedded newline inside an abstract would silently truncate it there.
    Internal whitespace is collapsed rather than trusted.

INPUTS
    An IEEE Xplore Results CSV (28 columns, `Document Title` first).

OUTPUTS
    An RIS file. Stage 0 uses the *filename stem* as the `Source` column, so
    name it for the database and the search date: `ieee_xplore_2026-09-03.ris`.

USAGE
    python scripts/00a_ieee_csv_to_ris.py \
        --input work/round2_ris/ieee_xplore_2026-09-03.csv
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import pandas as pd

# IEEE's `Document Identifier` names the content type, and Xplore hosts partner
# content as well as its own: IET, VDE, Wiley, River, CES, FRPS, ZUP. Matching
# on the trailing noun covers every publisher without enumerating them, and the
# suffixes are stable in a way the publisher prefixes are not.
TYPE_SUFFIXES = (
    ("Conferences", "CPAPER"),
    ("Early Access Articles", "JOUR"),
    ("Journals", "JOUR"),
    ("Magazines", "MGZN"),
    ("eBook Chapters", "CHAP"),
    ("Books", "CHAP"),
    ("Standards", "STAND"),
)

WHITESPACE = re.compile(r"\s+")


def ris_type(identifier: str) -> str:
    """Map an IEEE `Document Identifier` onto an RIS type, GEN when unknown."""
    for suffix, ris in TYPE_SUFFIXES:
        if identifier.endswith(suffix):
            return ris
    return "GEN"


def flatten(value) -> str:
    """
    Collapse whitespace and decode HTML entities.

    The entity decoding is load-bearing, not cosmetic. IEEE's CSV encodes
    non-ASCII characters as entities - `M. Molla&#x2010;Hosseini` for a name
    containing a hyphen - and the semicolon that terminates the entity is the
    same character that separates authors and keywords. Splitting before
    decoding tears one author into two, which then propagates into the
    deduplication key and the corpus counts.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return WHITESPACE.sub(" ", html.unescape(str(value))).strip()


def split_list(value, separator: str = ";") -> list[str]:
    """Split a delimited IEEE field into cleaned parts, dropping empties."""
    flat = flatten(value)
    if not flat:
        return []
    return [part.strip() for part in flat.split(separator) if part.strip()]


def record_lines(row: pd.Series) -> list[str]:
    """Build the RIS lines for one CSV row."""
    doc_type = ris_type(flatten(row.get("Document Identifier")))
    lines = [f"TY  - {doc_type}"]

    for author in split_list(row.get("Authors")):
        lines.append(f"AU  - {author}")

    for column, tag in (
        ("Document Title", "TI"),
        ("Publication Title", "T2"),
        ("Publication Year", "PY"),
        ("Volume", "VL"),
        ("Issue", "IS"),
        ("Start Page", "SP"),
        ("End Page", "EP"),
        ("Abstract", "AB"),
        ("DOI", "DO"),
        ("Publisher", "PB"),
        ("PDF Link", "UR"),
    ):
        value = flatten(row.get(column))
        if value:
            lines.append(f"{tag}  - {value}")

    # Author keywords and IEEE Terms are separate columns; stage 0 concatenates
    # every KW line into one semicolon-separated string, so both can be emitted.
    keywords = split_list(row.get("Author Keywords")) + split_list(row.get("IEEE Terms"))
    seen: set[str] = set()
    for keyword in keywords:
        lowered = keyword.lower()
        if lowered not in seen:
            seen.add(lowered)
            lines.append(f"KW  - {keyword}")

    lines.append("ER  - ")
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", required=True, help="IEEE Xplore Results CSV")
    parser.add_argument("--output", default=None,
                        help="RIS path (default: the input path with .ris)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".ris")

    frame = pd.read_csv(input_path)
    if "Document Title" not in frame.columns:
        raise SystemExit(
            f"{input_path} does not look like an IEEE Results export "
            f"(no 'Document Title' column). Columns: {list(frame.columns)[:5]}"
        )

    lines: list[str] = []
    for _, row in frame.iterrows():
        lines.extend(record_lines(row))

    output_path.write_text("\n".join(lines), encoding="utf-8")

    abstracts = int(frame["Abstract"].notna().sum()) if "Abstract" in frame else 0
    dois = int(frame["DOI"].notna().sum()) if "DOI" in frame else 0
    unmapped = sorted(
        identifier for identifier in frame.get("Document Identifier", pd.Series(dtype=str)).dropna().unique()
        if ris_type(flatten(identifier)) == "GEN"
    )

    print(f"{input_path.name} -> {output_path.name}")
    print(f"  records   {len(frame)}")
    print(f"  abstracts {abstracts}")
    print(f"  DOIs      {dois}")
    if unmapped:
        print(f"  UNMAPPED document types (written as GEN): {unmapped}")


if __name__ == "__main__":
    main()
