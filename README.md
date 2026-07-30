# Quadruped Robots in Industrial Environments — Scoping Review Dataset

Data and analysis code for the paper:

> P. Zsoldos, Z. Zrubka and P. Galambos, "A Scoping Review of State-of-the-Art
> Industrial Use Cases, Hardware Platforms, and Reproducibility of Quadruped
> Robots," in *Proc. IEEE International Symposium on Intelligent Systems and
> Informatics (SISY)*, 2026.
> DOI: `10.XXXX/XXXXXXX` *(to be filled in once assigned)*

Antal Bejczy Center for Intelligent Robotics, Obuda University, Budapest, Hungary.

This repository contains the three artifacts the paper promises in its Data
Availability section: the extracted dataset, the Python scripts used for
deduplication and analysis, and the LLM prompt templates used during screening
and data extraction.

## What this is

A scoping review of quadruped robots deployed in industrial environments,
conducted according to PRISMA-ScR. 1590 records were retrieved from Scopus and
IEEE Xplore, deduplicated to 1371, screened in two title/abstract rounds, and
narrowed to 88 included studies whose full texts were charted for robot
platform, industry sector, application task, real-world validation and
open-source availability.

The code here is an **LLM-assisted review pipeline**: a large language model was
used as a decision-support tool for screening and for first-pass extraction, and
every decision and extracted variable was then verified by the primary reviewer.
The model was never the final arbiter. If you are looking for a worked example of
that workflow — prompts, resumable batch calls, and the audit trail from raw
search export to published table — that is what this repository is.

It is not a general-purpose library. The scripts are the ones that produced this
particular review, published as-is for transparency. See
[Adapting this to another review](#adapting-this-to-another-review) if you want
to reuse the workflow.

## Repository structure

```
data/
  SISY2026_ScopingIndustrialQuadruped.xlsx   the published dataset (88 studies)
  data_dictionary.md                          column-by-column description
  sector_mapping.csv                          raw sector value -> consolidated sector
  usecase_mapping.csv                         raw goal value  -> use case category
  record_overrides.csv                        per-study category corrections, justified
  LICENSE                                     CC BY 4.0 (applies to data/ only)
prompts/
  abstract_screening_round1.md                first-round title/abstract screening
  abstract_screening_round2.md                second-round title/abstract screening
  data_extraction.md                          full-text structured extraction
  verification_double_check.md                extraction cross-check (see note)
scripts/
  _common.py                                  prompt loading, credentials, LLM client
  00_ris_to_xlsx.py                           RIS exports -> single table
  01_deduplicate.py                           title + DOI deduplication
  02_llm_screening.py                         both title/abstract screening rounds
  03_llm_extraction.py                        full-text data extraction
  04_analysis_and_figures.py                  statistics and Figures 2, 3, 4
  05_build_public_dataset.py                  full extraction -> published subset
  06_rehydrate_abstracts.py                   retrieve abstracts from open sources
LICENSE                                       MIT (applies to code)
requirements.txt
.env.example
```

## Dependencies

Python 3.10 or newer. The original runs used CPython 3.13.5; the scripts have
also been checked against pandas 2.2.3 and 3.0.3, so both major versions work.

```bash
pip install -r requirements.txt
```

| Package | Minimum | Used for |
|---|---|---|
| `pandas` | 2.0 | all tabular work; every stage except `00` |
| `openpyxl` | 3.1 | reading and writing `.xlsx` |
| `XlsxWriter` | 3.1 | writing the formatted sheet in stage `00` |
| `PyMuPDF` | 1.23 | extracting text from the article PDFs in stage `03` (imported as `fitz`) |
| `requests` | 2.31 | HTTP client for the LLM endpoint and the abstract rehydration helper |
| `python-dotenv` | 1.0 | loading `LLM_API_KEY` from a local `.env` |
| `matplotlib` | 3.7 | generating Figures 2, 3 and 4 in stage `04` |

Not every stage needs everything. If you only want to reproduce the published
analysis, `pandas`, `openpyxl` and `matplotlib` are sufficient:

| Script | Requires |
|---|---|
| `00_ris_to_xlsx.py` | `XlsxWriter` |
| `01_deduplicate.py` | `pandas`, `openpyxl` |
| `02_llm_screening.py` | `pandas`, `openpyxl`, `requests`, `python-dotenv` |
| `03_llm_extraction.py` | `pandas`, `openpyxl`, `requests`, `python-dotenv`, `PyMuPDF` |
| `04_analysis_and_figures.py` | `pandas`, `openpyxl`, `matplotlib` |
| `05_build_public_dataset.py` | `pandas`, `openpyxl` |
| `06_rehydrate_abstracts.py` | `pandas`, `openpyxl`, `requests` |

`python-dotenv` is imported defensively: without it the scripts still run and
read `LLM_API_KEY` straight from the environment.

## Reproducing the analysis

The analysis stage runs on the published dataset alone and needs no credentials:

```bash
pip install -r requirements.txt
python scripts/04_analysis_and_figures.py
```

This prints every headline statistic in Section III and writes the figures to
`figures/`.

## Reproducing the pipeline

The upstream stages cannot be run from this repository alone, and we would
rather say so plainly than imply otherwise:

- **The source database exports are not included.** The Scopus and IEEE Xplore
  RIS files are subject to the providers' terms of use. Section II-A gives the
  full search strings so the search can be repeated.
- **The PDF corpus is not included.** The full texts are copyrighted.
- **The LLM stages are not deterministic.** No random seed was set, and the
  endpoint does not expose one. Re-running the screening will produce broadly
  similar but not identical decisions. The published dataset is the record of
  what the model actually returned.
- **Two steps were manual.** See below.

To run the LLM stages you need an API key:

```bash
cp .env.example .env      # then fill in LLM_API_KEY
python scripts/00_ris_to_xlsx.py --input-dir input/ris
python scripts/01_deduplicate.py
python scripts/02_llm_screening.py
python scripts/03_llm_extraction.py
python scripts/05_build_public_dataset.py
```

### Model and serving

| | |
|---|---|
| Model | `gpt-oss:120b` |
| Endpoint | `https://genai.uni-obuda.hu/api/chat/completions` (OpenAI-compatible, Open WebUI in front of Ollama) |
| Screening round 1 | `temperature=0.1`, `max_tokens=800`, `presence_penalty=0.6` |
| Screening round 2 | `temperature=0.1`, `max_tokens=500`, `presence_penalty=0.2` |
| Data extraction | server-side defaults (no sampling parameters sent) |
| Seed | none set |
| PDF window | first 25 000 characters |

The exact backend build and the server-side default sampling parameters were
not recorded at run time and cannot be reconstructed.

## Manual steps in the pipeline

Two steps in the workflow were human judgment and are not scripted:

1. **From screening to full-text extraction.** The primary reviewer assessed the
   second-round output, removed the 18 records whose full text could not be
   retrieved, made the final inclusion decision, and matched each included study
   to a downloaded PDF. One study (`paper088`) was added after the automated
   rounds had finished.
2. **Charting the free-text variables.** The `Industry sector` and
   `High-level goal` columns are free text. Consolidating them into the eight
   sectors and five use case categories reported in the paper was a per-record
   reviewer decision. `sector_mapping.csv` and `usecase_mapping.csv` make that
   consolidation explicit; see "Known discrepancies" for their current state.

## Scope of the published dataset

The published dataset is a **deliberate subset** of the full extraction: 18 of
34 columns. Fifteen columns are withheld because they are reserved for
follow-up work and are not reported anywhere in the paper. `data_dictionary.md`
lists them.

This is implemented as an explicit allowlist (`PUBLISHED_COLUMNS` in
`scripts/05_build_public_dataset.py`), not a drop-list, so that any column added
to the extraction in future stays unpublished until someone deliberately
publishes it.

### Why the abstracts are not included

The `Abstract` column is withheld for a different reason than the other fifteen,
and it matters methodologically, so it deserves stating clearly:

**The abstracts were used.** Both LLM screening rounds consumed title +
abstract, so the abstracts are the actual model input for the screening
described in Section II-D. They are not incidental.

**They are nevertheless not ours to redistribute.** They are the publishers'
copyrighted material, retrieved from Scopus and IEEE Xplore exports. This
follows PRISMA-S (Rethlefsen et al., *Systematic Reviews*, 2021), which states
that "abstracts are copyrighted materials and should be removed from files
before sharing them publicly", and PRISMA 2020 item 27, which notes that records
exported from bibliographic databases typically include copyrighted material.

**They can be reconstructed.** `scripts/06_rehydrate_abstracts.py` retrieves
abstracts for the published DOIs from OpenAlex, falling back to Semantic
Scholar. Coverage is uneven by publisher and changes over time; the script
reports its achieved coverage rather than assuming completeness. Do not
redistribute its output.

## Known discrepancies

We document these rather than adjust either the code or the data to hide them.

### PRISMA-ScR flow counts (Fig. 1)

Two hand-transcribed tallies in the paper are each off by one. Both were traced
to their source; neither affects any result.

| Quantity | Paper (Fig. 1) | Actual | Cause |
|---|---|---|---|
| Records identified | 1591 | **1590** | Scopus contributed 972 records, not 973 |
| Duplicates removed | 220 | **219** | follows from the line above |
| Records screened | 1371 | 1371 | ✓ |
| Excluded at screening | 1222 | **1223** | hand-typed tally in the working spreadsheet miscounted the `N` decisions by one |
| Sought for retrieval | 149 | **148** | follows from the line above |
| Assessed for eligibility | 131 | **130** | follows from the line above |
| Included studies | 88 | 88 | ✓ |

The IEEE Xplore count of 618 in the paper is correct: 617 records came from the
Xplore exports and one was added manually from a reference manager.

Everything downstream matches the paper exactly: 88 included studies, real-world
validation 81/88 (92.0%), open-source availability 3/88 (3.4%), and all five
platform shares.

### Sector and use case consolidation

The lookup tables that produced the eight consolidated sectors and five use case
categories were not preserved, so they were reconstructed. Three files make the
reconstruction explicit and auditable:

- `sector_mapping.csv` — raw sector value to consolidated sector, following the
  reviewer's documented charting rationale
- `usecase_mapping.csv` — raw goal string to use case category. Because the
  original lookup table was lost, this was reconstructed with LLM assistance:
  two separate model sessions were each given only the 87 distinct goal strings
  and the category definitions, and their outputs agreed on 83 of 87 strings.
  **This is a reconstruction aid, not a second human coder.** It is not
  inter-rater reliability and does not alter the limitation stated in the paper,
  that no second independent reviewer screened the dataset. The reviewer
  retains responsibility for the categories as published.
- `record_overrides.csv` — per-record corrections, each with a written
  justification, for studies whose charted category differs from what their raw
  free-text label implies

The overrides are derived from published evidence, not fitted to the totals.
Figure 2's segment structure is itself a constraint: it shows a Logistics &
Handling segment in exactly four sectors, which rules out six of the ten
candidate studies and, combined with the category description in Section III-A
("inventory monitoring, manipulation using mounted robotic arms, or the passive
towing of materials"), determines all four.

**What this reproduces exactly:** all five use case totals (35 / 12 / 10 / 4 /
27), six of the eight sector totals, all five platform shares, overall
validation and open-source rates, and seven of the eight per-sector rates in
Figure 4.

**What it does not:** one study is charted here under General Industrial that
the paper counts under Oil & Gas, so those two sectors read 18 and 8 rather than
17 and 9, and the General Industrial validation rate reads 94.4% rather than
94.1%. None of the eight General Industrial candidates mentions oil, gas, a
refinery, a pipeline or an offshore setting in its title or extracted goal, so
we could not identify the study on the evidence available. Rather than pick one
to make the total agree, we leave it documented here.

## Differences from the working scripts

The scripts here are consolidated and cleaned versions of the original working
code. The logic that produced the published results is preserved; the changes
are:

- Comments and identifiers translated from Hungarian to English.
- Hardcoded credentials replaced by `os.environ["LLM_API_KEY"]` via
  `python-dotenv`, failing loudly when unset.
- Prompts moved out of string literals into `prompts/`.
- Three screening scripts merged into `02_llm_screening.py`; the duplicated HTTP
  client merged into `_common.py`. Per-stage sampling parameters are preserved
  exactly and live in the prompt front matter.
- Relative paths throughout; no absolute paths.
- `00_ris_to_xlsx.py` no longer generates the sci-hub URLs the original built
  into a `Fulltext` column. That column is not published and no result depends
  on it.
- `server_test.py`, a scratch connectivity check, is not included.
- `double_check.py` is not included as a script: it printed to the console and
  wrote nothing, so it has no reproducible output. Its prompt is published in
  `prompts/verification_double_check.md` for transparency.
- `04_analysis_and_figures.py` is new. The original working directory contained
  no analysis or plotting code.

## Adapting this to another review

The pipeline splits cleanly into parts that are generic and parts that encode
this specific review. Nothing about the workflow is quadruped-specific; the
review question lives almost entirely in `prompts/`.

**Generic — usually needs no change:** RIS parsing, title + DOI deduplication,
the two-round screening loop with resume and autosave, retry with exponential
backoff, PDF text extraction, credential handling.

**What you would change, in the order you would hit it:**

| # | Change | Where |
|---|---|---|
| 1 | Your review question, inclusion and exclusion criteria, output format | `prompts/abstract_screening_round1.md`, `prompts/abstract_screening_round2.md` |
| 2 | The variables you want charted | `prompts/data_extraction.md` |
| 3 | The column names those variables land in — **must match the number and order of fields in the extraction prompt** | `EXTRACTION_COLUMNS` in `scripts/03_llm_extraction.py` (15 fields here) |
| 4 | Which columns you publish | `PUBLISHED_COLUMNS` in `scripts/05_build_public_dataset.py` |
| 5 | Your categories and the figures | `PLATFORM_RULES`, `PLATFORM_ORDER`, `USECASE_ORDER` and the plotting functions in `scripts/04_analysis_and_figures.py`, plus the three CSVs in `data/` |
| 6 | Model and endpoint | `MODEL` and `DEFAULT_API_URL` in `scripts/_common.py`, or set `LLM_API_URL` in `.env` |
| 7 | Sampling parameters per stage | the front matter of each file in `prompts/` |

**Assumptions baked into the scripts.** Screening reads columns named `Title`
and `Abstract`; extraction matches PDFs by a column named `Pdf name` holding the
filename without extension; deduplication expects `Title` and `Doi`, with `na`
marking a missing DOI. Rename these in your input or adjust the constants at the
top of each script.

**One thing worth keeping.** `PUBLISHED_COLUMNS` is an allowlist, not a
drop-list. If you extract more variables than you intend to publish, an allowlist
fails safe: a newly added column stays unpublished until someone deliberately
adds it. A drop-list leaks it by default. The comment in
`05_build_public_dataset.py` explains this at the point of change.

**A caution, not a disclaimer.** The LLM stages are non-deterministic and were
never treated as authoritative here — every decision was human-verified, and the
paper reports the human-LLM agreement (76.0% absolute, Cohen's κ 0.40) rather
than assuming the model was right. If you reuse this workflow, plan for the same
verification step and report the same kind of reliability figure. The pipeline
saves you typing, not judgement.

## Citation

If you use this dataset or code, please cite the paper. A `CITATION.cff` will be
added once the DOI is assigned.

## Funding

This research was supported by the Consolidator Researcher Grant of Obuda
University (Grant ID: OKPPKPC004).

Project 2024-1.2.3-HU-RIZONT-00069 has been implemented with support provided by
the Ministry of Culture and Innovation of Hungary from the National Research,
Development and Innovation Fund, financed under the 2024-1.2.3-HU-RIZONT funding
scheme.

Project 2024-1.2.11-TÉT-IPARI-TR-2025-00031 has been implemented with support
provided by the Ministry of Culture and Innovation of Hungary, with the
cooperation of the National Research, Development and Innovation Office,
financed from the National Research, Development and Innovation Fund.

## License

This repository is released under two licenses, because code and data are
different legal objects and a single license fits neither well.

- **Code** — `scripts/` and `prompts/`: [MIT](LICENSE) · SPDX `MIT`
- **Data** — `data/`: [Creative Commons Attribution 4.0 International](data/LICENSE) · SPDX `CC-BY-4.0`

CC BY **4.0** is used specifically because it covers EU *sui generis* database
rights, which earlier CC versions do not.

The dataset contains bibliographic metadata retrieved from Scopus and IEEE
Xplore. The CC BY 4.0 grant covers our selection, arrangement and coded
variables. It cannot and does not purport to license the underlying
bibliographic records beyond what the source databases' terms allow.
