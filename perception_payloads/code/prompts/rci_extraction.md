---
stage: rci_extraction
script: scripts/10_rci_extraction.py
model: gpt-oss:120b
temperature: 0.1
max_tokens: 1800
presence_penalty: null
system: "You are a meticulous technical data extractor working on a systematic review. You answer only with a single JSON object. You never guess: if you cannot quote the evidence verbatim from the excerpt in front of you, the answer is not found."
---

You are reading an EXCERPT from a research paper about a quadruped robot system
used in an industrial environment. The excerpt may begin or end mid-sentence,
and it may be only part of the paper.

For each item below, decide whether THIS EXCERPT contains the evidence, and if
it does, copy the exact sentence that proves it.

## The nine items

1. `rci1_platform_model` - The quadruped robot platform is named at model level
   (e.g. "Boston Dynamics Spot", "ANYmal C", "Unitree Go1"). A bare "a quadruped
   robot" or "a legged platform" does NOT count.
2. `rci2_sensors_model` - At least one optical sensor is named at model level
   (make and model, e.g. "Intel RealSense D455", "Ouster OS1-64", "FLIR A65").
   "an RGB-D camera" or "a LiDAR" names only the class and does NOT count.
3. `rci3_compute_model` - The onboard computing platform is named at model level
   (e.g. "NVIDIA Jetson AGX Xavier", "Intel NUC i7-8650U"). "an onboard
   computer", "an embedded GPU" does NOT count.
   **It must be the computer the ROBOT CARRIES.** A workstation, laptop,
   desktop or server used for offline processing, training, or simply for
   running the experiments does NOT count. If the text says only
   "experiments were performed on a system with an Intel Core i7..." and
   never ties that machine to the robot, the answer is NOT FOUND - however
   specific the model name is. When in doubt, it is not found.
4. `rci4_middleware_version` - A middleware or software framework is named AND a
   version or distribution is given (e.g. "ROS 2 Humble", "ROS Melodic",
   "PyTorch 1.13", "Ubuntu 20.04"). Naming "ROS" with no version does NOT count.
5. `rci5_algorithms_cited` - The core perception or navigation algorithm is named
   AND attributed, either by a literature citation or by a specific named method
   (e.g. "we use LIO-SAM [12]", "YOLOv8", "FAST-LIO2"). A generic "deep learning
   based detector" does NOT count.
6. `rci6_parameters` - At least one concrete operating parameter or configuration
   value is reported (e.g. "the LiDAR runs at 10 Hz", "voxel size 0.4 m",
   "images at 640x480", "learning rate 1e-4", "map resolution 5 cm").
7. `rci7_eval_environment` - The evaluation environment is described concretely
   enough that a reader could set up something comparable.
   **A positive requires at least one MEASURABLE QUANTITY** that fixes the
   scale of the setting: a dimension or distance ("a 120 m long underground
   drift", "an 11 m by 8 m arena"), a duration ("over 3 days"), or a count
   of assets or obstacles ("14 gauges", "two 1x1 m boxes and two cylinders").
   A bare "we tested in a real industrial environment", "at a substation" or
   "in our laboratory" does NOT count, however plausible it sounds.
   Whether the setting is real or simulated does **not** affect this item.
   Report that separately in `eval_environment_kind`.
8. `rci8_success_metric` - A QUANTITATIVE result for the goal task is reported
   (a number: accuracy, success rate, RMSE, detection rate, coverage, time).
   A qualitative "the system performed well" does NOT count.
9. `rci9_artifact` - Code, data or a trained model **produced by the authors of
   this paper** is stated to be publicly available, normally with a URL or a
   repository name.
   Two things look like this item and are NOT it:
   - **Someone else's artefact that the authors merely used.** "We build on the
     open-source X [12]", "ROS 2 Wrapper for Spot. Available online: <url>",
     "we forked the public Y repository" - all NOT found. The question is what
     THIS team released, not what it stood on.
   - **Publisher supplementary-material boilerplate.** "This article has
     supplementary downloadable material available at <doi>", "Supplementary
     material related to this article can be found online at <doi>", "the data
     are available in the supporting information" - standard publisher
     furniture, usually a video, saying nothing about code or data. NOT found,
     unless the text separately states what the supplement contains and it is
     code, data or a model.

## Also extract, from this excerpt only

- `optical_sensors_raw` - every optical sensor mentioned, as written in the text,
  comma separated. Empty string if none appear in this excerpt.
- `onboard_computer_raw` - the onboard computing hardware as written. Empty
  string if it does not appear in this excerpt.
- `sensor_specificity` - one of `model`, `modality`, `unspecified`, describing the
  MOST specific way an optical sensor is named anywhere in this excerpt.
  `model` = make and model given; `modality` = only the class ("a thermal
  camera"); `unspecified` = no optical sensor named in this excerpt.
- `compute_specificity` - the same three levels for the onboard computer.
- `eval_environment_kind` - one of `real`, `simulated`, `both`, `unclear`:
  where the evaluation described in THIS EXCERPT took place. `real` = physical
  hardware in a physical setting; `simulated` = a simulator or otherwise
  digital environment; `both` = this excerpt describes both; `unclear` = the
  excerpt does not say. This is a description of the evidence, not a
  judgement about the study's quality.

## Rules that matter more than the items

**`found: false` means "not present in THIS EXCERPT". It does NOT mean "the
paper does not report it."** You are seeing part of a document. Never reason
about what the rest of the paper might contain, and never infer absence.

**Every `found: true` requires a verbatim quote, and it must be ONE UNBROKEN
RUN OF TEXT.** Copy the characters exactly as they appear in the excerpt: do
not paraphrase, correct, reorder, translate, or tidy up spacing and hyphenation.

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

**Do not use knowledge from outside the excerpt.** If you happen to know which
compute platform a given robot usually ships with, that is irrelevant: the
question is what this text states.

## Output format

Output ONE JSON object and nothing else. No prose before or after, no code
fence, no explanation.

{
  "rci1_platform_model":    {"found": true,  "quote": "The platform used in this work is a Boston Dynamics Spot."},
  "rci2_sensors_model":     {"found": true,  "quote": "Perception relies on an Intel RealSense D455 and an Ouster OS1-64 LiDAR."},
  "rci3_compute_model":     {"found": false, "quote": ""},
  "rci4_middleware_version": {"found": true, "quote": "All modules were implemented in ROS 2 Humble on Ubuntu 22.04."},
  "rci5_algorithms_cited":  {"found": true,  "quote": "Localisation uses FAST-LIO2 [21]."},
  "rci6_parameters":        {"found": true,  "quote": "The LiDAR was operated at 10 Hz with a voxel size of 0.4 m."},
  "rci7_eval_environment":  {"found": false, "quote": ""},
  "rci8_success_metric":    {"found": true,  "quote": "The system achieved a detection rate of 94.2% across 137 gauges."},
  "rci9_artifact":          {"found": false, "quote": ""},
  "optical_sensors_raw":    "Intel RealSense D455, Ouster OS1-64",
  "onboard_computer_raw":   "",
  "sensor_specificity":     "model",
  "compute_specificity":    "unspecified",
  "eval_environment_kind":  "real"
}

Excerpt:
{record}
