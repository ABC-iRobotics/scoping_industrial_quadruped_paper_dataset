"""
Stage 10 - RCI extraction from full texts, chunked, with verbatim evidence.

WHY THIS EXISTS RATHER THAN AN EDIT TO 03_llm_extraction.py
    Three properties the SISY extraction stage cannot provide:

    1. It read only the first 25 000 characters. Measured over the 88-study
       corpus that truncates 74 of 88 documents, and it cuts off the sections
       where RCI items 4, 6 and 7 live. This stage reads the whole document in
       overlapping chunks, so nothing is silently unread.
    2. Its output is one pipe-separated line, parsed by taking the line with the
       most "|" characters. Verbatim evidence quotes contain pipes, newlines and
       code fences, so that parser cannot carry them. This stage uses JSON.
    3. Its `Reproducable?` field is a single holistic yes/no. The RCI replaces
       it with nine separately evidenced items.

THE MERGE RULE, WHICH IS THE WHOLE CORRECTNESS ARGUMENT
    A chunk that does not mention ROS is not evidence that the paper does not
    use ROS - it is evidence that this part of the paper does not mention it.
    So:

      * found=true in ANY chunk wins, and carries that chunk's quote.
      * found=false is concluded for a record only when EVERY chunk was read
        and parsed successfully and none reported the item.
      * if ANY chunk failed (API error, unparseable reply), the record's status
        is `incomplete` and its negatives are NOT usable as "not reported".

    Without the third rule a transport failure silently becomes a finding of
    non-reporting, which would bias RQ4 in exactly the direction the paper's
    argument already predicts. Incomplete records must be re-run or resolved by
    hand, never averaged in.

INPUTS
    --input      spreadsheet with a `Pdf name` column (default: the baseline)
    --pdf-dir    directory of PDFs named <Pdf name>.pdf  (env PDF_DIR)
    prompts/rci_extraction.md
    LLM_API_KEY in the environment or in .env

OUTPUTS
    work/rci_<pass>_records.xlsx   one row per study: the merged codes
    work/rci_<pass>_evidence.csv   one row per (study, item): quote and offset
    work/rci_<pass>_raw/<id>.json  per-study raw chunk replies, for audit

TWO PASSES
    Run this twice with different models to get two independent extractions:

        python scripts/10_rci_extraction.py --pass A
        LLM_MODEL=<other-model> python scripts/10_rci_extraction.py --pass B

    Two runs of the SAME model produce correlated errors: they agree with each
    other while measuring nothing. Use a genuinely different model for pass B,
    and if that is impossible, say so in Methods rather than implying otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from _common import (
    API_URL,
    MODEL,
    PDF_DIR,
    WORK_DIR,
    call_llm,
    cell_text,
    chunk_text,
    load_prompt,
    merge_free_text,
    parse_json_reply,
    pdf_text,
    pdf_page_count,
    text_layer_ok,
)

# The nine rubric items, in the order they appear in CLAUDE.md section 6.
RCI_ITEMS = [
    "rci1_platform_model",
    "rci2_sensors_model",
    "rci3_compute_model",
    "rci4_middleware_version",
    "rci5_algorithms_cited",
    "rci6_parameters",
    "rci7_eval_environment",
    "rci8_success_metric",
    "rci9_artifact",
]

SPECIFICITY_RANK = {"unspecified": 0, "modality": 1, "model": 2}

# Quote verification. A quote is the whole reason this design is auditable, so
# it is checked mechanically against the chunk it was drawn from rather than
# trusted. Calibration on five papers found no fabricated quotes but two cases
# where the model stitched or elided instead of copying one span - which is
# enough to break mechanical location, so it is flagged rather than accepted.
#
# Matching strips everything but alphanumerics because PDF text extraction
# mangles ligatures, soft hyphens and unicode dashes: "1x1m" in the extracted
# text can be "1x1m" in the quote and still be the same characters on the page.
# A genuine fabrication does not survive this normalisation - it shows up as a
# match well under half the quote's length.
MIN_FRAGMENT_CHARS = 12
MIN_ELIDED_COVERAGE = 0.6

# Unicode lookalikes must be folded BEFORE non-alphanumerics are stripped.
# Stripping first silently breaks the comparison: "1x1 m" in a quote normalises
# to "1x1m", but "1x1 m" in the PDF loses the multiplication sign entirely and
# becomes "11m". The two then differ, and a correct quote is reported as
# unverifiable. Same story for dashes, ligatures and typographic quotes.
_CONFUSABLES = {
    "×": "x", "✕": "x", "✖": "x",                 # multiplication signs
    "–": "-", "—": "-", "−": "-", "‑": "-",  # dashes, non-breaking hyphen
    "‘": "'", "’": "'", "“": '"', "”": '"',  # smart quotes
    "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff",              # ligatures
    "µ": "u", "μ": "u",                                # micro sign
    " ": " ", " ": " ", " ": " ",                 # exotic spaces
}


def _hard_normalise(text: str) -> str:
    text = str(text).lower()
    for source_char, replacement in _CONFUSABLES.items():
        text = text.replace(source_char, replacement)
    return re.sub(r"[^a-z0-9]", "", text)


def verify_quote(quote: str, source: str) -> str:
    """
    Return 'exact', 'elided' or 'unverified' for a quote against its chunk.

    'elided' means the model wrote "A ... B": every fragment is present in the
    source but the span is not contiguous. That is honest quoting, but it
    defeats mechanical location, so it is recorded distinctly rather than being
    folded into 'exact'.

    The coverage floor stops a quote from being accepted on the strength of one
    long fragment plus filler - the located fragments have to account for most
    of what the model claimed to be quoting.
    """
    quote = str(quote or "").strip()
    if not quote:
        return "unverified"

    hard_quote = _hard_normalise(quote)
    hard_source = _hard_normalise(source)
    if not hard_quote:
        return "unverified"
    if hard_quote in hard_source:
        return "exact"

    fragments = [_hard_normalise(f) for f in re.split(r"\.\.\.|…|\[\.\.\.\]", quote)]
    usable = [f for f in fragments if len(f) >= MIN_FRAGMENT_CHARS]
    if len(usable) >= 2 and all(f in hard_source for f in usable):
        if sum(len(f) for f in usable) / len(hard_quote) >= MIN_ELIDED_COVERAGE:
            return "elided"

    return "unverified"

# Chunking defaults. Corpus measurements: median document 36 556 chars,
# p90 87 495, max 159 323. A 30 000-char chunk keeps the median document to two
# calls while staying well inside a conservative context window - verify the
# real limit with probe_context.py before trusting a larger value.
DEFAULT_CHUNK_CHARS = 30_000
DEFAULT_OVERLAP = 4_000


def merge_chunk_results(results: list[tuple[int, dict]]) -> dict:
    """
    Fold per-chunk extractions into one record-level result.

    `results` is a list of (chunk_start_offset, parsed_json). Positive findings
    win and carry their evidence; specificity takes the most specific level seen;
    raw strings are unioned in first-seen order.
    """
    merged: dict = {}

    for item in RCI_ITEMS:
        merged[item] = False
        merged[f"{item}__quote"] = ""
        merged[f"{item}__offset"] = ""
        merged[f"{item}__verified"] = ""

        # Collect every positive, then prefer the best-evidenced one. Taking the
        # first positive would let an unverifiable quote in one chunk mask a
        # verbatim one in another.
        candidates = []
        for offset, payload in results:
            entry = payload.get(item)
            if not isinstance(entry, dict) or entry.get("found") is not True:
                continue
            quote = str(entry.get("quote") or "").strip()
            # A positive claim without a quote is not evidence. The prompt says
            # so; enforce it here too, because prompts are not guarantees.
            if not quote:
                continue
            candidates.append((offset, quote, entry.get("__verified", "unverified")))

        if candidates:
            rank = {"exact": 0, "elided": 1, "unverified": 2}
            offset, quote, verdict = min(candidates, key=lambda c: (rank.get(c[2], 3), c[0]))
            merged[item] = True
            merged[f"{item}__quote"] = quote
            merged[f"{item}__offset"] = offset
            merged[f"{item}__verified"] = verdict

    for field in ("sensor_specificity", "compute_specificity"):
        best, best_rank = "unspecified", -1
        for _, payload in results:
            value = str(payload.get(field) or "").strip().lower()
            rank = SPECIFICITY_RANK.get(value, -1)
            if rank > best_rank:
                best, best_rank = value, rank
        merged[field] = best if best_rank >= 0 else "unspecified"

    # Environment kind is a union, not a maximum: a paper that evaluates in
    # simulation AND on hardware is 'both' even though no single chunk says so.
    kinds = set()
    for _, payload in results:
        value = str(payload.get("eval_environment_kind") or "").strip().lower()
        if value in {"real", "simulated"}:
            kinds.add(value)
        elif value == "both":
            kinds.update({"real", "simulated"})
    if kinds == {"real", "simulated"}:
        merged["eval_environment_kind"] = "both"
    elif kinds:
        merged["eval_environment_kind"] = kinds.pop()
    else:
        merged["eval_environment_kind"] = "unclear"

    for field in ("optical_sensors_raw", "onboard_computer_raw"):
        merged[field] = merge_free_text([payload.get(field) for _, payload in results])

    merged["rci_total"] = sum(1 for item in RCI_ITEMS if merged[item])
    return merged


def process_record(pdf_path: Path, system: str, template: str, params: dict,
                   chunk_chars: int, overlap: int, delay: float) -> tuple[dict, list]:
    """Extract one study. Returns (record_fields, raw_chunk_log)."""
    text = pdf_text(pdf_path)
    pages = pdf_page_count(pdf_path)
    usable, ratio = text_layer_ok(text, pages)
    if not usable:
        # No LLM call is made. A document with no usable text layer cannot be
        # coded, and asking anyway returns a full row of negatives that are
        # indistinguishable from findings. The previous guard tripped only below
        # 100 characters, which let a 6-page scanned PDF through at 2,160.
        print(f"      TEXT LAYER TOO THIN: {len(text):,} chars over {pages} page(s)"
              f" = {ratio:.0f}/page. Not coded.")
        return {"status": "text extraction failed", "n_chunks": 0, "n_failed": 0,
                "doc_chars": len(text), "doc_pages": pages,
                "chars_per_page": round(ratio, 1)}, []

    chunks = chunk_text(text, chunk_chars, overlap)
    results: list[tuple[int, dict]] = []
    raw_log: list[dict] = []
    failed = 0

    for index, (offset, chunk) in enumerate(chunks, start=1):
        answer = call_llm(system, template.replace("{record}", chunk), params, timeout=300)
        parsed = parse_json_reply(answer)
        raw_log.append({
            "chunk_index": index,
            "chunk_offset": offset,
            "chunk_chars": len(chunk),
            "parsed": parsed is not None,
            "reply": answer,
        })
        if parsed is None:
            failed += 1
            print(f"      chunk {index}/{len(chunks)}: UNPARSEABLE")
        else:
            # Check every claimed quote against the chunk it came from, now,
            # while that chunk is still in hand.
            unverified_here = 0
            for name in RCI_ITEMS:
                entry = parsed.get(name)
                if isinstance(entry, dict) and entry.get("found") is True:
                    verdict = verify_quote(entry.get("quote", ""), chunk)
                    entry["__verified"] = verdict
                    if verdict != "exact":
                        unverified_here += 1
            results.append((offset, parsed))
            hits = sum(1 for i in RCI_ITEMS
                       if isinstance(parsed.get(i), dict) and parsed[i].get("found") is True)
            flag = f", {unverified_here} not verbatim" if unverified_here else ""
            print(f"      chunk {index}/{len(chunks)}: {hits} item(s) found{flag}")
        if index < len(chunks):
            time.sleep(delay)

    merged = merge_chunk_results(results)
    # See the module docstring: negatives are only trustworthy when every chunk
    # was read. Anything else is `incomplete` and must not be counted as "no".
    merged["status"] = "ok" if failed == 0 and results else "incomplete"
    merged["n_chunks"] = len(chunks)
    merged["n_failed"] = failed
    merged["doc_chars"] = len(text)
    merged["doc_pages"] = pages
    merged["chars_per_page"] = round(ratio, 1)
    return merged, raw_log


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", default=str(WORK_DIR / "rci_include_list.xlsx"))
    parser.add_argument("--pdf-dir", default=str(PDF_DIR))
    parser.add_argument("--pass", dest="pass_label", default="A",
                        help="pass label, e.g. A or B (use a different LLM_MODEL for B)")
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=0, help="process at most N records (0 = all)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"ERROR: include list not found: {input_path}")

    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        raise SystemExit(f"ERROR: PDF directory not found: {pdf_dir}\nSet PDF_DIR or pass --pdf-dir.")

    tag = args.pass_label
    out_records = WORK_DIR / f"rci_{tag}_records.xlsx"
    out_evidence = WORK_DIR / f"rci_{tag}_evidence.csv"
    raw_dir = WORK_DIR / f"rci_{tag}_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_excel(out_records) if out_records.exists() else pd.read_excel(input_path)
    # A resumed run must also pick up records added to the input since the last
    # run; reading only the old output would skip them silently.
    fresh = pd.read_excel(input_path)
    fresh = fresh[~fresh["Pdf name"].astype(str).isin(frame["Pdf name"].astype(str))]
    if len(fresh):
        print(f"adding {len(fresh)} new input record(s): {', '.join(fresh['Pdf name'].astype(str))}")
        frame = pd.concat([frame, fresh], ignore_index=True)
    for column in ["status", "n_chunks", "n_failed", "doc_chars", "doc_pages", "chars_per_page", "rci_total",
                   "sensor_specificity", "compute_specificity",
                   "optical_sensors_raw", "onboard_computer_raw",
                   "eval_environment_kind"] + RCI_ITEMS:
        if column not in frame.columns:
            frame[column] = pd.NA
    # Created as object up front: these hold "" as often as numbers, and pandas
    # warns (and will later raise) when "" is written into a float64 column.
    for item in RCI_ITEMS:
        for suffix in ("__quote", "__offset", "__verified"):
            if f"{item}{suffix}" not in frame.columns:
                frame[f"{item}{suffix}"] = pd.Series([""] * len(frame), dtype="object")

    system, template, params = load_prompt("rci_extraction")

    print(f"pass={tag}  model={MODEL}  endpoint={API_URL}")
    print(f"chunking: {args.chunk_chars:,} chars, {args.overlap:,} overlap\n")

    processed = 0
    for position, (index, row) in enumerate(frame.iterrows(), start=1):
        pdf_name = cell_text(row.get("Pdf name"))
        if not pdf_name:
            continue
        # Resume: a completed record keeps its result. `incomplete` is retried,
        # which is the point of distinguishing it from `ok`.
        if cell_text(row.get("status")) == "ok":
            continue
        if args.limit and processed >= args.limit:
            break

        pdf_path = pdf_dir / f"{pdf_name}.pdf"
        if not pdf_path.exists():
            print(f"  {position}/{len(frame)}  PDF not found -> {pdf_name}")
            frame.at[index, "status"] = "pdf_missing"
            continue

        print(f"  {position}/{len(frame)}  {pdf_name}")
        merged, raw_log = process_record(pdf_path, system, template, params,
                                         args.chunk_chars, args.overlap, args.delay)
        for key, value in merged.items():
            if key in frame.columns or key.endswith(("__quote", "__offset")):
                frame.at[index, key] = value
            else:
                frame.at[index, key] = value

        (raw_dir / f"{pdf_name}.json").write_text(json.dumps({
            "pdf_name": pdf_name,
            "pass": tag,
            "model": MODEL,
            "endpoint": API_URL,
            "chunk_chars": args.chunk_chars,
            "overlap": args.overlap,
            "extracted_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "chunks": raw_log,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        status = merged.get("status")
        print(f"    -> {status}, RCI {merged.get('rci_total', '?')}/9\n")
        processed += 1
        frame.to_excel(out_records, index=False)

    frame.to_excel(out_records, index=False)

    # Long-format evidence table: one row per (study, item). This is what the
    # human validator reads, and what makes a claimed code checkable.
    evidence_rows = []
    for _, row in frame.iterrows():
        pdf_name = cell_text(row.get("Pdf name"))
        if not pdf_name or cell_text(row.get("status")) not in ("ok", "incomplete"):
            continue
        for item in RCI_ITEMS:
            evidence_rows.append({
                "pdf_name": pdf_name,
                "pass": tag,
                "item": item,
                "found": row.get(item),
                "quote": cell_text(row.get(f"{item}__quote")),
                "char_offset": cell_text(row.get(f"{item}__offset")),
                "quote_verified": cell_text(row.get(f"{item}__verified")),
                "record_status": cell_text(row.get("status")),
            })
    pd.DataFrame(evidence_rows).to_csv(out_evidence, index=False, encoding="utf-8")

    if evidence_rows:
        positives = [r for r in evidence_rows if r["found"] is True or str(r["found"]) == "True"]
        verdicts = {}
        for r in positives:
            verdicts[r["quote_verified"] or "unverified"] = verdicts.get(r["quote_verified"] or "unverified", 0) + 1
        if positives:
            exact = verdicts.get("exact", 0)
            print(f"\nQuote check: {exact}/{len(positives)} positives quote the source "
                  f"verbatim ({exact / len(positives) * 100:.1f}%). Breakdown: {verdicts}")
            if len(positives) - exact:
                print("  Non-verbatim codes are still positives, but they cannot be located")
                print("  mechanically - route them to human review first.")

    counts = frame["status"].astype(str).value_counts().to_dict()
    print(f"\nProcessed {processed} record(s) this run.")
    print(f"Status: {counts}")
    incomplete = int(frame["status"].astype(str).eq("incomplete").sum())
    if incomplete:
        print(f"\nWARNING: {incomplete} record(s) incomplete - at least one chunk failed.")
        print("Their negatives are NOT usable as 'not reported'. Re-run to retry them.")
    print(f"Records:  {out_records}")
    print(f"Evidence: {out_evidence}")


if __name__ == "__main__":
    main()
