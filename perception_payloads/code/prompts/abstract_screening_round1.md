---
stage: abstract_screening_round1
script: scripts/02_llm_screening.py
model: gpt-oss:120b
temperature: 0.1
max_tokens: 800
presence_penalty: 0.6
system: You are an expert evaluator. Always output 'Letter | Explanation'.
---

Evaluate the following text according to these instructions: [
You are an expert researcher screening title/abstract records for a scoping review titled: "Quadruped Robots in Industrial Environments: A Scoping Review of State-of-the-Art Use Cases, Hardware, and Software Architectures".

Background Objective: The research aims to evaluate the technological maturity, common use cases (e.g., visual inspection), preferred hardware-software architectures (e.g., ROS, AI navigation), and scalability bottlenecks of quadruped robots in industrial settings.

Input format: A scientific record with a title starting as Title: and an Abstract starting as _ Abstract:

Include (Y) only if ALL of the following criteria are met based on the title/abstract:
1) HARDWARE: Involves quadruped or four-legged robots.
2) CONTEXT: Set in an industrial environment (e.g., manufacturing, warehouse, power plant, construction, oil and gas, mining).
3) FOCUS: Presents a concrete industrial use-case, system architecture, hardware configuration, or autonomy/navigation solution.
4) SETTING: Mentions or implies field testing in a real physical environment or a high-fidelity physical simulation.

Exclude (N) if ANY of the following are true:
1) WRONG DOMAIN: The application is for military, space, agriculture, healthcare, or search and rescue (SAR).
2) WRONG HARDWARE: The study focuses primarily on bipedal, wheeled (AMR), tracked platforms, or drones/UAVs, with no significant quadruped involvement.
3) WRONG FOCUS: The study is solely focused on low-level mechanical design, joint control, or kinematics without demonstrating a system-level industrial application.
4) WRONG STUDY TYPE: The text clearly indicates it is a review article, opinion piece, patent, book chapter, or grey literature (not an original research study).

Uncertain (U): Use only if you cannot determine from the title/abstract whether to output Y or N, because crucial information regarding the hardware, context, or focus is missing or too vague.

Output format: Start your response with the decision letter (Y, N, or U), then add a separator ' | ', and then write a 1-sentence explanation of which specific criteria led to this decision.
Example: N | Excluded based on Exclusion Criteria 1 because the application domain is military.
].

Text:
{record}
