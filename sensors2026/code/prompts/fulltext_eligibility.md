---
stage: fulltext_eligibility
script: scripts/13_fulltext_eligibility.py
model: gpt-oss:120b
temperature: 0.1
max_tokens: 1200
presence_penalty: null
system: "You are a careful scoping-review screener. You apply the eligibility criteria exactly as written and answer only with a single JSON object. Your decision is a recommendation; a human reviewer makes the final inclusion decision."
---

You are screening ONE document at the full-text stage of a scoping review of
quadruped robots in industrial settings. The document has already passed
title-and-abstract screening. You are given its bibliographic record and the
evidence that was collected from its ENTIRE full text, chunk by chunk. Every
quote below is verbatim from the document.

## Eligibility criteria (PCC) - apply exactly these, add nothing

| Element | Include | Exclude |
|---|---|---|
| **Population** | Quadruped or four-legged robots capable of autonomous or semi-autonomous locomotion: commercial platforms (Boston Dynamics Spot, ANYbotics ANYmal, Unitree Go, and similar) and research prototypes clearly identified as quadrupeds. | Bipedal, humanoid, wheeled, tracked or aerial platforms. Simulation-only studies, unless the simulation is explicitly validated on physical quadruped hardware. |
| **Concept** | A concrete industrial task - inspection, mapping, logistics, safety monitoring - together with a description of the robot's hardware configuration. | Component-level work only: actuator design, gait optimisation, joint mechanics, low-level control, kinematics, with no demonstrated industrial use case. Purely theoretical algorithm or architecture papers with no implementation on a quadruped. |
| **Context** | Deployment or experimental validation in an industrial setting: plants, warehouses, construction sites, power plants, mines, oil-and-gas facilities, other harsh industrial environments. High-fidelity industrial simulations qualify only with hardware-in-the-loop or hardware-based verification and faithful reproduction of real constraints (dust, vibration, dynamic obstacles, complex layouts). | Non-industrial domains: military, space, agriculture, healthcare, disaster response, search-and-rescue. Laboratory-only experiments not emulating industrial conditions. |

Additional limits: **English language**, **2019 onward**. Excluded publication
types: conference or workshop abstracts without full papers, grey literature,
technical reports, patents, theses, and review articles.

A document is included only if it meets ALL of Population, Concept and Context
and none of the exclusions.

## How the Context criterion is applied (as in round 1)

This is how the criteria above were applied in the first review round, and it
governs how you read them (protocol amendment A4):

- **A laboratory validation of an industrial task QUALIFIES.** If the paper
  addresses a concrete industrial task or use case (inspection of a plant,
  mapping of a mine, monitoring of a construction site, and so on) and
  demonstrates it on physical quadruped hardware, it meets Context even when
  the experiments took place in a laboratory, a mock-up, a test facility or a
  generic indoor space. Whether the validation was in the field or in the lab
  is recorded later as a separate variable; it is NOT a reason to exclude.
- **"Laboratory-only experiments not emulating industrial conditions" excludes
  only work with no industrial task or use case at all** - for example a
  locomotion or control experiment on a lab floor whose only link to industry
  is a sentence of motivation.
- **Simulation-only work stays excluded** unless it is validated on physical
  quadruped hardware, exactly as the criteria state.
- **A single passing mention of "industrial settings" is not an industrial
  task.** The industrial task must be what the system is built and evaluated
  for.

## Exclusion reasons - choose exactly one if you exclude

- `non_quadruped_platform` - the main platform is not a quadruped.
- `no_industrial_use_case` - no concrete industrial task, or no industrial
  setting, or a non-industrial domain, or laboratory-only experiments not
  emulating industrial conditions.
- `low_level_control_only` - component-level work only (actuators, gait,
  joints, low-level control, kinematics), or a purely theoretical algorithm or
  architecture with no implementation on a quadruped.
- `simulation_only` - evaluated in simulation only, without validation on
  physical quadruped hardware.
- `not_primary_study_or_excluded_type` - proceedings front matter or digest,
  abstract without full paper, grey literature, technical report, patent,
  thesis, or review article.
- `non_english` - not written in English.
- `duplicate_or_companion_report` - another report of a study already in the
  corpus. Use this ONLY if the note below tells you a candidate companion
  exists AND the evidence shows it is the same work.
- `other` - any other reason; explain in `rationale`.

If several apply, choose the first one in this list order.

## Decision values

- `include` - all criteria met.
- `exclude` - at least one exclusion clearly applies; give the reason.
- `unclear` - the evidence is insufficient or contradictory. Prefer `unclear`
  over a guess; the human reviewer will read the full text.

## Evidence rules

Base the decision ONLY on the record and the evidence below. Do not use outside
knowledge about any robot or paper. `quote` must be copied verbatim from ONE of
the evidence quotes below (or from the title/abstract) - the single quote that
best supports your decision. For `include`, quote the industrial task or
setting evidence.

## Output format

Output ONE JSON object and nothing else. No prose, no code fence.

{
  "decision": "exclude",
  "exclusion_reason": "simulation_only",
  "quote": "All experiments were carried out in the Gazebo simulator.",
  "rationale": "Quadruped inspection task, but evaluated only in simulation with no hardware validation."
}

For `include` set `"exclusion_reason": ""`.

{record}
