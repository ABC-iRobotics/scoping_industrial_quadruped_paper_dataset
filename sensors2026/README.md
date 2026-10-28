# Visual perception payloads on industrial quadruped robots — data and code

Release accompanying the scoping review *"A Scoping Review of Visual Perception
Payloads on Industrial Quadruped Robots: Sensing Modalities, Onboard Compute,
and Reporting Completeness"* (Zsoldos, P.; Galambos, P.; submitted to MDPI
*Sensors*). It extends the earlier SISY 2026 review whose data are in the root
of this repository.

- **Protocol and amendment log:** OSF, <https://osf.io/r8zs6/overview>, and
  `protocol/osf_protocol.md`, `protocol/osf_amendment_log.md` (deviations A1–A13).
- **Search strings as executed:** `protocol/round2_search_strategy.md`.

## Contents

| Folder | What it holds |
|---|---|
| `data/charting_v2.xlsx` | The frozen charting table: one row per included study (108), final codes, controlled-vocabulary classes, RCI, and provenance columns (`code_source`, `sector_source`, `optical_sensors_source`, `onboard_computer_source`, `fails_current_criteria`). |
| `data/pipeline/` | Every human decision and model output that fed the table: signed codebooks, adjudication and re-adjudication logs, the blind validation coding (with the original codes before correction), full-text decisions, the title-scan recheck, the baseline eligibility audit, per-pass extraction records with their verbatim evidence quotations, and the files that amendments keep as retained (`rci_A_v1`, `*_B_qwen36`, `fte_A_v1`). |
| `results/` | Agreement and accuracy tables, PRISMA counts, the generated numbers (`numbers.tex`), figures, LaTeX tables, and the Supplementary Materials. |
| `code/` | The scripts that produced every reported number (`scripts/00`–`61`), the prompts with their sampling parameters, and the run scripts. |

## Reproducing the analysis

`code/scripts/42_build_final.py` rebuilds the charting table from the pass
records and the human decisions; `50_results.py`, `51_pipeline_accuracy.py`,
`52_tables.py` and `40_emit_numbers.py` regenerate every figure, table and
number in the paper from it. The extraction stages call a language-model
endpoint without a random seed, so re-running them will not reproduce the
model outputs exactly; the outputs used are included.

## Not included

Full texts (copyright), database exports and abstracts (providers' terms of
use; the Abstract, Keywords and Reference columns are removed from every
table), and raw activity logs (personal data; only the derived minutes are
included).

## Licences

Code: MIT. Data: CC BY 4.0 (see the licence files in the repository root).
