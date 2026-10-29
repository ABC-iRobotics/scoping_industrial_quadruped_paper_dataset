---
stage: data_extraction
script: scripts/03_llm_extraction.py
model: gpt-oss:120b
temperature: null
max_tokens: null
presence_penalty: null
system: You are an expert technical data extractor. Follow the output format strictly.
---

You are analyzing a research paper about a quadruped robot system used in an industrial environment.
Your task is to extract and describe the key technical specifications and capabilities from the full text.

Extract the following information from the paper:
1. Robot platform: What specific quadruped robot platform was used? (e.g., Boston Dynamics Spot, Ghost Robotics, ANYmal, custom, etc.)
2. Onboard Compute: What computing system is used onboard? (e.g., Intel NUC, NVIDIA Jetson, Raspberry Pi, etc.)
3. Optical Sensors: What cameras/optical sensors does it have? (e.g., RGB camera, stereo, LiDAR, thermal, etc.)
4. High-level goal: What is the primary objective of the system? (e.g., visual inspection, navigation, measurement, etc.)
5. AI / ML solutions: What machine learning or AI techniques are used? (e.g., computer vision, neural networks, semantic segmentation, etc.)

Then answer YES or NO for these:
6. SLAM/mapping? : Does the system use SLAM or mapping algorithms?
7. Autonomous navigation? : Does it have autonomous navigation capabilities?
8. Obstacle Avoidance : Does it perform obstacle avoidance?
9. Object detection? : Does it use object detection?
10. Instrument reading? : Can it read/interpret instruments or data displays?
11. Target tracking? : Does it track specific targets or objects?
12. environmental challenges? : Does the paper discuss real environmental challenges (noise, lighting, etc.)?
13. Real-world validation? : Is the system tested in real-world industrial environments (not only simulations)?
14. Reproducable? : Is the work reproducible from the description (sufficient details on hardware/software)?

Finally:
15. Success metric for goal task?: Describe how successfully the goal was achieved. What metrics were used?

CRITICAL INSTRUCTIONS FOR OUTPUT FORMAT:
Output EXACTLY ONE LINE of text containing the 15 extracted values separated by the pipe (|) character.
DO NOT output header names. DO NOT output introductory or concluding text. ONLY the values.

Example of the REQUIRED output format:
Boston Dynamics Spot | Intel NUC | LiDAR, RGB, Thermal | Visual inspection of valves | CNN, YOLOv5 | Yes | Yes | Yes | Yes | Yes | No | Yes | Yes | Yes | 95% accuracy in valve detection


Paper full text:
{record}
