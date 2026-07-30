"""
Helper - retrieve abstracts for the published DOIs.

WHY THIS EXISTS
    The published dataset does not carry the Abstract column, because the
    abstracts are the publishers' copyrighted material (see the note in
    05_build_public_dataset.py). The abstracts are nevertheless methodologically
    important: both LLM screening rounds consumed title + abstract, so they are
    the actual input to the screening described in Section II-D of the paper.

    This script reconstructs them locally from open sources, so that a third
    party can rebuild the screening inputs without us redistributing publisher
    text. It queries OpenAlex first and falls back to Semantic Scholar.

WHAT IT DOES
    Reads the DOIs from the published dataset, fetches abstracts, and writes a
    local file alongside a per-row source and a coverage summary. Rows where no
    open source carries the abstract are left empty and reported, rather than
    being silently dropped.

INPUTS
    data/SISY2026_ScopingIndustrialQuadruped.xlsx

OUTPUTS
    work/abstracts_rehydrated.xlsx   Doi, Title, Abstract, Abstract source

COVERAGE
    Coverage is uneven by publisher and changes over time. Measured on a
    stratified sample of quadruped-robotics DOIs in July 2026: IEEE and MDPI
    close to complete in OpenAlex and Semantic Scholar, Elsevier around half,
    Springer poor. Crossref carries almost no abstracts for IEEE and is not
    queried. Because this corpus is drawn from IEEE Xplore and Scopus, most
    records are expected to resolve - but always report the retrieval date and
    the achieved coverage rather than assuming completeness.

LICENSING NOTE
    Abstracts fetched by this script are retrieved by the person running it,
    from sources they access directly. Do not commit the output, and do not
    redistribute it. The Semantic Scholar dataset licence in particular
    prohibits redistribution of the response data. work/ is gitignored.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd
import requests

from _common import DATA_DIR, WORK_DIR, cell_text

OPENALEX_URL = "https://api.openalex.org/works/doi:{doi}"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"

# A contact address makes OpenAlex route the request to its polite pool.
# Replace with your own address when running the script.
POLITE_CONTACT = "your.email@example.org"

JATS_TAG = re.compile(r"<[^>]+>")


def invert_index_to_text(inverted: dict | None) -> str:
    """
    Rebuild plain text from an OpenAlex abstract_inverted_index.

    OpenAlex stores abstracts as {word: [positions]} rather than as running text.
    """
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, indices in inverted.items():
        for index in indices:
            positions.append((index, word))
    return " ".join(word for _, word in sorted(positions))


def fetch_openalex(doi: str, session: requests.Session) -> str:
    try:
        response = session.get(
            OPENALEX_URL.format(doi=doi),
            params={"mailto": POLITE_CONTACT},
            timeout=30,
        )
        if response.status_code != 200:
            return ""
        return invert_index_to_text(response.json().get("abstract_inverted_index"))
    except requests.exceptions.RequestException:
        return ""


def fetch_semantic_scholar(doi: str, session: requests.Session) -> str:
    try:
        response = session.get(
            SEMANTIC_SCHOLAR_URL.format(doi=doi),
            params={"fields": "abstract"},
            timeout=30,
        )
        if response.status_code != 200:
            return ""
        return JATS_TAG.sub("", response.json().get("abstract") or "").strip()
    except requests.exceptions.RequestException:
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", default=str(DATA_DIR / "SISY2026_ScopingIndustrialQuadruped.xlsx"))
    parser.add_argument("--output", default=str(WORK_DIR / "abstracts_rehydrated.xlsx"))
    parser.add_argument("--delay", type=float, default=0.2, help="seconds between requests")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"ERROR: input not found: {input_path}")

    frame = pd.read_excel(input_path)
    session = requests.Session()
    rows = []

    total = len(frame)
    for position, (_, row) in enumerate(frame.iterrows(), start=1):
        doi = cell_text(row.get("Doi"))
        title = cell_text(row.get("Title"))

        if not doi or doi.lower() == "na":
            rows.append({"Doi": doi, "Title": title, "Abstract": "", "Abstract source": "no DOI"})
            print(f"  {position}/{total}  no DOI")
            continue

        abstract = fetch_openalex(doi, session)
        source = "OpenAlex" if abstract else ""

        if not abstract:
            abstract = fetch_semantic_scholar(doi, session)
            source = "Semantic Scholar" if abstract else "not found"

        rows.append(
            {"Doi": doi, "Title": title, "Abstract": abstract, "Abstract source": source}
        )
        print(f"  {position}/{total}  {doi} -> {source}")
        time.sleep(args.delay)

    result = pd.DataFrame(rows)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_excel(output_path, index=False)

    recovered = int((result["Abstract"].str.len() > 0).sum())
    print(f"\nRecovered {recovered} of {total} abstracts ({recovered / total:.1%}).")
    print(result["Abstract source"].value_counts().to_string())
    print(f"\nWritten to: {output_path}")
    print("Do not commit this file - work/ is gitignored, and the retrieved text is not ours to redistribute.")


if __name__ == "__main__":
    main()
