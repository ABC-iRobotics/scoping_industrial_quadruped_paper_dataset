"""
Stage 20 - merge the round-2 search into the round-1 baseline.

WHAT IT DOES
    Builds the versioned charting table the Sensors paper analyses, from two
    inputs that are never edited:

      round-1 baseline   88 studies, already screened and charted
      round-2 records    deduplicated output of stage 1, this search round

    The baseline is IMMUTABLE. Its 88 studies keep their existing charting and
    are not re-screened. This stage only decides which round-2 records are new.

THE SECOND DEDUPLICATION
    Stage 1 removes duplicates *within* a pooled set. It has no concept of a
    baseline, so a study found in round 1 and found again in round 2 survives
    it. That second pass is here, and its count is a separate box in the
    PRISMA-ScR flow diagram - the two numbers must not be added together or
    reported as one.

    Matching is on normalised DOI first, then on normalised title. A DOI match
    is decisive. A title-only match is reported separately so it can be
    eyeballed: preprint, conference and journal versions of one work are the
    usual failure case in this literature, and they are exactly the pairs where
    an automatic match is least trustworthy.

PROVENANCE COLUMNS
    The baseline carries none of these, and without them the PRISMA-ScR counts
    cannot be reconstructed later:

      record_id      stable identifier, r1-#### or r2-####
      search_round   1 = pre-existing baseline, 2 = this search round
      db_source      which databases returned the record, semicolon separated;
                     a record can come from more than one
      charted_round  which round charted the analytical variables
      charted_by     how they were charted

    A record found in BOTH rounds keeps search_round 1 - it is not a new study -
    but its db_source gains the round-2 databases, because that is a fact about
    where it can be found, not about when it entered the corpus.

WHAT THIS STAGE DOES NOT DO
    It does not screen the new records, and it does not extract any analytical
    variable. Both wait on the OSF protocol registration (CLAUDE.md 3.5). New
    rows therefore arrive with their charting columns empty, which is the
    honest state of the corpus, not an omission.

INPUTS
    data/full_text_screening_results.xlsx    the 88-study baseline (read-only)
    work/r2_02_deduplicated.xlsx             stage 1 output for round 2

OUTPUTS
    work/charting_v2.xlsx                    the merged table
    work/charting_v2_prisma.md               the counts the flow diagram needs
    work/charting_v2_title_matches.csv       title-only matches, for eyeballing

USAGE
    python scripts/20_merge_corpus.py
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from _common import WORK_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = PROJECT_ROOT / "data" / "full_text_screening_results.xlsx"
DEFAULT_ROUND2 = WORK_DIR / "r2_02_deduplicated.xlsx"

PROVENANCE = ["record_id", "search_round", "db_source", "charted_round", "charted_by"]

DOI_PREFIX = re.compile(r"^\s*(https?://(dx\.)?doi\.org/|doi:)\s*", re.I)
NON_ALNUM = re.compile(r"[^a-z0-9]+")


def norm_doi(value) -> str:
    """Normalise a DOI for matching. Empty string when absent or a placeholder."""
    text = str(value or "").strip()
    if not text or text.lower() in {"na", "nan", "none", "-"}:
        return ""
    return DOI_PREFIX.sub("", text).strip().lower().rstrip(".")


def norm_title(value) -> str:
    """Normalise a title: lowercase, drop everything that is not alphanumeric."""
    text = str(value or "").strip().lower()
    if not text or text in {"na", "nan", "none"}:
        return ""
    return NON_ALNUM.sub(" ", text).strip()


def database_of(source: str) -> str:
    """
    Name the database a record came from, from its export filename.

    The baseline stores raw export filenames in `Source`
    ("IEEE Xplore Citation RIS Download 2026.5.21...", "scopus_export_May..."),
    and round 2 stores the filename stem this pipeline chose. Both reduce to a
    database name, which is what the PRISMA-ScR flow reports.
    """
    lowered = str(source or "").lower()
    if "ieee" in lowered:
        return "IEEE Xplore"
    if "scopus" in lowered:
        return "Scopus"
    if "wos" in lowered or "web of science" in lowered or "savedrecs" in lowered:
        return "Web of Science"
    return str(source or "unknown").strip() or "unknown"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--round2", default=str(DEFAULT_ROUND2))
    parser.add_argument("--round2-raw", default=str(WORK_DIR / "r2_01_converted.xlsx"),
                        help="stage 0 output, before deduplication. The PRISMA-ScR "
                             "'records identified' box reports RAW per-database counts; "
                             "post-dedup attribution understates every database whose "
                             "records happened to be deduplicated against another's.")
    parser.add_argument("--output", default=str(WORK_DIR / "charting_v2.xlsx"))
    args = parser.parse_args()

    baseline_path, round2_path = Path(args.baseline), Path(args.round2)
    for path in (baseline_path, round2_path):
        if not path.exists():
            raise SystemExit(f"ERROR: input not found: {path}")

    baseline = pd.read_excel(baseline_path)
    round2 = pd.read_excel(round2_path)
    print(f"baseline  {len(baseline):>5} rows x {len(baseline.columns)} cols  {baseline_path.name}")
    print(f"round 2   {len(round2):>5} rows x {len(round2.columns)} cols  {round2_path.name}\n")

    # ---- index the baseline for matching
    base_dois: dict[str, int] = {}
    base_titles: dict[str, int] = {}
    for index, row in baseline.iterrows():
        doi = norm_doi(row.get("Doi"))
        title = norm_title(row.get("Title"))
        if doi:
            base_dois.setdefault(doi, index)
        if title:
            base_titles.setdefault(title, index)

    # ---- classify every round-2 record
    already = {"doi": 0, "title": 0}
    title_only_matches = []
    extra_sources: dict[int, set[str]] = {}
    new_rows = []

    for _, row in round2.iterrows():
        database = database_of(row.get("Source"))
        doi, title = norm_doi(row.get("Doi")), norm_title(row.get("Title"))

        hit = base_dois.get(doi) if doi else None
        matched_on = "doi" if hit is not None else None
        if hit is None and title:
            hit = base_titles.get(title)
            matched_on = "title" if hit is not None else None

        if hit is not None:
            already[matched_on] += 1
            extra_sources.setdefault(hit, set()).add(database)
            if matched_on == "title":
                title_only_matches.append({
                    "baseline_row": hit,
                    "baseline_title": baseline.at[hit, "Title"],
                    "baseline_doi": baseline.at[hit, "Doi"],
                    "round2_title": row.get("Title"),
                    "round2_doi": row.get("Doi"),
                    "round2_year": row.get("Year"),
                    "round2_database": database,
                })
            continue

        record = {column: row.get(column) for column in round2.columns if column != "N"}
        record["db_source"] = database
        new_rows.append(record)

    # ---- assemble
    merged = baseline.copy()
    merged.insert(0, "record_id", [f"r1-{i + 1:04d}" for i in range(len(merged))])
    merged.insert(1, "search_round", 1)
    merged.insert(2, "db_source", [
        "; ".join(sorted({database_of(source)} | extra_sources.get(index, set())))
        for index, source in enumerate(merged.get("Source", pd.Series([""] * len(merged))))
    ])
    merged.insert(3, "charted_round", 1)
    merged.insert(4, "charted_by", "round-1 LLM extraction, human-verified on the SISY variables only")

    new_frame = pd.DataFrame(new_rows)
    if not new_frame.empty:
        new_frame.insert(0, "record_id", [f"r2-{i + 1:04d}" for i in range(len(new_frame))])
        new_frame.insert(1, "search_round", 2)
        new_frame.insert(3, "charted_round", pd.NA)
        new_frame.insert(4, "charted_by", pd.NA)
        # Every analytical column the baseline carries exists here too, empty:
        # a missing column and an uncharted study are different things, and the
        # analysis scripts must be able to tell them apart.
        for column in baseline.columns:
            if column not in new_frame.columns:
                new_frame[column] = pd.NA

    out = pd.concat([merged, new_frame], ignore_index=True)
    ordered = PROVENANCE + [c for c in out.columns if c not in PROVENANCE]
    out = out[ordered]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_excel(output_path, index=False)

    # Screening input: the new records only, in the column shape stage 2 expects.
    # The 88 baseline studies are already included and are NOT re-screened.
    if not new_frame.empty:
        screen_columns = ["record_id"] + [c for c in round2.columns if c != "N"]
        screening = new_frame[[c for c in screen_columns if c in new_frame.columns]].copy()
        screening.insert(1, "N", range(1, len(screening) + 1))
        screening_path = output_path.with_name("r2_03_to_screen.xlsx")
        screening.to_excel(screening_path, index=False)
        print(f"screening input            {len(screening)} rows -> {screening_path.name}")

    matches_path = output_path.with_name(output_path.stem + "_title_matches.csv")
    pd.DataFrame(title_only_matches).to_csv(matches_path, index=False, encoding="utf-8")

    # ---- baseline recovery: does the reconstructed search find round 1 again?
    #
    # The round-2 query is a RECONSTRUCTION, assembled from the Boolean blocks the
    # prior paper prints in prose. Nothing guarantees it matches what was actually
    # run. But it covers the same databases over a longer window, so every baseline
    # study SHOULD come back. One that does not means either a narrower query or a
    # genuine indexing change - and either way it is worth knowing before the corpus
    # is frozen rather than after a reviewer asks.
    recovery = pd.DataFrame([
        {"database": database_of(row.get("Source")), "refound": index in extra_sources}
        for index, row in baseline.iterrows()
    ])
    by_database = recovery.groupby("database")["refound"].agg(["sum", "count"])

    # ---- the PRISMA-ScR numbers
    per_database = {}
    for _, row in round2.iterrows():
        database = database_of(row.get("Source"))
        per_database[database] = per_database.get(database, 0) + 1

    lines = [
        "# PRISMA-ScR counts - merged corpus (regenerate, never transcribe)",
        "",
        "## Round 2, this search round",
        "",
        "| Quantity | n |",
        "|---|---:|",
    ]
    # The "records identified" box takes RAW per-database counts. Post-dedup
    # attribution credits a shared record to whichever export was read first, so
    # it understates every database that overlaps another - Web of Science reads
    # as 24 rather than 346 purely because Scopus and IEEE were parsed before it.
    raw_per_database: dict[str, int] = {}
    raw_total = 0
    raw_path = Path(args.round2_raw)
    if raw_path.exists():
        raw = pd.read_excel(raw_path)
        raw_total = len(raw)
        for _, row in raw.iterrows():
            name = database_of(row.get("Source"))
            raw_per_database[name] = raw_per_database.get(name, 0) + 1

    for database, count in sorted(raw_per_database.items()):
        lines.append(f"| **Records identified**, {database} | {count} |")
    if raw_total:
        lines.append(f"| **Records identified**, all three databases | {raw_total} |")
        lines.append(f"| Duplicate records removed within round 2 | {raw_total - len(round2)} |")
    lines += [
        f"| Round-2 records after within-round dedup, total | {len(round2)} |",
        f"| Already in the round-1 baseline, matched on DOI | {already['doi']} |",
        f"| Already in the round-1 baseline, matched on title only | {already['title']} |",
        f"| **New records to screen** | **{len(new_frame)}** |",
        "",
        "## Merged corpus",
        "",
        "| Quantity | n |",
        "|---|---:|",
        f"| Round-1 baseline, included studies | {len(baseline)} |",
        f"| Round-2 new records, not yet screened | {len(new_frame)} |",
        f"| Rows in the merged table | {len(out)} |",
        "",
        "The two deduplication counts are separate boxes in the flow diagram: one",
        "within round 2 across databases, one against the baseline. Do not add them.",
        "",
        f"Title-only matches ({already['title']}) are listed in",
        f"`{matches_path.name}` and need eyeballing before they are trusted.",
        "",
        "## Baseline recovery - does the reconstructed search find round 1 again?",
        "",
        "| Original database | Re-found | Baseline studies |",
        "|---|---:|---:|",
    ]
    for database, row in by_database.iterrows():
        lines.append(f"| {database} | {int(row['sum'])} | {int(row['count'])} |")
    lines += [
        f"| **Total** | **{int(by_database['sum'].sum())}** | **{int(by_database['count'].sum())}** |",
        "",
        "Every baseline study should come back: the round-2 query covers the same",
        "databases over a longer window. A database whose studies do not return has a",
        "query narrower than the one round 1 actually ran. Until every database has",
        "been searched, a shortfall in a not-yet-searched one is expected and means",
        "nothing.",
    ]
    prisma_path = output_path.with_name(output_path.stem + "_prisma.md")
    prisma_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"round-2 records            {len(round2)}")
    for database, count in sorted(per_database.items()):
        print(f"    {database:<16} {count}")
    print(f"already in baseline (DOI)   {already['doi']}")
    print(f"already in baseline (title) {already['title']}")
    print(f"NEW records to screen       {len(new_frame)}")
    print(f"\nmerged rows                 {len(out)}  ({len(baseline)} baseline + {len(new_frame)} new)")
    print("\nbaseline recovery by original database:")
    for database, row in by_database.iterrows():
        flag = "" if row["sum"] == row["count"] else "   <-- shortfall"
        print(f"    {database:<16} {int(row['sum']):>3}/{int(row['count']):<3}{flag}")

    print(f"\nWritten: {output_path}")
    print(f"         {prisma_path}")
    print(f"         {matches_path}")


if __name__ == "__main__":
    main()
