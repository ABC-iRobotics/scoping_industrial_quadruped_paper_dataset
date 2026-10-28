"""
Stage 21 - resolve records to full-text locations, and separate automatic from manual.

WHY THIS EXISTS
    Retrieving full texts by hand is the single largest block of human time in
    this review, and most of it is not reading - it is looking up a DOI, landing
    on a publisher page, and finding the PDF button. That part is mechanical.

    This stage does the lookup for every record at once and splits the result in
    two: the ones with a legally downloadable open-access PDF, and the ones that
    need a human to click through an institutional subscription. It then writes a
    click-through worklist for the second group, so the human part is one page of
    links rather than several hundred searches.

WHAT IT DOES NOT DO
    It does not mass-download from publisher sites. Bulk automated retrieval of
    subscription content breaches the terms of use of every major publisher and
    is enforced by rate limiting at the IP level - which here is the university's
    IP, shared by everyone. Getting institutional access suspended mid-review
    would cost far more than the time it saves. Open-access copies are fetched;
    subscription copies are listed for a human to open.

    It is also deliberately run AFTER title/abstract screening. Resolving every
    identified record wastes effort on the ~85% that screening excludes, and
    round 1's numbers say so directly: 1,371 records screened, 149 full texts
    sought.

SOURCES
    OpenAlex (api.openalex.org)   open-access status and best OA PDF location.
                                  Free, no key, no registration. Queried in
                                  batches of 50 DOIs.
    The IEEE export's `PDF Link`  already present for IEEE records, and valid
                                  under the institutional subscription.

    No email address is sent to either service. OpenAlex's "polite pool" invites
    a mailto parameter and runs fine without one; a personal address is not this
    script's to hand out.

INPUTS
    A table with `Doi` and `Title` columns - typically the post-screening
    include list, optionally `record_id` and `PDF Link`.

OUTPUTS
    work/fulltext_worklist.csv    every record: OA status, resolved URL, source
    work/fulltext_manual.html     the click-through list for the manual remainder

USAGE
    python scripts/21_resolve_fulltext.py --input work/charting_v2.xlsx
    python scripts/21_resolve_fulltext.py --input work/charting_v2.xlsx --round 2
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from _common import WORK_DIR

OPENALEX = "https://api.openalex.org/works"
BATCH = 50
SELECT = "doi,open_access,best_oa_location,primary_location,title,publication_year,type"

DOI_PREFIX = re.compile(r"^\s*(https?://(dx\.)?doi\.org/|doi:)\s*", re.I)


def norm_doi(value) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"na", "nan", "none", "-"}:
        return ""
    return DOI_PREFIX.sub("", text).strip().lower().rstrip(".")


def fetch_batch(dois: list[str], timeout: int = 60) -> dict[str, dict]:
    """Look up a batch of DOIs in OpenAlex. Returns {normalised doi: work}."""
    if not dois:
        return {}
    query = urllib.parse.urlencode({
        "filter": "doi:" + "|".join(dois),
        "per-page": str(len(dois)),
        "select": SELECT,
    })
    request = urllib.request.Request(
        f"{OPENALEX}?{query}",
        headers={"User-Agent": "scoping-review-fulltext-resolver"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    found = {}
    for work in payload.get("results", []):
        doi = norm_doi(work.get("doi"))
        if doi:
            found[doi] = work
    return found


def resolve(work: dict | None, ieee_link: str) -> tuple[str, str, str]:
    """
    Return (oa_status, url, link_source), best link first.

    Preference order, and the order matters for how much human time this costs:

      1. an open-access PDF          one fetch, no human, no subscription
      2. IEEE's own PDF link         one click under the subscription
      3. an open-access landing page one click, PDF is on the page
      4. the publisher landing page  one click, then hunt for the PDF button

    IEEE's direct link outranks a generic publisher landing page even though
    both need a human, because it lands on the file rather than on a page the
    human then has to search. Roughly four in five records here are IEEE, so
    getting this order wrong turns one click into three, several hundred times.
    """
    access = (work or {}).get("open_access") or {}
    status = str(access.get("oa_status") or "unknown")

    if work:
        best = work.get("best_oa_location") or {}
        if best.get("pdf_url"):
            return status, best["pdf_url"], "openalex-oa-pdf"

    if ieee_link:
        return status, ieee_link, "ieee-pdf-link"

    if work:
        best = work.get("best_oa_location") or {}
        landing = best.get("landing_page_url") or access.get("oa_url") or ""
        if landing:
            return status, landing, "openalex-oa-landing"
        primary = work.get("primary_location") or {}
        if primary.get("landing_page_url"):
            return status, primary["landing_page_url"], "openalex-publisher"

    return status, "", ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", default=str(WORK_DIR / "charting_v2.xlsx"))
    parser.add_argument("--round", type=int, default=None,
                        help="restrict to one search_round (e.g. 2)")
    parser.add_argument("--limit", type=int, default=0, help="process at most N records")
    parser.add_argument("--ieee-csv", default=str(WORK_DIR / "round2_ris" / "ieee_xplore_2026-09-03.csv"),
                        help="IEEE Results export, joined by DOI for its PDF Link column "
                             "(stage 0 does not carry that field through)")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--output", default=str(WORK_DIR / "fulltext_worklist.csv"))
    args = parser.parse_args()

    frame = pd.read_excel(args.input)
    if args.round is not None and "search_round" in frame.columns:
        frame = frame[frame["search_round"] == args.round]
    if args.limit:
        frame = frame.head(args.limit)
    print(f"{len(frame)} record(s) from {Path(args.input).name}\n")

    # Stage 0 reads only the RIS tags it needs, so IEEE's `PDF Link` does not
    # survive into the merged table. Join it back by DOI when the export is there.
    ieee_links: dict[str, str] = {}
    ieee_path = Path(args.ieee_csv) if args.ieee_csv else None
    if ieee_path and ieee_path.exists():
        ieee = pd.read_csv(ieee_path)
        for _, row in ieee.iterrows():
            doi, link = norm_doi(row.get("DOI")), str(row.get("PDF Link") or "").strip()
            if doi and link:
                ieee_links[doi] = link
        print(f"IEEE PDF links available for {len(ieee_links)} DOIs\n")

    records = []
    for _, row in frame.iterrows():
        doi = norm_doi(row.get("Doi"))
        records.append({
            "record_id": row.get("record_id", ""),
            "title": str(row.get("Title") or "").strip(),
            "year": row.get("Year", ""),
            "doi": doi,
            "ieee_link": str(row.get("PDF Link") or "").strip() or ieee_links.get(doi, ""),
        })

    with_doi = [r for r in records if r["doi"]]
    print(f"with a DOI: {len(with_doi)}   without: {len(records) - len(with_doi)}")

    works: dict[str, dict] = {}
    unique = sorted({r["doi"] for r in with_doi})
    for start in range(0, len(unique), BATCH):
        chunk = unique[start:start + BATCH]
        try:
            works.update(fetch_batch(chunk))
        except Exception as exc:  # noqa: BLE001
            print(f"  batch {start // BATCH + 1}: FAILED {type(exc).__name__}: {exc}")
        else:
            print(f"  batch {start // BATCH + 1}/{(len(unique) + BATCH - 1) // BATCH}: "
                  f"{len(works)} resolved so far")
        time.sleep(args.delay)

    for record in records:
        status, url, source = resolve(works.get(record["doi"]), record["ieee_link"])
        record["oa_status"] = status
        record["url"] = url
        record["link_source"] = source
        # Automatic only when there is a direct PDF that is genuinely open access.
        record["automatic"] = source == "openalex-oa-pdf"

    out = pd.DataFrame(records)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False, encoding="utf-8")

    manual = out[~out["automatic"]]
    rows = []
    for _, record in manual.iterrows():
        title = html.escape(str(record["title"])[:200])
        url = str(record["url"])
        doi = html.escape(str(record["doi"]))
        link = (f'<a href="{html.escape(url)}" target="_blank" rel="noopener">open</a>'
                if url else
                (f'<a href="https://doi.org/{doi}" target="_blank" rel="noopener">doi.org</a>'
                 if doi else "&mdash;"))
        rows.append(
            f"<tr><td>{html.escape(str(record['record_id']))}</td>"
            f"<td>{title}</td><td>{html.escape(str(record['oa_status']))}</td>"
            f"<td>{link}</td></tr>"
        )

    manual_path = output_path.with_name(output_path.stem + "_manual.html")
    manual_path.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>Full texts to retrieve by hand</title>"
        "<style>body{font:14px/1.5 system-ui;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;width:100%}"
        "td,th{border-bottom:1px solid #ddd;padding:.4rem;vertical-align:top}"
        "td:first-child{white-space:nowrap;font-family:monospace}</style>"
        f"<h1>Full texts to retrieve by hand ({len(manual)})</h1>"
        "<p>Open each in a tab, save the PDF into the corpus folder, and name it "
        "by its record id. Links resolve through the institutional subscription.</p>"
        "<table><tr><th>id</th><th>title</th><th>OA status</th><th>link</th></tr>"
        + "".join(rows) + "</table>",
        encoding="utf-8",
    )

    print(f"\nOA status:\n{out['oa_status'].value_counts().to_string()}")
    print(f"\nlink source:\n{out['link_source'].value_counts().to_string()}")
    print(f"\ndirectly downloadable (open access PDF): {int(out['automatic'].sum())}"
          f"  of {len(out)}  ({100 * out['automatic'].mean():.1f}%)")
    print(f"needs a human click-through:              {len(manual)}")
    print(f"\nWritten: {output_path}\n         {manual_path}")


if __name__ == "__main__":
    main()
