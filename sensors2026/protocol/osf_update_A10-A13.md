AMENDMENT LOG, continued (added 29 October 2026)

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
