# analysis/ — the review pipeline

Ported from the SISY 2026 reproducibility release
(`Downloads/RIS/release/`), which produced the 88-study baseline. Code is
MIT, data CC BY 4.0; see `LICENSE`.

Reusing that pipeline rather than writing a new one is deliberate: the
merged corpus has to sit on **one provenance**. If search round 2 were
screened by different code than round 1, the two halves of the corpus
would differ in origin and Methods would have to disclose it.

## Layout

```
scripts/
  _common.py               prompt loading, credentials, HTTP client   [ported, extended]
  00_ris_to_xlsx.py        RIS exports -> one table                   [ported as-is]
  01_deduplicate.py        title + DOI deduplication                  [ported as-is]
  02_llm_screening.py      two-round title/abstract screening         [ported as-is]
  03_llm_extraction.py     the SISY 15-field extraction               [ported, kept for provenance]
  10_rci_extraction.py     RCI extraction: chunked, JSON, evidence    [new]
  11_agreement.py          agreement stats, written to disk           [new]
  probe_context.py         verify the endpoint's real context window  [new]
  probe_pdf_window.py      the measurement behind the window decision [new]
prompts/
  abstract_screening_round1.md, abstract_screening_round2.md          [ported]
  data_extraction.md                                                  [ported]
  verification_double_check.md                                        [ported, superseded]
  rci_extraction.md        nine RCI items, JSON, verbatim quotes      [new]
```

Sampling parameters live in each prompt's front matter, per stage. They
differ between stages and **must not be unified** — they are the record
of what was actually run.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in LLM_API_KEY
```

`PDF_DIR` defaults to the corpus PDF folder and can be overridden by
environment variable or `--pdf-dir`. The PDFs are copyrighted and are not
in this repository.

## Before the first real run

```bash
python scripts/probe_context.py
```

This is not optional. Ollama-backed gateways commonly default to a small
`num_ctx` regardless of the model's architectural limit, and they do not
error when the input exceeds it — they **silently truncate**. Silent
truncation is indistinguishable from "the paper does not report this",
which is the one failure mode that would bias RQ4 invisibly. The probe
sends canary phrases at both ends of a long input and reports which ones
survive. Set `--chunk-chars` from its answer and record the result in
Methods.

## Why the 25 000-character window had to go

`03_llm_extraction.py` read the first 25 000 characters of each PDF. Its
comment explains the choice: hardware specifications sit on pages 6–8.
That is sound for sensors and compute. It does not hold for RCI items 4,
6 and 7, whose evidence lives in the implementation and experiments
sections.

Measured over all 88 corpus PDFs (`probe_pdf_window.py`):

| | |
|---|---|
| Document length | median 36 556 chars, p90 87 495, max 159 323 |
| Truncated by a 25 000-char read | **74 of 88** |
| Corpus total | 3 928 611 chars, mean 44 643/doc |

Where the evidence sits, relative to that window:

| Marker | Papers containing it | First mention inside 25k | **Last** mention inside 25k |
|---|---:|---:|---:|
| item 4 — middleware | 42/88 | 34 | **17** |
| item 6 — parameters | 65/88 | 54 | **25** |
| item 7 — evaluation env. | 80/88 | 76 | **23** |
| control — sensors | 61/88 | 54 | 23 |
| control — compute | 81/88 | 72 | 25 |

The first-mention column understates the problem, and the gap between the
two columns is the finding. For item 7 the first hit lands at a median of
2 357 characters — that is the *abstract* saying "experiments", not a
description anyone could re-create a setup from. The text that actually
satisfies the rubric item is later: 57 of 80 papers have their last
evaluation-related mention beyond 25 000 characters.

Enlarging the window does not fix this either. Going from 25k to the full
document moves first-mention coverage by only 4–13 percentage points,
because a fixed window of *any* size still cuts the tail of long papers —
and long papers are exactly the ones with substantial experiments
sections. So `10_rci_extraction.py` reads the **whole document in
overlapping chunks**: 30 000 characters with 4 000 overlap by default,
about 131 chunk calls for the corpus.

Had the window stayed at 25k, items 4, 6 and 7 would have been
systematically under-detected, and the resulting "studies do not report
this" finding would have pointed in exactly the direction the paper's
argument already predicts. Confirmatory bias manufactured by a constant.

## The merge rule

A chunk that does not mention ROS is not evidence that the paper does not
use ROS. So, in `10_rci_extraction.py`:

- `found=true` in **any** chunk wins, and carries that chunk's quote and
  character offset.
- `found=false` is concluded only when **every** chunk was read and parsed
  and none reported the item.
- if **any** chunk failed — API error or unparseable reply — the record's
  status is `incomplete`, and its negatives are **not** usable as "not
  reported".

The third rule is the one that matters. Without it a transport failure
silently becomes a finding of non-reporting. Incomplete records are
re-tried on the next run (the resume logic deliberately skips only `ok`)
or resolved by hand — never averaged in.

A positive code without a verbatim quote is also rejected at merge time,
not just discouraged in the prompt. Prompts are not guarantees.

## Two extraction passes

```bash
python scripts/10_rci_extraction.py --pass A
LLM_MODEL=qwen3.6:35b-a3b python scripts/10_rci_extraction.py --pass B
```

Two runs of the *same* model produce correlated errors: they agree with
each other while measuring nothing. Pass B should be a genuinely
different model. If that turns out to be impossible, say so in Methods
rather than implying independence that was not there.

## Agreement

```bash
# inter-pass, whole corpus
python scripts/11_agreement.py --a work/rci_A_records.xlsx \
                               --b work/rci_B_records.xlsx --label pass_A_vs_pass_B

# the load-bearing one: blind human subsample vs the LLM
python scripts/11_agreement.py --a work/rci_human_subsample.xlsx \
                               --b work/rci_A_records.xlsx \
                               --label human_vs_llm --a-name human --b-name llm
```

Writes a CSV and a Markdown table to `work/`. The SISY cross-check
printed to the console and wrote nothing, which is why the release ships
its prompt but no script. Here that output *is* the reliability evidence,
so it has to be a file.

Per item it reports raw agreement with a Wilson interval, **prevalence on
both sides**, and Cohen's κ with an asymptotic interval. Prevalence sits
next to κ because on a rare item the two point in opposite directions:
artefact availability was 3 of 88 in round 1, where coders can agree on
97% of studies and still produce κ near zero. Where a coding is constant,
κ is undefined and is reported as undefined, not as 0.

**Labelling.** `human_vs_llm` is LLM extraction accuracy against a human
reference standard on a subsample. It is not inter-rater reliability
between independent human coders and must never be reported as such.

## Not carried over

- `04_analysis_and_figures.py`, `05_build_public_dataset.py`,
  `06_rehydrate_abstracts.py` — SISY-specific outputs. The Sensors
  figures are a separate task.
- The SISY `data/`, `figures/` and `work/` contents.
- Anything from outside `release/`. The original working scripts contain
  a hardcoded (revoked) API key in a variable named `API_KULCS`; none of
  it was copied. Credentials come from `LLM_API_KEY` only.
