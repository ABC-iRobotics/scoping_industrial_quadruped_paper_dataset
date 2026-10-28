# Search round 2 — strategy, strings, and what to record

**Common cut-off: 3 September 2026.** One cut-off across all three
databases, one PRISMA-ScR flow. Run all three on the same day.

## Where the strings come from

Round 1 (Scopus + IEEE Xplore) used two conceptual Boolean blocks, quoted
verbatim from the SISY paper, Section II-A:

```
platform block:
  ("quadruped*" OR "four-legged" OR "legged robot*" OR "legged platform*")
  AND NOT ("humanoid*" OR "bipedal" OR "two-legged")

industrial context block:
  ("industry" OR "industrial" OR "industry 4.0" OR "manufacturing" OR
   "factory" OR "factories" OR "warehouse*" OR "plant" OR "plants" OR
   "construction site*" OR "oil and gas" OR "mining" OR "power plant*" OR
   "harsh environment*" OR "production line*" OR "facilities" OR
   "logistics" OR "shop floor" OR "field deployment")
```

The paper reports the *conceptual* blocks. It does **not** report the
field qualifiers (`TITLE-ABS-KEY`, `"All Metadata"`, `TS=`), and the RIS
exports do not carry the query either. The qualifiers below are therefore
a **reconstruction**, not a transcription.

That is acceptable, and it is worth being clear about why: round 2 re-runs
all three databases to a single cut-off, so **round 2 is the search of
record** for this paper. Round 1's exact field configuration matters only
for describing the baseline's provenance, not for the corpus.

The **Concept block is deliberately absent** from the query. Round 1 left
it out to maximise sensitivity and applied it at screening instead. Keep
it out, or the two rounds are not comparable.

## Filters — identical to round 1

- **Publication years 2019 to 3 September 2026.** Round 1 used "2019
  onward" because that is when commercial quadrupeds became relevant to
  real deployments.
- **English only.**
- Document type is **not** filtered in the query. Reviews, abstracts
  without full papers, grey literature, technical reports, patents and
  theses are excluded at screening, as in round 1.

---

## Scopus

Advanced search:

```
TITLE-ABS-KEY ( ( "quadruped*" OR "four-legged" OR "legged robot*"
    OR "legged platform*" )
  AND
  ( "industry" OR "industrial" OR "industry 4.0" OR "manufacturing"
    OR "factory" OR "factories" OR "warehouse*" OR "plant" OR "plants"
    OR "construction site*" OR "oil and gas" OR "mining" OR "power plant*"
    OR "harsh environment*" OR "production line*" OR "facilities"
    OR "logistics" OR "shop floor" OR "field deployment" ) )
AND NOT TITLE-ABS-KEY ( "humanoid*" OR "bipedal" OR "two-legged" )
AND PUBYEAR > 2018
AND LANGUAGE ( english )
```

**Every term stays quoted, exactly as the SISY paper prints it.** This is
not cosmetic. Unquoting the single words lets Scopus apply its own
stemming, which returned **1,782** records against **1,137** for the quoted
form — a 57% inflation that would have flowed straight into the PRISMA
counts. Scopus accepts wildcards inside double quotes; the quoted form is
the reconstruction that matches round 1.

The language limit is expressed as `LANGUAGE ( english )` in the query
rather than as a `LIMIT-TO` refinement, so the whole search is one
copy-pasteable string.

Export: **RIS**, with abstracts. Scopus exports in batches; keep every
file, do not merge them by hand.

## Web of Science

Advanced search, Web of Science Core Collection:

```
TS=(
  ( quadruped* OR "four-legged" OR "legged robot*" OR "legged platform*" )
  AND
  ( industry OR industrial OR "industry 4.0" OR manufacturing OR factory
    OR factories OR warehouse* OR plant OR plants OR "construction site*"
    OR "oil and gas" OR mining OR "power plant*" OR "harsh environment*"
    OR "production line*" OR facilities OR logistics OR "shop floor"
    OR "field deployment" )
)
NOT TS=( humanoid* OR bipedal OR "two-legged" )
```

Then refine: **Publication Years 2019–2026**, **Language: English**.

`TS=` searches title, abstract, author keywords and Keywords Plus. That is
slightly broader than Scopus's `TITLE-ABS-KEY` because of Keywords Plus.
Record that in Methods rather than trying to suppress it — WoS has no
exact equivalent, and the difference is a property of the databases.

Export: **RIS** ("Other File Formats" → RIS), with **Full Record**.

## IEEE Xplore

Command search:

```
(
  ( "All Metadata":quadruped* OR "All Metadata":"four-legged"
    OR "All Metadata":"legged robot*" OR "All Metadata":"legged platform*" )
  AND
  ( "All Metadata":industry OR "All Metadata":industrial
    OR "All Metadata":"industry 4.0" OR "All Metadata":manufacturing
    OR "All Metadata":factory OR "All Metadata":factories
    OR "All Metadata":warehouse* OR "All Metadata":plant
    OR "All Metadata":plants OR "All Metadata":"construction site*"
    OR "All Metadata":"oil and gas" OR "All Metadata":mining
    OR "All Metadata":"power plant*" OR "All Metadata":"harsh environment*"
    OR "All Metadata":"production line*" OR "All Metadata":facilities
    OR "All Metadata":logistics OR "All Metadata":"shop floor"
    OR "All Metadata":"field deployment" )
)
NOT ( "All Metadata":humanoid* OR "All Metadata":bipedal
      OR "All Metadata":"two-legged" )
```

Then filter **Year 2019–2026** in the left-hand panel, or append
`&ranges=2019_2026_Year` to the results URL.

**Keep the wildcards inside the quoted phrases.** IEEE accepts them, and
they matter: dropping them from `"legged robot*"`, `"construction site*"`,
`"power plant*"`, `"harsh environment*"` and `"production line*"` returned
**546** records against **729** with them — below round 1's 617 over a
longer window, which is what exposed the error.

Two IEEE quirks:

- **Term limit.** Xplore allows 25 terms per search clause. This query
  uses 4, 19 and 3, so it passes — but there is little room to add
  synonyms to the context block.
- **Export.** The Citations tab is capped per batch, but the **Results**
  tab of the export dialog downloads the entire result set as a single
  CSV, abstracts included. Prefer that over seven RIS files, and convert
  it to the pipeline's input format.

---

## Where the exports go

```
analysis/work/round2_ris/
```

`analysis/work/` is gitignored. Database exports are subject to the
providers' terms of use and are **not** redistributable — the same reason
the SISY release ships no RIS files. Do not commit them.

Then:

```bash
cd analysis
python scripts/00_ris_to_xlsx.py --input-dir work/round2_ris
```

## Record this at run time — it goes into the OSF entry and Methods

For each of the three databases, write down **before leaving the page**:

| Field | Why |
|---|---|
| The exact string as pasted | The reconstruction above is what we *intend* to run; this is what ran |
| Date and time of execution | The cut-off has to be a fact, not a plan |
| Number of hits | Feeds the PRISMA-ScR "records identified" boxes |
| Field qualifier and any UI filter used | Round 1 could not reconstruct this; do not repeat that |
| Export file names | Ties every record back to its export |

Round 1's figure is unrecoverable in this detail. This is the cheapest
credibility gain available in the whole project, and it costs five
minutes.

## Sanity check before exporting

Round 1 returned **Scopus 972** and **IEEE Xplore 617** records (the paper
prints 973 and 618; the release documents the off-by-one).

Round 2 runs the same query on the same two databases over a **longer**
window, so both counts must come back **at least as high**. If Scopus
returns markedly fewer, the reconstructed syntax differs from what round 1
actually ran — stop and compare before exporting anything.

WoS has no round-1 baseline to compare against. A plausible return is the
same order of magnitude as Scopus, with heavy overlap; a return of a few
dozen or of many thousands both mean the string is wrong.

---

## As executed — 3 September 2026

Run through the browser against the live databases. The reconstructions
above are the **corrected** ones; both corrections were caught by the
round-1 count check, which is the whole reason it is in this document.

| Database | Access | Hits | Round 1 | Export |
|---|---|---:|---:|---|
| IEEE Xplore | institutional IP | **729** | 617 | `ieee_xplore_2026-09-03.csv`, 729 records, 729 abstracts |
| Scopus | signed-in account | **1,137** | 972 | `scopus_2026-09-03.ris`, 1,137 records, 1,137 abstracts |
| Web of Science | institutional IP | **346** | — (new) | `wos_core_2026-09-03.ris`, 346 records, 344 abstracts |

Scopus was exported with citation information, bibliographical information and
abstract & keywords selected, so the records carry volume, issue, pages and
publisher — the fields ACS-style references need and that a Crossref
enrichment pass would otherwise have to recover.

### Scopus returns two different counts for one query

The same string, the same account, the same day:

| Interface | Result |
|---|---:|
| `scopus.com/pages/search/publications` (current) | **1,137** |
| `scopus.com/results/results.uri` (classic) | **1,782** |

The classic endpoint returns exactly what the *unquoted* query returns, so it
appears not to honour quoted terms; the current interface does. Signing in
changes nothing — both counts reproduce anonymously and authenticated.

**The export is from the current interface, and the reported count is 1,137.**
Methods must name the interface alongside the query: "Scopus,
`TITLE-ABS-KEY(...)`" does not by itself reproduce the number, which is not a
property anyone would expect a search string to lack.

Both counts sit plausibly above their round-1 values for a window extended
by roughly three months, in a literature whose output is concentrated in
the last two years.

**Two failed reconstructions, both caught by the count check:**

1. Scopus with unquoted single words → 1,782 hits (+57%). Cause: Scopus
   stems unquoted terms. Fixed by quoting every term as the paper prints
   it.
2. IEEE without wildcards inside quoted phrases → 546 hits, *below* round
   1 over a longer window. Cause: `"power plant"` does not match
   `power plants`. Fixed by restoring the wildcards.

Neither would have been visible without a baseline to compare against. A
search reconstructed from a paper's prose is a hypothesis, not a fact.

**Blockers at the time of writing:**

- **Scopus export requires an account.** The search itself runs
  anonymously, but export returns "To use this feature you must have a
  Scopus account". Institutional sign-in is needed; credentials are the
  author's to enter.
Web of Science and IEEE Xplore both authenticate by institutional IP and
needed no sign-in. **Scopus does not**: the search runs anonymously, but
export returns "To use this feature you must have a Scopus account".
Round 1 clearly had a working route to Scopus, so one exists — a personal
account, or the national/consortial link rather than `scopus.com`
directly. Credentials are the author's to enter.

## The Web of Science query as executed

The year and language limits are inside the query rather than applied as
refinements, so the whole search is one reproducible string:

```
(TS=(("quadruped*" OR "four-legged" OR "legged robot*" OR "legged platform*")
  AND ("industry" OR "industrial" OR "industry 4.0" OR "manufacturing"
    OR "factory" OR "factories" OR "warehouse*" OR "plant" OR "plants"
    OR "construction site*" OR "oil and gas" OR "mining" OR "power plant*"
    OR "harsh environment*" OR "production line*" OR "facilities"
    OR "logistics" OR "shop floor" OR "field deployment"))
 NOT TS=("humanoid*" OR "bipedal" OR "two-legged"))
AND PY=(2019-2026) AND LA=(English)
```

Export: RIS, **Full Record**, records 1–346 in one file. Without the year
and language limits the same query returns 502, so the limits remove 156.

Still to record before the OSF entry is final: the Scopus count under an
authenticated session (it should match the 1,137 seen anonymously), and
the export timestamps.
