# Scoping review protocol — visual perception payloads on industrial quadruped robots

Prepared for registration on the Open Science Framework (osf.io).
Registered: **https://osf.io/r8zs6/overview**, 3 September 2026.
Search cut-off: **3 September 2026**.

> Paste into the OSF registration form. Sections map onto the standard
> OSF "Open-Ended Registration" fields; keep the headings.

---

## 1. Title

A Scoping Review of Visual Perception Payloads on Industrial Quadruped
Robots: Sensing Modalities, Onboard Compute, and Reporting Completeness.

## 2. Review team

- Panna Zsoldos — Antal Bejczy Center for Intelligent Robotics, Obuda
  University. Sole reviewer and human coder; corresponding author.
- Péter Galambos — supervision; editorial review of the finished
  manuscript. Does not screen, chart or code.

There is **one human coder**. This is a deliberate design constraint, not
an omission, and Section 9 describes how reliability is established
without a second independent human rater.

## 3. Registration status — partly retrospective, stated plainly

This registration is **not fully prospective**, and the boundary is
exactly here:

**Completed before registration (retrospective):**

- The round-1 literature search (Scopus and IEEE Xplore, 2019 to mid-2026)
  and the two-stage screening that produced a baseline of **88 included
  studies**, reported in a prior conference paper by the same first author
  (SISY 2026).
- The round-1 charting of that baseline on a 34-variable schema.
- A **5-study pilot** of the extraction pipeline described in Section 8,
  run on 1–2 September 2026 to calibrate chunk size, verify that the
  serving endpoint does not silently truncate long inputs, and tighten the
  evidence-quote rule. The pilot produced no review findings and its
  outputs are not carried into the analysis; it is disclosed because it
  shaped the protocol.

**Performed after registration (prospective):**

- The **entire round-2 search** across three databases (Scopus, IEEE
  Xplore and, newly, Web of Science) to the common cut-off, its
  deduplication against the baseline, and the screening and charting of
  all newly identified records.
- **All variables this review analyses**, over the **whole merged corpus**
  including the 88 baseline studies: optical sensing modalities, onboard
  compute, the reporting-specificity coding, and all nine items of the
  Reporting Completeness Index.

The baseline's round-1 charting of the perception variables is **not
inherited**. It is re-extracted after registration, for three reasons: it
was produced by a 25,000-character partial read of each PDF; it was never
verified by a human, because the prior paper did not report those columns;
and re-extraction gives the merged corpus a single extraction provenance
instead of two vintages. The round-1 values are retained solely as a
comparison and provenance record.

No claim of a fully prospective registration is made anywhere in the
resulting manuscript.

## 4. Rationale

Quadruped robots are being deployed in industrial inspection, mapping and
monitoring, and their capability rests on an optical perception payload:
cameras, depth sensors, LiDAR, thermal imagers, and the onboard computer
that runs them. Existing reviews describe platforms and use cases. What
they do not characterise is the perception payload itself, or how
completely it is reported.

The second question is the more consequential one. A perception pipeline
cannot be reimplemented from a paper that names neither the sensor nor the
compute it ran on.

## 5. Research questions

- **RQ1** — Which optical sensing modalities are reported on industrial
  quadruped deployments, and in what combinations?
- **RQ2** — How do modalities map onto perception capabilities
  (SLAM/mapping, autonomous navigation, obstacle avoidance, object
  detection, instrument reading, target tracking), and onto industrial
  sectors and tasks?
- **RQ3** — What onboard computing platforms support these payloads?
- **RQ4** — How completely are the sensing, computing and software
  configurations reported, and what follows for the ability of an
  independent engineer to attempt a reimplementation?

## 6. Eligibility criteria (PCC)

Population–Concept–Context, following Peters et al. Criteria are unchanged
from round 1, so that the two search rounds pool into one corpus.

| Element | Include | Exclude |
|---|---|---|
| **Population** | Quadruped or four-legged robots capable of autonomous or semi-autonomous locomotion: commercial platforms (Boston Dynamics Spot, ANYbotics ANYmal, Unitree Go, and similar) and research prototypes clearly identified as quadrupeds. | Bipedal, humanoid, wheeled, tracked or aerial platforms. Simulation-only studies, unless the simulation is explicitly validated on physical quadruped hardware. |
| **Concept** | A concrete industrial task — inspection, mapping, logistics, safety monitoring — together with a description of the robot's hardware configuration. | Component-level work only: actuator design, gait optimisation, joint mechanics, low-level control, kinematics, with no demonstrated industrial use case. Purely theoretical algorithm or architecture papers with no implementation on a quadruped. |
| **Context** | Deployment or experimental validation in an industrial setting: plants, warehouses, construction sites, power plants, mines, oil-and-gas facilities, other harsh industrial environments. High-fidelity industrial simulations qualify only with hardware-in-the-loop or hardware-based verification and faithful reproduction of real constraints (dust, vibration, dynamic obstacles, complex layouts). | Non-industrial domains: military, space, agriculture, healthcare, disaster response, search-and-rescue. Laboratory-only experiments not emulating industrial conditions. |

Additional limits: **English language**, **2019 onward**. Excluded
publication types: conference or workshop abstracts without full papers,
grey literature, technical reports, patents, theses, and review articles.
Publication type is assessed at screening, not filtered in the query.

## 7. Information sources and search strategy

Three databases, searched on **3 September 2026**, one common cut-off:
**Scopus**, **IEEE Xplore**, **Web of Science Core Collection**. Web of
Science is new relative to round 1; Scopus and IEEE Xplore are re-run to
pick up everything published since.

The query is the intersection of two Boolean blocks. The Concept element
is deliberately **not** in the query — it is applied at screening, to
maximise sensitivity.

```
platform:   ("quadruped*" OR "four-legged" OR "legged robot*"
             OR "legged platform*")
            AND NOT ("humanoid*" OR "bipedal" OR "two-legged")

context:    ("industry" OR "industrial" OR "industry 4.0" OR "manufacturing"
             OR "factory" OR "factories" OR "warehouse*" OR "plant"
             OR "plants" OR "construction site*" OR "oil and gas"
             OR "mining" OR "power plant*" OR "harsh environment*"
             OR "production line*" OR "facilities" OR "logistics"
             OR "shop floor" OR "field deployment")
```

Field qualifiers: `TITLE-ABS-KEY` in Scopus, `TS=` in Web of Science,
`"All Metadata"` in IEEE Xplore. `TS=` additionally covers Keywords Plus,
which is slightly broader than the other two; this is a property of the
databases and is reported rather than suppressed. The database-native
strings as executed, with hit counts and timestamps, are recorded in the
review's public repository.

No citation chasing, no grey-literature search, no contact with authors.

## 8. Selection and charting process

**Deduplication** runs twice: within round 2 across the three databases,
and against the 88-study baseline. Matching is on normalised DOI first,
then normalised title and year for records without a DOI, with manual
inspection of near-misses — preprint, conference and journal versions of
one work are the expected failure case.

**Screening** is two-stage: title and abstract, then full text. Screening
is LLM-assisted with human adjudication; the human makes every final
inclusion decision.

**Charting** is **LLM-primary with human validation**. For every study,
the model reads the **entire full text in overlapping chunks** (30,000
characters, 4,000 overlap) rather than a fixed prefix, and returns for
each variable a code and a **verbatim evidence quote** with its character
offset. Quotes are verified mechanically against the source text; a
positive code whose quote cannot be located as a single continuous run of
text is rejected and routed to human review. A variable is recorded as
"not reported" only when every chunk of that document was read and parsed
successfully.

**Model and serving.** `gpt-oss:120b` for pass A and `qwen3.6:35b-a3b` — a
different model family — for pass B, both served via an institutional Open
WebUI/Ollama endpoint. Pass B is the smaller model of the two; where the
passes disagree, the human adjudicates, and the asymmetry is reported.
The backend build and server-side sampling defaults are recorded at run
time. No seed is available: the stages are non-deterministic, and this is
stated in the limitations.

## 9. Reliability and validation

Four components, all of which must be present:

1. **Every code carries a verbatim evidence quote**, machine-verified
   against the source. Codes without a locatable quote are not codes.
2. **Two independent extraction passes** over the whole corpus, using two
   **different model families** — not two runs of one model, which produce
   correlated errors that inflate apparent agreement while measuring
   nothing.
3. **Human adjudication of every inter-pass disagreement**, logged as
   study, item, pass-1 code, pass-2 code, final code, and a one-line
   reason. The log is published as supplementary material.
4. **A blind human validation subsample.** A random sample of
   approximately 30 studies is drawn **before any model output is
   inspected**, and coded by the human reviewer from the full texts
   **without sight of the model's answers**. This covers the perception
   variables as well as the RCI items.

Reported per item on the subsample: raw agreement with a Wilson interval,
**the prevalence of the positive code on both sides**, and Cohen's κ with
an interval. Prevalence is reported next to κ because on a rare item the
two point in opposite directions. Where a coding is constant, κ is
undefined and is reported as undefined, not as zero.

**This is LLM extraction accuracy measured against a human reference
standard on a subsample. It is not inter-rater reliability between
independent human coders and will not be described as such.**

If a peer agrees to blind-code an overlapping portion of the subsample,
human–human agreement on that overlap is reported alongside. Such a person
is acknowledged, not an author.

The **codebook sign-off remains a manual, row-by-row human decision** and
is not automated.

## 10. Charting variables

Bibliographic: authors, year, title, DOI, venue, database source, search
round, record identifier.

Analytical:

- `Optical Sensors` — free text as written, then classified (RQ1)
- `Onboard Computer` — free text as written, then classified (RQ3)
- Six capability flags: SLAM/mapping, autonomous navigation, obstacle
  avoidance, object detection, instrument reading, target tracking (RQ2)
- `Industry sector`, `High-level goal` — cross-tabulation axes
- `AI / ML solutions for vision` — free text describing the perception
  method
- `Real-world validation`, `Open source`, `Success metric for goal task`,
  `Environmental challenges`, `Robot platform`
- The nine RCI items (Section 12)
- `eval_environment_kind` — real, simulated, both or unclear, recorded
  alongside RCI item 7 so that the binary item stays mechanically checkable
  while the real-versus-simulated distinction remains analysable

## 11. Controlled vocabulary and specificity scale

**Sensor classes** (multi-label; one study may fall in several): LiDAR,
RGB camera, depth/RGB-D, stereo, thermal/IR, unspecified. **Compute
classes** are derived the same way from the onboard-computer strings.

Every raw string is mapped to a class by a **written rule**, and the
mapping table — raw string → class → rule — is signed off by the human
reviewer row by row and published as supplementary material. The rules are
written so a newly identified record can be classified without reopening
the discussion.

**Reporting specificity** is a three-level ordinal scale, applied
independently to the sensor field and the compute field:

| Level | Definition |
|---|---|
| `model` | Make and model stated, e.g. "Intel RealSense D455", "NVIDIA Jetson AGX Xavier" |
| `modality` | Only the class stated, e.g. "an RGB-D camera", "an embedded GPU" |
| `unspecified` | No optical sensor / onboard computer named |

These two become items 2 and 3 of the index below.

## 12. The Reporting Completeness Index (RCI)

Nine binary items, each answerable by pointing at **one sentence** in the
primary study. The sum is the RCI, range 0–9.

| # | Item | Counts only if |
|---|---|---|
| 1 | Robot platform named at model level | e.g. "Boston Dynamics Spot", "ANYmal C". "A quadruped robot" does not count |
| 2 | Optical sensor named at model level | make and model. "An RGB-D camera" names only the class |
| 3 | Onboard compute named at model level | e.g. "NVIDIA Jetson AGX Xavier". "An onboard computer" does not count, and neither does a workstation or laptop used only to run the experiments — it must be the machine the robot carries |
| 4 | Middleware/framework named **with version** | e.g. "ROS 2 Humble", "Ubuntu 20.04". "ROS" alone does not count |
| 5 | Core algorithm named **and attributed** | a citation or a specific named method, e.g. "FAST-LIO2", "YOLOv8". "A deep-learning detector" does not count |
| 6 | At least one concrete operating parameter | e.g. "LiDAR at 10 Hz", "voxel size 0.4 m", "640×480" |
| 7 | Evaluation environment described concretely enough to set up something comparable | at least one measurable quantity — a dimension, distance, duration, or count of assets. "We tested in a real industrial environment" does not count. Real versus simulated is recorded separately, not in this item |
| 8 | A quantitative result for the goal task | a number: accuracy, success rate, RMSE, coverage, time. "Performed well" does not count |
| 9 | Code, data or model stated to be publicly available | normally with a URL or repository |

**Two items were tightened after the pilot, before registration.** A five-study
calibration run with two different models disagreed on exactly two items, and in
both cases the disagreement traced to the rubric rather than to the models: item 3
did not distinguish the robot's onboard computer from a workstation used to run
the experiments, and item 7 set no threshold for what counts as a concrete
description. Both were given operational criteria before this protocol was
registered, and no coding from the pilot is carried into the analysis.

**Coding rules.** A code is positive only on evidence present in the text;
absence of evidence in one chunk is never evidence of absence for the
document. Outside knowledge is not used — that a given robot usually ships
with a particular computer is irrelevant to what the paper states. The
full item wording given to the model, including the non-qualifying
examples, is version-controlled in the review's repository as
`analysis/prompts/rci_extraction.md`.

**What the index does and does not claim.** It measures **reported
information**, not verified reproducibility. Establishing the latter would
require reimplementing the systems, which is out of scope. No study is
described as "reproducible"; studies report *n* of 9 items. The index is
modelled on established artefact-badging schemes (ACM Artifact Review and
Badging v1.1; IEEE/NISO Reproducibility Badging) and on the
signalling-question structure of risk-of-bias instruments such as Cochrane
RoB 2, and is not presented as novel.

The prior round's single holistic `Reproducable?` yes/no judgement is
retained as a **comparison variable**, to show how a holistic call relates
to the itemised score. It is itself unverified and is validated within the
subsample before any argument is built on it.

## 13. Synthesis and presentation

Descriptive synthesis, no meta-analysis. Frequencies and co-occurrence of
modalities; modality × capability and modality × sector cross-tabulations;
distribution of RCI scores overall and by sector; reporting specificity by
sector. A PRISMA-ScR flow diagram and a completed PRISMA-ScR checklist are
included. All flow counts are computed from the data, not transcribed by
hand.

## 14. Amendments

Any deviation from this protocol is recorded in the OSF registration's
amendment log with its date and reason, and reported in the manuscript.

## 15. Data availability

The charting data, codebook, adjudication log and pipeline code are
published in the review's public repository, cited at a fixed tagged
release. Full-text PDFs and raw database exports are not redistributable
and are not published. This protocol is cited in the manuscript's Methods
by its OSF link.

## 16. Funding and conflicts

Institutional funding; the university covers publication costs. Grant
identifiers are stated in the manuscript. No competing interests.

## 17. Amendment log

Deviations from the protocol as registered, each with its date and reason.
Kept here and mirrored in the OSF registration's amendment log.

### A1 - 4 September 2026: RCI item 9 tightened

**Change.** Item 9 now requires the artefact to be one the *authors of that
paper* released, and explicitly excludes publisher supplementary-material
boilerplate.

**Why.** Pass A over the 88-study baseline returned 19 of 87 positives for item
9, against 3 of 88 in the round-1 charting - a variable the prior review
verified by hand. Reading the 19 evidence quotes showed the item was collecting
three different things: genuine author releases, standard publisher sentences
("This article has supplementary downloadable material available at <doi>",
usually attached to a video), and third-party tools the authors merely used
("ROS 2 Wrapper for Spot. Available online: ...", "we forked the public Y
repository"). Roughly half the positives were of the latter two kinds.

**Why this could not be left to adjudication.** The design routes disagreement
between the two passes to a human. This error is not a disagreement: both
models read publisher boilerplate the same way and both are wrong, so it is
invisible to the inter-pass check and would survive into the reported number.
Correlated error is exactly the failure mode the two-pass design cannot catch,
which is why the instrument, not the adjudication, had to change.

**Consequence.** Item 9 is re-extracted for the whole corpus under the amended
wording. The pre-amendment coding is retained as `rci_A_v1` / `rci_B_v1` rather
than discarded, so the effect of the amendment is auditable.

**What was not changed.** The other eight items, the specificity scale, and the
capability instrument are untouched.

### A2 - 4 September 2026: unreadable PDFs are no longer coded

**Change.** Before extraction, a document's text layer is checked as characters
per page. Below 1,000 the record is marked `text extraction failed`, no model
call is made, and it is routed to manual retrieval instead of being coded.

**Why.** One baseline PDF (`paper043`) is a 6-page scanned document yielding
2,160 characters - 360 per page, against a corpus median of 4,795 and a lowest
genuine document of 1,981. The previous guard tripped only below 100 characters,
so this document passed and was coded: every item returned "not reported", and
those negatives entered the prevalence counts as if they were findings. It is
the same failure the chunked reading was introduced to prevent, arriving through
a different door - an unread document and an uninformative one are
indistinguishable in the output unless something checks.

**Scope.** One study in the 88-record baseline. The guard matters more for
round 2, where 76 full texts are being retrieved and scanned copies are likelier.

**Consequence.** `paper043` is excluded from the coded set and flagged for
retrieval of a text-layer copy; if none exists it is reported as a study whose
full text could not be assessed, which is a PRISMA-ScR category, not a zero.

### A3 - 26 September 2026: pass-B model replaced

**Change.** The second extraction pass now uses `Qwen3.8-Flash-Next` instead of
`qwen3.6:35b-a3b`, and it is re-run over the **whole corpus** - the 88-study
baseline as well as round 2 - for the RCI instrument, the capability instrument
and full-text eligibility.

**Why.** On 26 September 2026 the institutional endpoint stopped serving
`qwen3.6:35b-a3b` (HTTP 400, `Model not found`). Round 2 could not be coded
with the registered pass-B model. Of the models still served, `Qwen3.8-Flash-Next`
answered a trivial call in 3.5 s; it is a Qwen model, so it keeps pass B in a
different model family from pass A (`gpt-oss:120b`), which is the property the
two-pass design depends on.

**Why the whole corpus, not only round 2.** Using the new model for round 2 only
would leave the corpus with two pass-B models, and inter-pass agreement would mix
two different rater pairs. Re-running the baseline costs machine time only; no
adjudication had yet been done, so no human work is lost.

**Consequence.** The `qwen3.6:35b-a3b` outputs are retained as `rci_B_qwen36` and
`cap_B_qwen36` and are not used for any reported agreement figure. The
same-model test-retest figures are unaffected: they came from pass A.

### A4 - 26 September 2026: how the Context criterion is applied at full text

**Change.** The full-text eligibility prompt now states how the registered
Context criterion is applied: a laboratory validation of an industrial task on
physical quadruped hardware qualifies; "laboratory-only experiments not
emulating industrial conditions" excludes only work with no industrial task or
use case at all; simulation-only work without hardware validation stays
excluded. The criterion text itself is unchanged.

**Why.** The first advisory LLM pass over the round-2 full texts read the
criterion literally and recommended excluding 32 of 38 documents, most for lack
of a field deployment - far stricter than the human reading in round 1, which
included 7 of 88 studies without real-world validation and records real-world
versus laboratory validation as a separate charting variable. Applying the
literal reading to round 2 only would have made the two rounds inconsistent.
P.Z. decided the round-1 reading applies.

**Consequence.** The first pass is retained as `fte_A_v1` and the eligibility
passes are re-run with the clarified prompt. The model output remains advisory:
P.Z. makes every final inclusion decision, recorded with its reason.

### A5 - 8 October 2026: validation subsample set at 24 studies

**Change.** The blind human validation subsample is 24 studies instead of the
registered "approximately 30": 18 from the round-1 baseline and 6 from round 2.
The baseline stratum was drawn as 24 studies on 26 September 2026 (seed
`20260926-baseline`, recorded in `validation_sample.md`); it is truncated to the
first 18 of that drawn list in record-id order. The six dropped are `paper066`,
`paper069`, `paper075`, `paper080`, `paper081` and `paper083`. The round-2
stratum of 6 is drawn as planned once the round-2 eligibility decisions are made.

**Why.** Coding time: about 40 minutes per study for a single human coder, with
a submission deadline. The loss in precision is small: at about 90% agreement the
95% Wilson interval is roughly 74-98% at n = 24 against 74-97% at n = 30.

**When.** Decided on 8 October 2026, after 11 baseline studies had been coded and
**before any human-LLM agreement figure had been computed or looked at**. The
truncation rule (first 18 in record-id order) is fixed in advance and does not
depend on any coded value, so it cannot select for agreement.

**Consequence.** The six dropped studies are not coded and are not part of the
reference standard. Reported validation figures carry n = 24 (or fewer per item
where an item is not codable) and are labelled accordingly.

### A6 - 20 October 2026: validation subsample is 23 studies

**Change.** The round-2 stratum of the validation subsample has 5 studies, not
6, so the subsample is 23 (18 baseline + 5 round 2) instead of the 24 in A5.

**Why.** The round-2 stratum was drawn on 19 October 2026 (seed
`20260926-round2`) from the 19 round-2 records then marked include. One drawn
record, `r2-0581`, was excluded at full text on 20 October (low-level control
only) before it was coded. A study outside the corpus cannot be part of its
reference standard. It was not replaced: by then round-2 extraction output
existed, so a replacement draw would no longer have been blind to model output.

**Consequence.** Validation figures carry n = 23 (or fewer per item where an
item is not codable).

### A7 - 20 October 2026: five human reference codes for RCI item 4 corrected

**Change.** In the blind human coding, five studies were coded positive on RCI
item 4 (middleware named *with version*) on the strength of an unversioned
"ROS". The registered rule requires a version, so these five reference codes
were corrected to negative.

**Why.** The error was in applying the rule, not in the rule: the coder
recorded that ROS was mentioned, which the item does not ask. It was found
when the human and model codes were compared, i.e. after unblinding, which is
why it is logged rather than silently fixed.

**Consequence.** The blind codes are kept unaltered as
`rci4_middleware_version__blind`, and agreement is reported against both: pass A
agrees with the corrected reference on 23 of 23 studies and with the blind
codes on 18 of 23. No other item was changed after unblinding.

### A8 - 21 October 2026: human title scan of the model's title/abstract exclusions

**Change.** Section 8 states that screening is LLM-assisted and that the human
makes every final inclusion decision. At title and abstract level, records the
model passes excluded would otherwise never reach a human. P.Z. therefore read
the title of every one of the 1,473 round-2 records the model passes excluded,
with the abstract available, and marked those that might meet the criteria.

**Result.** 27 records were marked. On re-reading at abstract level, 9 were sent
to full text and 18 stayed excluded. Of the 9, 3 were included, 5 excluded and
1 could not be retrieved.

**Why.** The earlier review checked this stage the same way (a title scan of the
excluded records for false negatives). Without it, round-2 title/abstract
exclusions would rest on the model alone.

**Consequence.** The included corpus is 108 studies (88 baseline + 20 round 2).
The three added studies are extracted with the same instruments, models and
procedure as the rest.

### A9 - 19-21 October 2026: technical changes to the extraction runs

These change how documents are read and how requests are sent, not what is
coded. They are logged because they alter the run parameters on record.

- **Text decoding.** Two baseline PDFs (`paper011`, `paper028`) carry a text
  layer whose characters are shifted by a constant 29 code points, which
  passes the A2 characters-per-page check but is unreadable. A page is now
  decoded when the shift raises its share of English words to at least 0.12
  and to more than 1.5 times the undecoded share. Both studies were
  re-extracted in both passes.
- **Request limits for pass B.** `Qwen3.8-Flash-Next` spends part of its token
  budget on reasoning and takes about three minutes per chunk. With the
  prompt's own `max_tokens` and the client's 120 s timeout it returned empty
  replies. Pass B was re-run with `max_tokens` = 16,000 and a 900 s timeout;
  incomplete pass-A records were retried once with `max_tokens` = 8,000. The
  overrides are printed into every run log.

### A10 - 23 October 2026: two coding-rule clarifications made after data were seen

**Change.** (1) For RCI items 2 and 3, a product family named without its
variant ("NVIDIA Jetson", "Jetson Orin", "Raspberry Pi", "Intel NUC", "Intel i5
CPU") counts as model level. (2) For the capability item obstacle avoidance,
stairs and slopes are terrain features, not obstacles: climbing them does not
by itself code the item.

**Why.** Both questions arose during coding and adjudication; the registered
wording does not settle them. Rule (1) followed P.Z.'s practice in the blind
validation coding, rule (2) her adjudication of conflicting cases.

**Consequence.** Because both were fixed after codes had been seen, each is
reported with a sensitivity check. For item 3, a strict version (`rci3_strict`)
requires at least one onboard compute string naming a specific model; it is
reported beside the main figure (31 against 44 studies on the current data).
Every adjudicated obstacle-avoidance case that rested on stairs alone was
re-decided under rule (2).

### A11 - 23 October 2026: adjudication re-checked with context; human codes used for the validation subsample

**Change.** (1) Every inter-pass disagreement that was first adjudicated "yes"
from the quotes alone was re-adjudicated with the quote shown in its paragraph
and with counter-evidence passages from the rest of the paper (simulation,
laboratory, teleoperation and similar cues). The re-adjudicated code replaces
the first. (2) For the 23 studies of the blind validation subsample, the blind
human codes are the final codes of the charting table.

**Why.** On the validation subsample the first, quote-only adjudication matched
P.Z.'s own blind full-text codes in 19 of 34 cases, and 14 of the 15 mismatches
were "yes" where the full-text reading said "no". A quote shows the evidence for
a positive code but not the context that undoes it, so quote-only adjudication
leans towards "yes". Across all items the final codes on the subsample had 183
positives against 155 in the blind human coding.

**Consequence.** The accuracy figures reported for the pipeline are computed
from the pass and adjudication codes before either replacement, so the
replacement does not flatter them. The first adjudication is kept unaltered
in the adjudication log, beside the re-adjudicated code.

### A12 - 28 October 2026: eligibility audit of the 88 baseline studies, reported as a sensitivity analysis

**Change.** The 88 round-1 studies were re-checked against the eligibility
criteria as they were applied in round 2. `gpt-oss:120b` read each full text
with the round-2 full-text eligibility prompt (advisory only); P.Z. reviewed
every study it did not recommend for inclusion (18 exclude, 7 unclear) and
decided whether the study would be included today. 16 would not: simulation
only (paper017, paper022, paper084), low-level or locomotion control without
an industrial task (paper006, paper024), and no concrete industrial task or
setting (paper014, paper018, paper020, paper026, paper030, paper032, paper033,
paper067, paper071, paper075, paper076). Building condition assessment
(defect and thermal inspection of buildings) was judged an AEC/construction
task and passes; a generic method tested only in an office does not.

**Why.** Section 4 keeps the baseline inclusion decisions, but round 2 applied
the same criteria more strictly and excluded studies of the kinds listed above
(for example r2-0581, low-level control). Leaving the difference unexamined
would mix two readings of one criterion in one corpus.

**Consequence.** The 16 studies stay in the corpus, as Section 4 requires,
and are flagged (`fails_current_criteria`). Every main result is also reported
for the 92 studies without them, so a reader can see whether any finding
depends on the earlier, looser reading.

### A13 - 28 October 2026: one more human reference code corrected; sources of the sensor and compute strings

**Change.** (1) In the blind validation coding, RCI item 2 for `r2-0677` was
coded positive on the strength of a radiation detector (RadEye SPRD-ER). The
item asks for an *optical* sensor named at model level, so the reference code
was corrected to negative; the blind code is kept as
`rci2_sensors_model__blind`, as for item 4 under A7. (2) The sensor and
compute strings that feed the controlled vocabulary now come from the blind
human coding for the validation studies (consistent with A11), from pass A
otherwise, and from pass B where pass A listed none (2 studies for sensors,
5 for compute). Each study records which source it used. The few strings this
added to the codebooks were classified by the signed rules and are marked as
added.

**Why.** (1) Same reason as A7: a rule-application error found after
unblinding. (2) Pass A missed the sensor list of two studies that pass B and
the human coder both read, which left them counted as reporting no optical
modality while their RCI item 2 said a model was named.

**Consequence.** The human reference now has 154 positives on the
validation subsample (155 before); the pipeline figures in A11 change by one
accordingly.
