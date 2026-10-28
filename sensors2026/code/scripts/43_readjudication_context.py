"""
Stage 43 - re-adjudicate the adjudicated "yes" decisions with context.

WHY THIS EXISTS
    The first adjudication (stage 30) showed each disagreement as the quote a
    model offered for "yes" against a bare "no". On the 23 validation studies,
    P.Z.'s adjudicated code matched her own blind full-text code in only 19 of
    34 cases, and 14 of the 15 mismatches were adjudicated "yes" where the blind
    reading said "no" (validation_final_vs_human.csv). A quote shows what speaks
    for a positive code; what speaks against it - "in simulation", "with a
    Vicon system", "teleoperated" - is elsewhere in the paper and never reached
    the adjudicator. That is automation bias with a mechanism, and it inflates
    exactly the items the paper reports as prevalences.

WHAT THIS SHOWS FOR EACH CASE
    - the rubric text of the item, from the prompt (as stage 30 does);
    - the supporting quote, located in the full text, with about 1,200
      characters on either side, so the sentence is read where it stands;
    - every passage in the paper that matches the item's counter-evidence
      cues (simulation, laboratory, teleoperation, a citation of other work,
      ...), each with a short window. These are search hits, not judgements;
      most will be irrelevant, and that is fine.

SCOPE
    Every adjudicated case whose first decision was "yes", except studies in
    the validation subsample: their final codes come from the blind human
    coding (42_build_final.py), so re-deciding them here would change nothing.

OUTPUTS
    work/readjudication_yes.html   the reading copy
    work/readjudication_yes.xlsx   one row per case: first_decision,
                                   final_code (empty, P.Z. fills yes/no), reason
    42_build_final.py reads final_code from here where it is filled, and it
    replaces the first decision for that case.

USAGE
    python scripts/43_readjudication_context.py
"""
from __future__ import annotations

import html
import importlib.util
import re
import sys
from pathlib import Path

import pandas as pd

from _common import PDF_DIR, WORK_DIR, cell_text, pdf_text

SCRIPTS = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("adj", SCRIPTS / "30_adjudication_package.py")
_adj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_adj)

OUT_HTML = WORK_DIR / "readjudication_yes.html"
OUT_XLSX = WORK_DIR / "readjudication_yes.xlsx"
VALIDATION = WORK_DIR / "validation" / "validation_coding_baseline_v2.xlsx"
ROUND2_PDF = WORK_DIR / "pdf_round2"
WINDOW = 1200
CUE_WINDOW = 220
MAX_CUES = 8

# Counter-evidence cues per item: words near which a positive code tends to
# fall apart. They widen what the reader sees; they decide nothing.
CUES = {
    "rci1_platform_model": r"quadruped|legged robot|platform",
    "rci2_sensors_model": r"camera|lidar|sensor",
    "rci3_compute_model": r"on-?board|computer|laptop|workstation|offboard|remote|ground station|server|control box",
    "rci4_middleware_version": r"\bROS\b|ROS ?2|melodic|noetic|humble|foxy|galactic|kinetic|ubuntu",
    "rci5_algorithms_cited": r"we (use|adopt|employ|apply)|based on|\[\d+\]",
    "rci6_parameters": r"parameter|set to|threshold|resolution|frequency|\bHz\b",
    "rci7_eval_environment": r"\d+(\.\d+)? ?(m|mm|cm|s|min|h)\b|area|room|corridor|site",
    "rci8_success_metric": r"accuracy|success rate|error|RMSE|precision|recall|%",
    "rci9_artifact": r"github|available at|open[- ]source|repository|dataset|supplementary",
    "cap_slam_mapping": r"SLAM|map(ping)?\b|localization|localisation|pre-?built|prior map|given map",
    "cap_autonomous_navigation": r"teleop|tele-op|remote(ly)? control|joystick|operator|manual|autonom|waypoint|planner|path planning",
    "cap_obstacle_avoidance": r"obstacle|collision|avoid|stair|step over",
    "cap_object_detection": r"detect|segment|classif|recogni|YOLO|CNN",
    "cap_instrument_reading": r"gauge|meter|dial|read(ing)?|display|indicator",
    "cap_target_tracking": r"track|follow",
    "cap_real_world_validation": r"simulat|gazebo|isaac|laborator|\blab\b|vicon|optitrack|motion capture|test ?bed|mock-?up|arena|field|on-?site|deploy|pilot",
}


def _norm_index(text: str) -> tuple[str, list[int]]:
    """Lower-cased alphanumerics of `text`, and each one's position in `text`."""
    chars, where = [], []
    for i, ch in enumerate(text):
        if ch.isalnum():
            chars.append(ch.lower())
            where.append(i)
    return "".join(chars), where


def locate(quote: str, text: str, norm: str, where: list[int]) -> int | None:
    q = re.sub(r"[^a-z0-9]", "", str(quote).lower())
    if len(q) < 12:
        return None
    pos = norm.find(q)
    if pos < 0:
        pos = norm.find(q[:60])
    return where[pos] if pos >= 0 else None


def pdf_for(study: str) -> Path:
    p = PDF_DIR / f"{study}.pdf"
    return p if p.exists() else ROUND2_PDF / f"{study}.pdf"


def main() -> None:
    for out in (OUT_HTML, OUT_XLSX):
        if out.exists():
            raise SystemExit(f"ERROR: {out} exists; archive it first, it may hold decisions.")

    validated = set(pd.read_excel(VALIDATION)["record_id"].astype(str))
    defs = {**_adj.item_definitions("rci_extraction.md"), **_adj.item_definitions("capability_extraction.md")}

    frames = [pd.read_excel(WORK_DIR / f"adjudication_{t}.xlsx") for t in ("rci", "cap")]
    adj = pd.concat(frames, ignore_index=True)
    first = adj["final_code"].astype(str).str.strip().str.lower()
    cases = adj[(first == "yes") & ~adj["pdf_name"].astype(str).isin(validated)].copy()
    cases = cases.sort_values(["item", "pdf_name"]).reset_index(drop=True)
    print(f"{len(cases)} adjudicated 'yes' cases outside the validation subsample")

    texts: dict[str, tuple[str, str, list[int]]] = {}
    parts = [f"<!doctype html><meta charset='utf-8'><title>Re-adjudication with context</title>"
             "<style>body{font:15px/1.55 system-ui,sans-serif;max-width:70rem;margin:0 auto;padding:2rem;color:#111}"
             "h2{margin-top:2.6rem;border-top:2px solid #ddd;padding-top:1rem}.def{background:#f6f6f4;padding:.5rem .8rem;"
             "border-left:3px solid #ccc;color:#333}.ctx{white-space:pre-wrap;background:#fbfbf8;padding:.6rem;border:1px solid #eee}"
             "mark{background:#ffe58a}.cue{font-size:.88rem;color:#333;margin:.25rem 0;padding-left:.6rem;border-left:2px solid #c9d6e8}"
             "b.cw{background:#dbe7f5;font-weight:400}.meta{color:#666;font-size:.85rem}</style>"
             "<h1>Re-adjudication with context</h1>"
             f"<p>{len(cases)} cases that were first decided <b>yes</b>. For each, read the quote where it stands and the "
             "counter-evidence hits below it, then record <b>yes</b> or <b>no</b> and a one-line reason in the xlsx row with the "
             "same number. Decide against the rubric, not against the first decision.</p>"]
    rows = []
    for n, r in enumerate(cases.itertuples(), start=1):
        study, item = str(r.pdf_name), str(r.item)
        if study not in texts:
            t = pdf_text(pdf_for(study))
            texts[study] = (t, *_norm_index(t))
        text, norm, where = texts[study]
        quote = cell_text(r.A_quote) or cell_text(r.B_quote)
        pos = locate(quote, text, norm, where) if quote else None
        parts.append(f"<h2 id='c{n}'>#{n} &nbsp; {html.escape(study)} &nbsp;&middot;&nbsp; {html.escape(item)}</h2>"
                     f"<p class='meta'>pass A: {html.escape(str(r.pass_A))} &middot; pass B: {html.escape(str(r.pass_B))} "
                     f"&middot; first decision: yes &mdash; {html.escape(cell_text(r.reason))}</p>"
                     f"<p class='def'>{html.escape(defs.get(item, ''))}</p>")
        if pos is not None:
            a, b = max(0, pos - WINDOW), min(len(text), pos + len(quote) + WINDOW)
            q_end = min(len(text), pos + len(quote))
            parts.append("<div class='ctx'>" + html.escape(text[a:pos]) + "<mark>" + html.escape(text[pos:q_end])
                         + "</mark>" + html.escape(text[q_end:b]) + "</div>")
        else:
            parts.append(f"<div class='ctx'><i>quote not located in the text layer:</i> {html.escape(quote)}</div>")
        hits = []
        for m in re.finditer(CUES.get(item, r"$^"), text, re.I):
            if pos is not None and abs(m.start() - pos) < WINDOW:
                continue
            if hits and m.start() - hits[-1] < CUE_WINDOW:
                continue
            hits.append(m.start())
        parts.append(f"<p class='meta'>{len(hits)} counter-evidence hit(s) elsewhere in the paper"
                     + (f", first {MAX_CUES} shown" if len(hits) > MAX_CUES else "") + ":</p>")
        for h in hits[:MAX_CUES]:
            a, b = max(0, h - CUE_WINDOW), min(len(text), h + CUE_WINDOW)
            frag = html.escape(text[a:b])
            frag = re.sub(f"({CUES[item]})", r"<b class='cw'>\1</b>", frag, flags=re.I)
            parts.append(f"<div class='cue'>&hellip;{frag}&hellip;</div>")
        rows.append({"n": n, "pdf_name": study, "item": item, "pass_A": r.pass_A, "pass_B": r.pass_B,
                     "first_decision": "yes", "first_reason": cell_text(r.reason),
                     "final_code": "", "reason": ""})

    OUT_HTML.write_text("".join(parts), encoding="utf-8")
    pd.DataFrame(rows).to_excel(OUT_XLSX, index=False)
    print(pd.DataFrame(rows)["item"].value_counts().to_string())
    print(f"written {OUT_HTML.name}, {OUT_XLSX.name}")


if __name__ == "__main__":
    sys.exit(main())
