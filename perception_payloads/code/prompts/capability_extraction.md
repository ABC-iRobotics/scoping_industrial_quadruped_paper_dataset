---
stage: capability_extraction
script: scripts/12_capability_extraction.py
model: gpt-oss:120b
temperature: 0.1
max_tokens: 2000
presence_penalty: null
system: "You are a meticulous technical data extractor working on a systematic review. You answer only with a single JSON object. You never guess: if you cannot quote the evidence verbatim from the excerpt in front of you, the answer is not found."
---

You are reading an EXCERPT from a research paper about a quadruped robot system
used in an industrial environment. The excerpt may begin or end mid-sentence,
and it may be only part of the paper.

For each item below, decide whether THIS EXCERPT contains the evidence, and if
it does, copy the exact sentence that proves it.

## The seven capability items

Each is answered `true` only when the paper says the system **does** this, not
when it merely mentions the concept, cites related work, or lists it as future
work.

1. `cap_slam_mapping` - The system performs SLAM, localisation-and-mapping, or
   builds a map of its environment. A paper that only *uses* a pre-built map
   does NOT count; a paper that constructs or updates one does.
2. `cap_autonomous_navigation` - The robot navigates autonomously or
   semi-autonomously: it plans and follows paths without a human driving it.
   Teleoperation alone does NOT count. If the paper describes **shared or
   supervised** autonomy, still answer `true` and let the quote show it.
3. `cap_obstacle_avoidance` - The system detects and avoids obstacles, or
   traverses around or over them, as a described function.
4. `cap_object_detection` - The system detects, recognises, segments or
   classifies objects, defects or people from sensor data.
5. `cap_instrument_reading` - The system reads or interprets instruments,
   gauges, dials, displays, meters or signage - the classic industrial
   inspection task.
6. `cap_target_tracking` - The system tracks a specific moving target or
   person over time. One-off detection is item 4, not this.
7. `cap_real_world_validation` - The integrated system was demonstrated in a
   physical, real-world setting, not only in simulation or on a laboratory
   floor. Set this to `true` only for evidence of a physical deployment or
   trial.

## Also extract, from this excerpt only

- `industry_sector_raw` - the industrial sector or setting the deployment
  targets, as the text words it (e.g. "underground mine", "electrical
  substation", "construction site", "oil and gas facility", "nuclear
  decommissioning", "chemical plant"). Copy the text's own wording. Do NOT map
  it to a category of your own; the controlled vocabulary is applied later, by a
  human, from these raw strings. Empty string if this excerpt does not say.
- `high_level_goal_raw` - the primary objective of the system in the authors'
  own words (e.g. "autonomous inspection of substation equipment", "mapping of
  underground drifts"). Empty string if this excerpt does not say.
- `ai_ml_solutions_raw` - the machine learning or AI methods used for
  perception, as named in the text (e.g. "YOLOv8", "PointNet++", "a CNN-based
  defect classifier"). Empty string if none appear in this excerpt.

## Rules that matter more than the items

**`found: false` means "not present in THIS EXCERPT". It does NOT mean "the
paper does not do this."** You are seeing part of a document. Never reason about
what the rest of the paper might contain, and never infer absence.

**Every `found: true` requires a verbatim quote, and it must be ONE UNBROKEN RUN
OF TEXT.** Copy the characters exactly as they appear in the excerpt: do not
paraphrase, correct, reorder, translate, or tidy up spacing and hyphenation.

Specifically:

- Do **not** stitch together two separated pieces of the text.
- Do **not** use "..." or any other ellipsis to skip over a middle part.
- If the supporting sentence is long, quote a shorter CONTIGUOUS span from
  inside it rather than a summary of the whole. Aim for under 40 words.
- If no single continuous span proves the item, set `found: false`.

Every quote is checked automatically against the source text. A quote that
cannot be located as a continuous run is flagged and sent for manual review, so
a stitched quote costs a human more time than a `found: false` would have.
An exact short quote always beats a broad inexact one.

**Distinguish what the system DOES from what the paper DISCUSSES.** Related
work, motivation and future work sections describe capabilities the system does
not have. If the quote you would give comes from such a passage, the answer is
`false`.

**Do not use knowledge from outside the excerpt.** If you happen to know what a
given robot platform is usually capable of, that is irrelevant: the question is
what this text states.

## Output format

Output ONE JSON object and nothing else. No prose before or after, no code
fence, no explanation.

{
  "cap_slam_mapping":           {"found": true,  "quote": "We build a 3D map of the tunnel online using a LiDAR-inertial odometry pipeline."},
  "cap_autonomous_navigation":  {"found": true,  "quote": "The robot then follows the planned route autonomously between inspection waypoints."},
  "cap_obstacle_avoidance":     {"found": false, "quote": ""},
  "cap_object_detection":       {"found": true,  "quote": "A YOLOv8 detector locates corrosion patches in the RGB stream."},
  "cap_instrument_reading":     {"found": true,  "quote": "The system reads the analogue pressure gauges and reports the needle angle."},
  "cap_target_tracking":        {"found": false, "quote": ""},
  "cap_real_world_validation":  {"found": true,  "quote": "Field trials were carried out at an operational substation over three days."},
  "industry_sector_raw":        "electrical substation",
  "high_level_goal_raw":        "autonomous inspection of substation equipment",
  "ai_ml_solutions_raw":        "YOLOv8"
}

Excerpt:
{record}
