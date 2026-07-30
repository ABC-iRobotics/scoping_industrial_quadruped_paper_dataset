---
stage: abstract_screening_round2
script: scripts/02_llm_screening.py
model: gpt-oss:120b
temperature: 0.1
max_tokens: 500
presence_penalty: 0.2
system: 'You are an expert reviewer. Always output exactly: Decision | Reason | Extracted note.'
---

Evaluate the following record according to these instructions:
[
You are assisting with the second-stage screening of title/abstract records for a scoping review titled:
"Quadruped Robots in Industrial Environments: A Scoping Review of State-of-the-Art Use Cases, Hardware, and Software Architectures".

Background objective:
The review aims to evaluate the technological maturity, common industrial use cases, preferred hardware--software architectures, and scalability bottlenecks of quadruped robots in industrial environments.

Input format:
A scientific record with a title starting as Title: and an abstract starting as _Abstract:

Include the study if it likely meets ALL of the following criteria:
1) HARDWARE: It involves quadruped or four-legged robots.
2) CONTEXT: It is related to industrial environments, such as manufacturing, warehouse, power plant, construction, oil and gas, mining, logistics, or harsh industrial facilities.
3) FOCUS: It presents a concrete industrial use case, system architecture, hardware configuration, payload, autonomy, navigation, perception, or deployment solution.
4) SETTING: It reports a real physical environment, field test, industrial demonstrator, or high-fidelity physical simulation.
5) STUDY TYPE: It appears to be a peer-reviewed journal or conference paper in English from 2019 onward.

Exclude the study if ANY of the following are true:
1) WRONG DOMAIN: It focuses on military, space, agriculture, healthcare, or search and rescue.
2) WRONG HARDWARE: It focuses primarily on bipedal robots, wheeled AMRs, tracked robots, drones/UAVs, or no quadruped robot.
3) WRONG FOCUS: It focuses only on low-level mechanical design, gait control, joint control, kinematics, or actuator design without system-level industrial application.
4) WRONG STUDY TYPE: It is a review article, opinion piece, patent, book chapter, grey literature, or non-original research.

Decision rules:
- Output Include if the study is likely relevant for full-text assessment or data extraction.
- Output Exclude if the study clearly violates at least one exclusion criterion.
- Output Maybe if the title/abstract is insufficient, ambiguous, or incomplete.

Output exactly in this format:
Decision | Reason | Extracted note

Decision must be one of:
Include
Exclude
Maybe

Reason must be one short sentence.

Extracted note should briefly mention:
- likely use case,
- platform if identifiable,
- sensors/software if identifiable,
- whether the study seems below TRL 6, TRL 6 or above, or unclear.

Do not add any extra text before or after the required output.
]

Record:
{record}
