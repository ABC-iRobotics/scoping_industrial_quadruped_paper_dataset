# Data dictionary

File: `SISY2026_ScopingIndustrialQuadruped.xlsx`
Rows: 88 (one per included study)
Columns: 18

This dataset is a deliberate subset of the full extraction. See
[Scope of the published dataset](../README.md#scope-of-the-published-dataset).

## Columns

| # | Column | Type | Description |
|---|---|---|---|
| 1 | `Pdf name` | string | Internal identifier of the study (`paper001` … `paper088`). Corresponds to the local PDF filename. The PDFs themselves are not redistributed. |
| 2 | `N` | integer | Record number carried over from the deduplicated search results. Not contiguous, because it refers to the position in the 1371-record screened set. |
| 3 | `Source` | categorical | Source database the record was retrieved from: `Scopus` or `IEEE Xplore`. |
| 4 | `Author` | string | First author only, surname and initials, as exported in the RIS record. |
| 5 | `Year` | integer | Publication year. |
| 6 | `Journal` | string | Journal or conference proceedings name, title-cased as exported. |
| 7 | `Type` | categorical | RIS publication type (`JOUR`, `CONF`). |
| 8 | `Title` | string | Article title. |
| 9 | `Keywords` | string | Author and index keywords, semicolon-separated, as supplied by the source database. |
| 10 | `Reference` | string | Volume / issue / page fragment, e.g. `Vol. 24, Iss. 10, pp. 16935-16942`. |
| 11 | `Doi` | string | DOI, or `na` when the source record carried none. |
| 12 | `Decision (gpt-oss:120b)` | categorical | **Second-round** LLM title/abstract screening decision: `Include`, `Exclude`, `Maybe`. See the note below. |
| 13 | `Final decision` | categorical | Final human inclusion decision. `Include` for every row, since the file contains only included studies. |
| 14 | `Robot platform` | string | Quadruped platform as reported in the paper, free text. Consolidated into five groups for Fig. 3 by `scripts/04_analysis_and_figures.py`. |
| 15 | `Industry sector` | string | Industrial sector, free text. Consolidated into eight sectors for Fig. 2 and Fig. 4 via `sector_mapping.csv`. |
| 16 | `High-level goal` | string | Primary objective of the system, free text. Consolidated into five use case categories via `usecase_mapping.csv`. |
| 17 | `Real-world validation?` | categorical | `Yes` / `No`. Whether the fully integrated system was demonstrated end-to-end in its actual target environment. Section II-C explains why this binary was set at a higher bar than eligibility itself. |
| 18 | `Open source?` | string | `No`, or `Yes` followed by the repository URL. Coded positive only when the study provided publicly accessible source code, software packages, or equivalent implementation artifacts. |

## Note on column 12

The column is named `Decision (gpt-oss:120b)` but holds the decision from the
**second** screening round, not the first. The first round produced a `Y`/`N`/`U`
letter and is not published. This naming is inherited from the original working
files and is preserved so that the published file matches the one already
referenced by the paper.

## Values that were normalised

The raw extraction contained case and whitespace variants of the same value,
introduced during manual data entry. `scripts/05_build_public_dataset.py`
collapses them, keeping the most frequent spelling in each group:

| Column | Merged |
|---|---|
| `Source` | trailing whitespace stripped (`Scopus ` → `Scopus`); export filenames mapped to database names |
| `Industry sector` | `Chemical industry` → `Chemical Industry`; `Oil & Gas` → `Oil & gas` |
| `Robot platform` | `Boston Dynamics SPOT` → `Boston Dynamics Spot`; `Unitree GO1` → `Unitree Go1`; `Unspecified quadruped robot` → `unspecified quadruped robot` |
| `High-level goal` | `Autonomous exploration ` → `Autonomous exploration` |

No semantic grouping happens at this stage — only variants that are identical
apart from case and whitespace are merged. The semantic consolidation into
sectors and use cases is separate, explicit, and reviewable in
`sector_mapping.csv` and `usecase_mapping.csv`.

## Columns withheld from publication

Sixteen columns of the full extraction are not published. Fifteen are reserved
for follow-up work and are not reported anywhere in the paper:

`Fulltext`, `Decision round 1 (gpt-oss:120b)`, `Onboard Computer`,
`Optical Sensors`, `AI / ML solutions for vision qualities?`, `SLAM/mapping?`,
`Autonomous navigation?`, `Obstacle Avoidance`, `Object detection?`,
`Instrument reading?`, `Target tracking?`, `Environmental challenges?`,
`Reproducable?`, `Success metric for goal task?`, `Reason`

The sixteenth, `Abstract`, is withheld for a different reason — it is the
publishers' copyrighted material. See
[Why the abstracts are not included](../README.md#why-the-abstracts-are-not-included).
