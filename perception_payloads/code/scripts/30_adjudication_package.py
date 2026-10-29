"""
Stage 30 - build the adjudication package: every inter-pass disagreement, ready to decide.

WHAT THE HUMAN ACTUALLY HAS TO DO
    The two passes disagree on 128 (study, item) pairs across both instruments.
    Each one needs a person to decide which pass is right. That decision is
    cheap only if the evidence is in front of them: with both quotes on screen,
    most cases resolve in seconds, because one pass usually quotes something
    that plainly does or does not satisfy the item.

    Without this package the same work means opening a PDF, finding the passage,
    and reconstructing what each model saw - minutes per case instead of
    seconds, 128 times over.

WHY BOTH AN XLSX AND AN HTML
    They are for different moments. The HTML is for reading and deciding: the
    two quotes sit side by side under the item's own wording, grouped by item so
    the reader calibrates on one question at a time rather than switching
    between nine. The xlsx is the form and, once filled, the adjudication log
    itself - study, item, pass-1 code, pass-2 code, final code, reason - which
    the protocol commits to publishing as supplementary material.

READING ORDER IS BY ITEM, NOT BY STUDY
    Judging "is this evaluation environment described concretely enough" twenty
    times in a row is one calibrated decision repeated. Judging nine different
    questions about one paper, then nine about the next, is nine decisions
    re-derived each time, and it drifts.

WHAT IT DELIBERATELY DOES NOT DO
    It does not guess the answer, rank the passes, or mark one as likely
    correct. A suggested default is the fastest possible route to rubber-
    stamping a machine's opinion, which is the one thing this design exists to
    avoid. Where a quote is missing, that absence is shown plainly - a negative
    has no quote by construction, and that is often exactly the information
    needed.

INPUTS
    work/<tag>_A_records.xlsx, work/<tag>_B_records.xlsx  for tag in rci, cap
    the prompt files, for the item wording shown to the reader

OUTPUTS
    work/adjudication_<tag>.xlsx    the form, and afterwards the log
    work/adjudication_<tag>.html    the reading view

USAGE
    python scripts/30_adjudication_package.py
    python scripts/30_adjudication_package.py --tag rci
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import pandas as pd

from _common import PROMPTS_DIR, WORK_DIR, cell_text

INSTRUMENTS = {
    "rci": {
        "prefix": "rci",
        "prompt": "rci_extraction.md",
        "exclude": {"rci_total"},
        "title": "Reporting Completeness Index",
    },
    "cap": {
        "prefix": "cap_",
        "prompt": "capability_extraction.md",
        "exclude": {"n_capabilities"},
        "title": "Capabilities and context",
    },
}

EVIDENCE_SUFFIXES = ("__quote", "__offset", "__verified")


def item_columns(frame: pd.DataFrame, prefix: str, exclude: set[str]) -> list[str]:
    return [
        c for c in frame.columns
        if c.startswith(prefix) and c not in exclude and not c.endswith(EVIDENCE_SUFFIXES)
    ]


def item_definitions(prompt_name: str) -> dict[str, str]:
    """
    Pull each item's own wording out of the prompt file.

    The reader is deciding against the rubric, so the rubric has to be on the
    page. Taking it from the prompt rather than restating it here means the two
    can never drift apart - and if they did, the wrong one would be the copy.
    """
    path = PROMPTS_DIR / prompt_name
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    definitions: dict[str, str] = {}
    # Items are numbered list entries opening with `item_name`.
    pattern = re.compile(r"^\d+\.\s+`([a-z0-9_]+)`\s*-\s*(.+?)(?=^\d+\.\s+`|^##)",
                         re.S | re.M)
    for match in pattern.finditer(text):
        body = " ".join(match.group(2).split())
        definitions[match.group(1)] = body
    return definitions


def collect(tag: str, spec: dict, suffix: str = "") -> pd.DataFrame:
    a_path = WORK_DIR / f"{tag}_A{suffix}_records.xlsx"
    b_path = WORK_DIR / f"{tag}_B{suffix}_records.xlsx"
    if not (a_path.exists() and b_path.exists()):
        return pd.DataFrame()

    a = pd.read_excel(a_path).set_index("Pdf name")
    b = pd.read_excel(b_path).set_index("Pdf name")
    items = item_columns(a, spec["prefix"], spec["exclude"])

    def status(frame: pd.DataFrame, key: str) -> str:
        return cell_text(frame.at[key, "status"]).lower() if "status" in frame.columns else "ok"

    rows = []
    for item in items:
        if item not in b.columns:
            continue
        for key in a.index:
            if key not in b.index:
                continue
            sa, sb = status(a, key), status(b, key)
            if sa != "ok" and sb != "ok":
                # Neither pass read the document (e.g. a scanned PDF): nothing
                # to adjudicate between; it is coded by hand or excluded.
                continue
            va, vb = a.at[key, item], b.at[key, item]
            if sa == "ok" and sb == "ok":
                if pd.isna(va) or pd.isna(vb) or bool(va) == bool(vb):
                    continue
                kind = "disagreement"
            else:
                # One pass failed part-way: its "not found" codes are defaults,
                # not judgements, so agreement with it means nothing. Every code
                # of the complete pass goes to the human, positive or negative.
                kind = f"single pass ({'B' if sb != 'ok' else 'A'} incomplete)"
            rows.append({
                "pdf_name": key,
                "item": item,
                "case": kind,
                "pass_A": bool(va) if sa == "ok" and not pd.isna(va) else None,
                "pass_B": bool(vb) if sb == "ok" and not pd.isna(vb) else None,
                "A_quote": cell_text(a.at[key, f"{item}__quote"]) if f"{item}__quote" in a.columns else "",
                "A_offset": cell_text(a.at[key, f"{item}__offset"]) if f"{item}__offset" in a.columns else "",
                "A_verified": cell_text(a.at[key, f"{item}__verified"]) if f"{item}__verified" in a.columns else "",
                "B_quote": cell_text(b.at[key, f"{item}__quote"]) if f"{item}__quote" in b.columns else "",
                "B_offset": cell_text(b.at[key, f"{item}__offset"]) if f"{item}__offset" in b.columns else "",
                "B_verified": cell_text(b.at[key, f"{item}__verified"]) if f"{item}__verified" in b.columns else "",
                "final_code": "",     # the human fills these two
                "reason": "",
            })

    frame = pd.DataFrame(rows)
    if not frame.empty:
        # By item first: one calibrated question at a time.
        frame["__order"] = frame["item"].map({name: i for i, name in enumerate(items)})
        frame = frame.sort_values(["__order", "pdf_name"]).drop(columns="__order")
    return frame


def write_html(frame: pd.DataFrame, definitions: dict[str, str], path: Path, title: str,
               model_a: str, model_b: str) -> None:
    def quote_block(code, quote: str, offset: str, verified: str) -> str:
        if code is None:
            return ('<div class="neg"><b>no usable code</b><div class="note">this pass did '
                    'not finish reading the document; decide from the other pass and the PDF'
                    '</div></div>')
        if not code:
            return ('<div class="neg">said <b>no</b><div class="note">a negative carries '
                    'no quote by construction</div></div>')
        badge = f'<span class="badge {html.escape(verified or "?")}">{html.escape(verified or "?")}</span>'
        where = f'<span class="off">@{html.escape(offset)}</span>' if offset else ""
        body = html.escape(quote) if quote else "<i>said yes but gave no quote</i>"
        return f'<div class="pos">said <b>yes</b> {badge} {where}<blockquote>{body}</blockquote></div>'

    sections = []
    for item, group in frame.groupby("item", sort=False):
        definition = definitions.get(item, "")
        rows = []
        for _, r in group.iterrows():
            rows.append(
                f'<tr id="{html.escape(r["pdf_name"])}_{html.escape(item)}">'
                f'<td class="id">{html.escape(r["pdf_name"])}</td>'
                f'<td>{quote_block(r["pass_A"], r["A_quote"], r["A_offset"], r["A_verified"])}</td>'
                f'<td>{quote_block(r["pass_B"], r["B_quote"], r["B_offset"], r["B_verified"])}</td>'
                f'</tr>'
            )
        sections.append(
            f'<section><h2>{html.escape(item)} <span class="count">{len(group)} to decide</span></h2>'
            + (f'<p class="def">{html.escape(definition)}</p>' if definition else "")
            + f'<table><tr><th>study</th><th>pass A &mdash; {html.escape(model_a)}</th>'
              f'<th>pass B &mdash; {html.escape(model_b)}</th></tr>'
            + "".join(rows) + "</table></section>"
        )

    path.write_text(
        "<!doctype html><meta charset='utf-8'>"
        f"<title>Adjudication &mdash; {html.escape(title)}</title>"
        "<style>"
        "body{font:15px/1.55 system-ui,sans-serif;margin:0 auto;padding:2rem;max-width:75rem;color:#111}"
        "h1{margin-bottom:.2rem} h2{margin:2.5rem 0 .3rem;font-size:1.15rem}"
        ".count{font-weight:400;color:#666;font-size:.85rem}"
        ".def{color:#444;background:#f6f6f4;padding:.6rem .8rem;border-left:3px solid #ccc;margin:.4rem 0 1rem}"
        "table{border-collapse:collapse;width:100%} th{text-align:left;font-size:.8rem;color:#666;padding:.3rem}"
        "td{border-top:1px solid #e5e5e5;padding:.6rem .4rem;vertical-align:top;width:42%}"
        "td.id{width:16%;font-family:ui-monospace,monospace;font-size:.85rem;white-space:nowrap}"
        "blockquote{margin:.35rem 0 0;padding-left:.7rem;border-left:2px solid #bbb;color:#222}"
        ".neg{color:#777} .note{font-size:.78rem;color:#999}"
        ".badge{font-size:.7rem;padding:.05rem .35rem;border-radius:3px;background:#eee;color:#555}"
        ".badge.exact{background:#e3f2e3;color:#25612b} .badge.unverified{background:#fde8e8;color:#9b2020}"
        ".off{font-size:.75rem;color:#999}"
        "</style>"
        f"<h1>Adjudication &mdash; {html.escape(title)}</h1>"
        f"<p>{len(frame)} disagreements between the two extraction passes, grouped by item. "
        "Decide each against the rubric text shown under the heading, then record the "
        "decision and a one-line reason in the matching row of the xlsx.</p>"
        "<p><b>Neither pass is presented as more likely right.</b> Where a pass said no, "
        "there is no quote to show: that is how a negative is recorded, not a missing value.</p>"
        + "".join(sections),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--tag", choices=list(INSTRUMENTS) + ["all"], default="all")
    parser.add_argument("--model-a", default="gpt-oss:120b")
    parser.add_argument("--model-b", default="Qwen3.8-Flash-Next")
    parser.add_argument("--suffix", default="_all",
                        help="record-file suffix; _all = baseline + included round 2 (38_combine_records.py)")
    args = parser.parse_args()

    tags = list(INSTRUMENTS) if args.tag == "all" else [args.tag]
    for tag in tags:
        spec = INSTRUMENTS[tag]
        frame = collect(tag, spec, args.suffix)
        if frame.empty:
            print(f"{tag}: nothing to adjudicate (or inputs missing)")
            continue

        xlsx = WORK_DIR / f"adjudication_{tag}.xlsx"
        page = WORK_DIR / f"adjudication_{tag}.html"
        if xlsx.exists():
            # Once P.Z. starts filling it, this file is the adjudication log.
            raise SystemExit(f"ERROR: {xlsx} exists. Archive or rename it first; "
                             "this script never overwrites a decision log.")
        frame.to_excel(xlsx, index=False)
        write_html(frame, item_definitions(spec["prompt"]), page, spec["title"],
                   args.model_a, args.model_b)

        per_item = frame["item"].value_counts()
        print(f"{tag}: {len(frame)} disagreements across {frame['pdf_name'].nunique()} studies")
        for item, count in per_item.items():
            print(f"    {item:<28} {count:>3}")
        print(f"    -> {xlsx.name}")
        print(f"    -> {page.name}\n")


if __name__ == "__main__":
    main()
