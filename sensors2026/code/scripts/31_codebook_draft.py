"""
Stage 31 - draft the controlled vocabulary, for row-by-row human sign-off.

WHAT THIS IS AND IS NOT
    It is a proposal. Every raw string gets a candidate class and, next to it,
    the exact rule that produced the candidate - so the reviewer is checking a
    stated reason, not a machine's opinion. `final_class` starts empty and is
    the only column the analysis reads.

    Nothing downstream is valid until that column is filled. This step stays a
    human decision on purpose: it is ~330 short strings rather than 88 full
    texts, an afternoon rather than a month, and it is the step where one wrong
    call propagates into every figure.

WHY THE RULE IS RECORDED, NOT JUST THE CLASS
    A codebook whose mappings cannot be re-derived is a lookup table, and a
    lookup table cannot classify the next record. The SISY release had to
    reconstruct exactly this, because the original mapping was not preserved.
    The published codebook is raw string -> class -> rule, and this file is
    where the third column comes from.

MULTI-LABEL BY CONSTRUCTION
    One sensor string can be several classes at once: "RealSense D455" is both
    a depth sensor and an RGB camera, and a study carrying it counts in both.
    Order matters in the rule list only for which rule is *reported* first; all
    matching classes are kept.

INPUTS
    work/rci_A_all_records.xlsx    optical_sensors_raw, onboard_computer_raw
    work/cap_A_all_records.xlsx    industry_sector_raw
    (baseline + included round 2, from 38_combine_records.py)

OUTPUTS
    work/codebook_sensors.xlsx
    work/codebook_compute.xlsx
    work/codebook_sector.xlsx

USAGE
    python scripts/31_codebook_draft.py
"""

from __future__ import annotations

import argparse
import collections
import re
from pathlib import Path

import pandas as pd

from _common import WORK_DIR

# Each rule is (class, human-readable rule text, pattern). The rule text is what
# the reviewer reads and what the published codebook prints; it must say what
# the pattern actually does, not what it was meant to do.
SENSOR_RULES = [
    ("lidar", "names a LiDAR, laser scanner, or a known LiDAR vendor",
     r"lidar|laser scanner|laser range|velodyne|ouster|livox|rplidar|hokuyo|robosense|hesai|sick\b|faro|\btls\b|terrestrial laser|leica\s*(rtc|blk)|\bos[0-2]-?\d+|vlp-?\d+|hdl-?\d+"),
    ("thermal_ir", "names thermal or infrared imaging, or a thermal vendor",
     r"thermal|infrared|\bir\b|lwir|flir|thermograph|radiomet"),
    ("depth_rgbd", "names a depth or RGB-D sensor, or a depth-camera product line",
     r"rgb-?d|depth camera|depth sensor|time.?of.?flight|\btof\b|realsense\s*d\d|kinect|azure kinect|structure sensor|astra|femto"),
    ("stereo", "names stereo imaging or a stereo camera product",
     r"stereo|\bzed\b|zed\s*(2|mini|x)|bumblebee|multi.?camera rig"),
    ("event_camera", "names an event or neuromorphic camera",
     r"event camera|event-based|dvs\b|davis\s*\d|prophesee"),
    ("rgb_camera", "names a camera without a more specific modality above",
     r"rgb|colou?r camera|cameras?\b|webcam|gopro|fisheye|wide.?angle|monocular|pan.?tilt.?zoom|\bptz\b"),
]

COMPUTE_RULES = [
    ("embedded_gpu", "names an NVIDIA Jetson-class embedded GPU module",
     r"jetson|xavier|orin\b|tegra|\btx2\b|jetson nano"),
    ("x86_mini_pc", "names a small-form-factor x86 machine",
     r"\bnuc|up board|up\s*squared|mini.?pc|brix|fitlet|zotac"),
    ("laptop_workstation", "names a laptop, desktop or workstation-class CPU or GPU",
     r"laptop|notebook|workstation|desktop|core\s*i[3579]|\bi[3579]-\d{3,5}|\bi[3579]\b|ryzen|threadripper|\brtx\b|\bgtx\b|xeon"),
    ("sbc_microcontroller", "names a single-board computer or a microcontroller",
     r"raspberry|odroid|beaglebone|arduino|stm32|jetson nano dev|latte panda|\bmcu\b"),
    ("vendor_integrated", "names the robot vendor's own onboard computer",
     r"spot\s*core|anymal.*(computer|pc)|unitree.*(computer|pc)|onboard pc of"),
]

SECTOR_RULES = [
    ("construction", "names construction, building sites or civil works",
     r"construction|building site|civil engineering|building interior|jobsite|job site"),
    ("mining", "names mining or underground extraction",
     r"mining|\bmine\b|mines\b|underground drift|tunnel|quarry|subterranean"),
    ("energy_power", "names power generation, transmission or substations",
     r"power plant|substation|electrical grid|energy|turbine|transformer|photovoltaic|solar (farm|plant)|wind farm"),
    ("nuclear", "names nuclear facilities or decommissioning",
     r"nuclear|radioactive|reactor|decommission"),
    ("oil_gas_chemical", "names oil, gas, refining or chemical process plant",
     r"oil|gas (facility|plant|field)|refiner|petrochem|chemical plant|distillation|offshore platform"),
    ("manufacturing", "names manufacturing, factories or production lines",
     r"manufactur|factory|factories|production line|assembly line|shop floor|plant floor"),
    ("logistics_warehouse", "names warehousing, logistics or material handling",
     r"warehouse|logistic|distribution cent|intralogistic|material handling"),
    ("general_industrial", "names an industrial setting without naming a sector",
     r"industrial (environment|site|setting|facility|facilities|plant|scenario|application)|industry\b|industrial\b"),
]

FIELDS = {
    "sensors": ("work/rci_A_all_records.xlsx", "optical_sensors_raw", SENSOR_RULES),
    "compute": ("work/rci_A_all_records.xlsx", "onboard_computer_raw", COMPUTE_RULES),
    "sector": ("work/cap_A_all_records.xlsx", "industry_sector_raw", SECTOR_RULES),
}


def classify(value: str, rules) -> tuple[str, str]:
    """Return (classes, rules that fired) - both semicolon separated, both may be empty."""
    classes, fired = [], []
    for name, rule_text, pattern in rules:
        if re.search(pattern, value, re.I):
            classes.append(name)
            fired.append(rule_text)
    return "; ".join(classes), "; ".join(fired)


def build(path: Path, field: str, rules) -> pd.DataFrame:
    frame = pd.read_excel(path)
    if field not in frame.columns:
        return pd.DataFrame()

    mentions = collections.Counter()
    studies: dict[str, set] = collections.defaultdict(set)
    key = "Pdf name"
    for _, row in frame.iterrows():
        raw = row.get(field)
        if pd.isna(raw):
            continue
        # a comma between digits is a thousands separator ("1,000 sf"), not a list separator
        for part in re.split(r",(?!\d)", str(raw)):
            part = " ".join(part.split())
            if not part:
                continue
            lowered = part.lower()
            mentions[lowered] += 1
            studies[lowered].add(row.get(key))

    rows = []
    for string, count in mentions.most_common():
        classes, fired = classify(string, rules)
        rows.append({
            "raw_string": string,
            "mentions": count,
            "n_studies": len(studies[string]),
            "proposed_class": classes,
            "rule_fired": fired,
            "final_class": "",     # the human fills this; the analysis reads only this
            "note": "",
        })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--field", choices=list(FIELDS) + ["all"], default="all")
    args = parser.parse_args()

    names = list(FIELDS) if args.field == "all" else [args.field]
    for name in names:
        rel, field, rules = FIELDS[name]
        path = Path(rel)
        if not path.is_absolute():
            path = WORK_DIR.parent / rel
        if not path.exists():
            print(f"{name}: input missing ({path})")
            continue

        frame = build(path, field, rules)
        if frame.empty:
            print(f"{name}: no values found in {field}")
            continue

        out = WORK_DIR / f"codebook_{name}.xlsx"
        if out.exists():
            old = pd.read_excel(out)
            if old.get("final_class", pd.Series(dtype=str)).fillna("").astype(str).str.strip().ne("").any():
                raise SystemExit(f"ERROR: {out} already holds signed-off classes; not overwriting.")
            raise SystemExit(f"ERROR: {out} exists; archive it first.")
        frame.to_excel(out, index=False)

        unclassified = frame[frame["proposed_class"] == ""]
        multi = frame[frame["proposed_class"].str.contains(";", na=False)]
        print(f"{name}: {len(frame)} distinct strings, {int(frame['mentions'].sum())} mentions")
        print(f"    proposed a class for {len(frame) - len(unclassified)}")
        print(f"    multi-class          {len(multi)}")
        print(f"    NO rule matched      {len(unclassified)}  <- these need a human first")
        if len(unclassified):
            head = ", ".join(unclassified["raw_string"].head(6))
            print(f"      e.g. {head}")
        print(f"    -> {out.name}\n")


if __name__ == "__main__":
    main()
