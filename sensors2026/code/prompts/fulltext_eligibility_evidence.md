---
stage: fulltext_eligibility_evidence
script: scripts/13_fulltext_eligibility.py
model: gpt-oss:120b
temperature: 0.1
max_tokens: 1800
presence_penalty: null
system: "You are a meticulous evidence collector working on a scoping review. You answer only with a single JSON object. You never guess: if you cannot quote the evidence verbatim from the excerpt in front of you, the answer is not found."
---

You are reading an EXCERPT from a document retrieved for full-text screening in
a scoping review of quadruped robots used in industrial settings. The excerpt
may begin or end mid-sentence, and it may be only part of the document.

You do NOT decide eligibility here. You only collect evidence from THIS EXCERPT
for each question below, so that a later step can decide.

## The questions

1. `quadruped_platform` - The system studied is a quadruped / four-legged robot
   (a commercial platform such as Boston Dynamics Spot, ANYbotics ANYmal,
   Unitree Go, or a research prototype clearly identified as a quadruped).
2. `other_platform` - The main platform studied is NOT a quadruped: bipedal,
   humanoid, wheeled, tracked, aerial, a crawler without legs, or a
   non-quadruped legged robot (e.g. hexapod).
3. `industrial_task` - The system performs a concrete industrial task, such as
   inspection, mapping, logistics or safety monitoring.
4. `industrial_setting` - The system is deployed or experimentally validated in
   an industrial setting: plants, warehouses, construction sites, power plants,
   mines, oil-and-gas facilities, or other harsh industrial environments.
5. `non_industrial_domain` - The application domain is military, space,
   agriculture, healthcare, disaster response or search-and-rescue.
6. `hardware_validation` - The work is implemented or validated on physical
   quadruped hardware (not only in a simulator).
7. `simulation_only` - The evaluation is stated to be in simulation only.
8. `component_level_only` - The contribution is component-level work only:
   actuator design, gait optimisation, joint mechanics, low-level control or
   kinematics, with no demonstrated industrial use case.
9. `hardware_configuration` - The robot's hardware configuration (sensors,
   compute, payload) is described.
10. `excluded_document_type` - The document is NOT a full primary research
    paper: conference proceedings front matter or a digest/programme, an
    abstract without a full paper, grey literature, a technical report, a
    patent, a thesis, or a review article.

## Also report, from this excerpt only

- `language` - the language the excerpt is written in (e.g. "English").

## Rules

**`found: false` means "not present in THIS EXCERPT".** Never reason about the
rest of the document.

**Every `found: true` requires a verbatim quote, ONE UNBROKEN RUN OF TEXT.**
Copy the characters exactly. Do not stitch pieces together, do not use "...",
do not paraphrase. Aim for under 40 words. If no single continuous span proves
the point, set `found: false`.

**Distinguish what THIS work does from what it DISCUSSES.** Related work,
motivation and future-work passages describe other systems or plans. A quote
from such a passage does not count as evidence for what this work does.

**Do not use knowledge from outside the excerpt.**

## Output format

Output ONE JSON object and nothing else. No prose, no code fence.

{
  "quadruped_platform":     {"found": true,  "quote": "We deploy a Boston Dynamics Spot equipped with a thermal camera."},
  "other_platform":         {"found": false, "quote": ""},
  "industrial_task":        {"found": true,  "quote": "The robot autonomously inspects analogue gauges along a fixed route."},
  "industrial_setting":     {"found": true,  "quote": "Field trials took place at an operational offshore platform."},
  "non_industrial_domain":  {"found": false, "quote": ""},
  "hardware_validation":    {"found": true,  "quote": "All experiments were conducted on the physical robot."},
  "simulation_only":        {"found": false, "quote": ""},
  "component_level_only":   {"found": false, "quote": ""},
  "hardware_configuration": {"found": true,  "quote": "The payload comprises an Ouster OS1-64 LiDAR and a Jetson AGX Orin."},
  "excluded_document_type": {"found": false, "quote": ""},
  "language": "English"
}

Excerpt:
{record}
