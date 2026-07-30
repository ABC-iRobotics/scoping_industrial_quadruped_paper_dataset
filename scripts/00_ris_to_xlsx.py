"""
Stage 0 - convert the raw RIS exports into a single spreadsheet.

WHAT IT DOES
    Parses every *.ris file in the input directory and flattens the records into
    one table, assigning a running record number N and recording which export
    file each record came from.

INPUTS
    input/ris/*.ris   RIS exports from Scopus and IEEE Xplore (and any records
                      exported manually from a reference manager). Not included
                      in this repository: the source database exports are
                      subject to the providers' terms of use and are not
                      redistributable. See README.md, "Reproducing the pipeline".

OUTPUTS
    work/01_converted_papers.xlsx

PAPER REFERENCE
    Section II-A (Search Strategy) and the "Records identified" box of the
    PRISMA-ScR flow diagram in Fig. 1.

NOTE ON RECORD COUNTS
    Run on the original exports this stage yields 1590 records (Scopus 972,
    IEEE Xplore 617, plus 1 record exported manually from a reference manager).
    The paper reports 1591. See README.md, "Known discrepancies".

NOTE ON THE Fulltext COLUMN
    The original working script also generated a `Fulltext` column containing
    sci-hub URLs built from each DOI. That column is not part of the published
    dataset and the URL construction has been removed from this release: the
    published record now carries an empty placeholder instead. This changes no
    published result. See README.md, "Differences from the working scripts".
"""

from __future__ import annotations

import argparse
import glob
import os

import xlsxwriter

from _common import RELEASE_ROOT, WORK_DIR

# Column order of the output sheet, and the column widths used for readability.
FIELDS = [
    "N", "Source", "Author", "Year", "Journal", "Type",
    "Title", "Keywords", "Abstract", "Reference", "Doi", "Fulltext",
]
COL_WIDTHS = [5, 20, 15, 5, 20, 15, 50, 20, 50, 20, 8, 5]


def tag_value(line: str) -> str:
    """Return the value part of an RIS `TAG  - value` line."""
    return line[line.find("-") + 1:].strip() if "-" in line else line.strip()


def parse_ris_file(path: str, records: list, counter: int) -> int:
    """
    Parse one RIS file, appending records to `records`.

    Returns the updated running counter. Multi-line Title and Abstract fields
    are joined; the first author only is kept; keywords are collected into a
    semicolon-separated list; the first DOI wins.
    """
    source = os.path.splitext(os.path.basename(path))[0]

    with open(path, "r", encoding="utf-8-sig") as handle:
        lines = handle.readlines()

    record: dict = {}
    author_seen = 0
    keywords: list[str] = []
    dois: list[str] = []
    in_title = 0
    in_abstract = 0
    title_text = ""
    abstract_text = ""

    for line in lines:
        # TY starts a new record.
        if line.startswith("TY  -") or line.startswith("TY -"):
            record = {"N": counter, "Source": source, "Type": tag_value(line)}
            records.append(record)
            counter += 1
            author_seen = 1
            keywords = []
            dois = []

        if not record:
            continue

        # First author only.
        if (line.startswith("AU  -") or line.startswith("AU -")) and author_seen == 1:
            record["Author"] = tag_value(line).replace(",", " ").replace(".", "")
            author_seen += 1

        elif line.startswith("PY  -") or line.startswith("PY -"):
            record["Year"] = tag_value(line)[:4]

        # Title, with continuation lines.
        elif line.startswith("TI  -") or line.startswith("TI -"):
            in_title = 1
            cleaned = tag_value(line)
            if cleaned.endswith("."):
                cleaned = cleaned[:-1]
            title_text = cleaned
            record["Title"] = title_text

        elif line.startswith("      ") and in_title != 0:
            cleaned = line.strip()
            if cleaned.endswith("."):
                cleaned = cleaned[:-1]
            title_text += " " + cleaned
            record["Title"] = title_text
        else:
            in_title = 0

        if line.startswith("T2  -") or line.startswith("T2 -") or line.startswith("JO  -"):
            record["Journal"] = tag_value(line).title()

        if line.startswith("PT  -") or line.startswith("PT -"):
            record["Type"] = tag_value(line)

        # Abstract, with continuation lines.
        if line.startswith("AB  -") or line.startswith("AB -"):
            in_abstract = 1
            cleaned = tag_value(line)
            if cleaned.endswith("."):
                cleaned = cleaned[:-1]
            abstract_text = cleaned
            record["Abstract"] = abstract_text
        elif line.startswith("      ") and in_abstract != 0:
            cleaned = line.strip()
            if cleaned.endswith("."):
                cleaned = cleaned[:-1]
            abstract_text += " " + cleaned
            record["Abstract"] = abstract_text
        else:
            in_abstract = 0

        if line.startswith("KW  -") or line.startswith("MH  -") or line.startswith("KW -"):
            keywords.append(tag_value(line).replace("*", ""))
            record["Keywords"] = "; ".join(keywords)

        if line.startswith("DO  -") or line.startswith("DO -"):
            dois.append(tag_value(line))

        # Reference string. PubMed-style exports carry a ready-made SO field;
        # Scopus and IEEE Xplore instead provide volume/issue/page fragments
        # that are reassembled after parsing.
        if line.startswith("SO  -") or line.startswith("SO -"):
            cleaned = tag_value(line)
            idx = cleaned.find("10.")
            record["Reference"] = cleaned[:idx].strip() if idx != -1 else cleaned

        for tag in ("VL", "IS", "SP", "EP"):
            if line.startswith(f"{tag}  -") or line.startswith(f"{tag} -"):
                record[tag] = tag_value(line)

        # The published dataset does not carry a full-text link; see module docstring.
        record["Doi"] = dois[0] if dois else "na"
        record["Fulltext"] = "na"

    return counter


def assemble_missing_references(records: list) -> None:
    """Build a Reference string from volume/issue/page parts when SO was absent."""
    for record in records:
        if record.get("Reference", "na") != "na":
            continue
        parts = []
        if "VL" in record:
            parts.append(f"Vol. {record['VL']}")
        if "IS" in record:
            parts.append(f"Iss. {record['IS']}")
        if "SP" in record:
            pages = f"pp. {record['SP']}"
            if "EP" in record and record["EP"] != record["SP"]:
                pages += f"-{record['EP']}"
            parts.append(pages)
        if parts:
            record["Reference"] = ", ".join(parts)


def write_xlsx(records: list, output_path) -> None:
    """Write the parsed records to a formatted xlsx sheet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with xlsxwriter.Workbook(str(output_path)) as workbook:
        sheet = workbook.add_worksheet("Records")
        bold = workbook.add_format({"bold": True})
        sheet.write_row("A1", FIELDS, bold)

        for index, width in enumerate(COL_WIDTHS):
            sheet.set_column(index, index, width)

        for row_index, record in enumerate(records):
            for field_index, field in enumerate(FIELDS):
                cell = str(record.get(field, "na"))
                if cell.isnumeric():
                    sheet.write(row_index + 1, field_index, int(cell))
                else:
                    sheet.write(row_index + 1, field_index, cell)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "--input-dir",
        default=str(RELEASE_ROOT / "input" / "ris"),
        help="directory containing the *.ris exports (default: input/ris)",
    )
    parser.add_argument(
        "--output",
        default=str(WORK_DIR / "01_converted_papers.xlsx"),
        help="output spreadsheet (default: work/01_converted_papers.xlsx)",
    )
    args = parser.parse_args()

    from pathlib import Path

    ris_files = sorted(glob.glob(os.path.join(args.input_dir, "*.ris")))
    if not ris_files:
        raise SystemExit(
            f"ERROR: no .ris files found in {args.input_dir}\n"
            "The source database exports are not redistributable and are not\n"
            "included in this repository. See README.md, 'Reproducing the pipeline'."
        )

    records: list = []
    counter = 1
    for path in ris_files:
        before = counter
        counter = parse_ris_file(path, records, counter)
        print(f"  {counter - before:5d} records  {os.path.basename(path)}")

    assemble_missing_references(records)

    output_path = Path(args.output)
    write_xlsx(records, output_path)

    print(f"\nParsed {len(records)} records from {len(ris_files)} file(s).")
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
