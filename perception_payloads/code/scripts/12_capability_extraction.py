"""
Stage 12 - RQ1-RQ3 capability extraction: chunked, JSON, with evidence quotes.

WHY A SECOND INSTRUMENT
    `03_llm_extraction.py` already extracts the six capability flags, and it is
    the stage that produced them for the 88-study baseline. It is not good
    enough to extend across the merged corpus:

      - it reads only the first 25,000 characters of each PDF, and capability
        evidence sits in the implementation and experiments sections
      - it returns 15 pipe-separated values, so a code cannot carry the verbatim
        evidence quote the reliability design requires
      - a quotation containing a pipe breaks its parser outright

    So the RQ2 variables get the same treatment the RCI items got: the whole
    document in overlapping chunks, JSON out, a machine-verified quote behind
    every positive. The round-1 values stay as a comparison, not as input.

WHY NOT MORE FIELDS IN `rci_extraction.md`
    That prompt is the registered RQ4 instrument and it was piloted as it
    stands. Bolting ten more fields onto it would put twenty-odd items in one
    reply at `max_tokens: 1800`, dilute the item wording, and require the whole
    instrument to be re-piloted. Two instruments, each piloted, cost machine
    time; one overloaded instrument costs credibility.

    `industry_sector_raw` lives HERE and not in the RCI prompt, so that each
    variable has exactly one source and the merge has nothing to arbitrate.

WHAT IT DOES
    Identical machinery to `10_rci_extraction.py`, which it imports rather than
    copies - chunking, quote verification, the merge rule. Only the item list
    and the free-text fields differ.

    The merge rule matters as much here as there: a positive in ANY chunk wins;
    a negative is concluded only when EVERY chunk was read and parsed; if any
    chunk failed, the record is `incomplete` and its negatives are not usable as
    "the system does not do this".

INPUTS
    An xlsx with a `Pdf name` column; the PDFs in PDF_DIR.
    prompts/capability_extraction.md
    LLM_API_KEY in the environment or in .env

OUTPUTS
    work/cap_<pass>_records.xlsx    one row per study, flags + quotes + offsets
    work/cap_<pass>_evidence.csv    long format, one row per (study, item)
    work/cap_<pass>_raw/<id>.json   the untouched per-chunk replies

USAGE
    python scripts/12_capability_extraction.py --pass A
    LLM_MODEL=qwen3.6:35b-a3b python scripts/12_capability_extraction.py --pass B
"""

from __future__ import annotations

import argparse
import importlib.util
import json
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

# The RCI stage owns the chunking, quote-verification and merge-preference
# machinery, and it has been calibrated against the corpus. Importing it keeps
# ONE implementation of "is this quote really in the source"; a copy would drift
# from the original the first time either is fixed. The module name starts with
# a digit, so it cannot be imported by name - hence the explicit loader.
_RCI_PATH = Path(__file__).resolve().parent / "10_rci_extraction.py"
_spec = importlib.util.spec_from_file_location("rci_extraction", _RCI_PATH)
_rci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rci)

verify_quote = _rci.verify_quote
QUOTE_RANK = {"exact": 0, "elided": 1, "unverified": 2}

DEFAULT_CHUNK_CHARS = _rci.DEFAULT_CHUNK_CHARS
DEFAULT_OVERLAP = _rci.DEFAULT_OVERLAP

CAPABILITY_ITEMS = [
    "cap_slam_mapping",
    "cap_autonomous_navigation",
    "cap_obstacle_avoidance",
    "cap_object_detection",
    "cap_instrument_reading",
    "cap_target_tracking",
    "cap_real_world_validation",
]

FREE_TEXT = ["industry_sector_raw", "high_level_goal_raw", "ai_ml_solutions_raw"]


def merge_chunk_results(results: list[tuple[int, dict]]) -> dict:
    """
    Collapse per-chunk replies into one record.

    Positives win across chunks and carry their evidence. Among competing
    positives the best-verified quote wins, then the earliest offset - so a
    verified quote in a late chunk beats an unverifiable one in an early chunk.
    A positive with no quote is not a positive.
    """
    merged: dict = {}

    for item in CAPABILITY_ITEMS:
        candidates = []
        for offset, payload in results:
            entry = payload.get(item)
            if not isinstance(entry, dict) or not entry.get("found"):
                continue
            quote = str(entry.get("quote") or "").strip()
            if not quote:
                continue  # a code with no evidence is not a code
            source = payload.get("__chunk_text", "")
            verdict = verify_quote(quote, source) if source else "unverified"
            candidates.append((QUOTE_RANK.get(verdict, 3), offset, quote, verdict))

        if candidates:
            candidates.sort()
            _, offset, quote, verdict = candidates[0]
            merged[item] = True
            merged[f"{item}__quote"] = quote
            merged[f"{item}__offset"] = offset
            merged[f"{item}__verified"] = verdict
        else:
            merged[item] = False
            merged[f"{item}__quote"] = ""
            merged[f"{item}__offset"] = ""
            merged[f"{item}__verified"] = ""

    for field in FREE_TEXT:
        merged[field] = merge_free_text([payload.get(field) for _, payload in results])

    merged["n_capabilities"] = sum(1 for item in CAPABILITY_ITEMS if merged[item])
    return merged


def process_record(pdf_path: Path, system: str, template: str, params: dict,
                   chunk_chars: int, overlap: int, delay: float) -> tuple[dict, list]:
    """Read one PDF in overlapping chunks and merge the per-chunk answers."""
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
    results, raw_log, failed = [], [], 0

    for index, (offset, chunk) in enumerate(chunks, start=1):
        answer = call_llm(system, template.replace("{record}", chunk), params, timeout=600)
        payload = parse_json_reply(answer)
        raw_log.append({"chunk": index, "offset": offset, "reply": answer})

        if payload is None:
            failed += 1
            print(f"      chunk {index}/{len(chunks)}: UNPARSEABLE")
            continue

        payload["__chunk_text"] = chunk
        results.append((offset, payload))
        found = sum(
            1 for item in CAPABILITY_ITEMS
            if isinstance(payload.get(item), dict) and payload[item].get("found")
        )
        print(f"      chunk {index}/{len(chunks)}: {found} item(s) found")
        if delay:
            import time
            time.sleep(delay)

    merged = merge_chunk_results(results)
    merged["n_chunks"] = len(chunks)
    merged["n_failed"] = failed
    merged["doc_chars"] = len(text)
    merged["doc_pages"] = pages
    merged["chars_per_page"] = round(ratio, 1)
    # A failed chunk means the negatives are unproven, not proven false.
    merged["status"] = "ok" if failed == 0 and results else "incomplete"
    return merged, raw_log


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", default=str(WORK_DIR / "rci_include_list.xlsx"))
    parser.add_argument("--pdf-dir", default=str(PDF_DIR))
    parser.add_argument("--pass", dest="pass_label", default="A")
    parser.add_argument("--chunk-chars", type=int, default=DEFAULT_CHUNK_CHARS)
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    input_path, pdf_dir, tag = Path(args.input), Path(args.pdf_dir), args.pass_label
    if not input_path.exists():
        raise SystemExit(f"ERROR: input not found: {input_path}")

    system, template, params = load_prompt("capability_extraction")
    out_records = WORK_DIR / f"cap_{tag}_records.xlsx"
    out_evidence = WORK_DIR / f"cap_{tag}_evidence.csv"
    raw_dir = WORK_DIR / f"cap_{tag}_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_excel(out_records) if out_records.exists() else pd.read_excel(input_path)
    # A resumed run must also pick up records added to the input since the last
    # run; reading only the old output would skip them silently.
    fresh = pd.read_excel(input_path)
    fresh = fresh[~fresh["Pdf name"].astype(str).isin(frame["Pdf name"].astype(str))]
    if len(fresh):
        print(f"adding {len(fresh)} new input record(s): {', '.join(fresh['Pdf name'].astype(str))}")
        frame = pd.concat([frame, fresh], ignore_index=True)
    for column in (["status", "n_chunks", "n_failed", "doc_chars", "doc_pages", "chars_per_page", "n_capabilities"]
                   + FREE_TEXT + CAPABILITY_ITEMS):
        if column not in frame.columns:
            frame[column] = pd.NA
    for item in CAPABILITY_ITEMS:
        for suffix in ("__quote", "__offset", "__verified"):
            if f"{item}{suffix}" not in frame.columns:
                frame[f"{item}{suffix}"] = pd.Series([pd.NA] * len(frame), dtype="object")

    print(f"model={MODEL}  endpoint={API_URL}")
    print(f"pass={tag}  input={input_path.name}  records={len(frame)}")
    print(f"chunking: {args.chunk_chars:,} chars, {args.overlap:,} overlap\n")

    processed = 0
    for index, row in frame.iterrows():
        if args.limit and processed >= args.limit:
            break
        # Resume deliberately skips only 'ok': an incomplete record is retried.
        if cell_text(row.get("status")) == "ok":
            continue

        pdf_name = cell_text(row.get("Pdf name"))
        pdf_path = pdf_dir / f"{pdf_name}.pdf"
        print(f"  {processed + 1}  {pdf_name}")
        if not pdf_path.exists():
            frame.at[index, "status"] = "pdf missing"
            print("      PDF NOT FOUND\n")
            processed += 1
            continue

        merged, raw_log = process_record(pdf_path, system, template, params,
                                         args.chunk_chars, args.overlap, args.delay)
        for key, value in merged.items():
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

        print(f"    -> {merged['status']}, {merged.get('n_capabilities', '-')}/7 capabilities\n")
        processed += 1
        frame.to_excel(out_records, index=False)

    frame.to_excel(out_records, index=False)

    evidence_rows = []
    for _, row in frame.iterrows():
        pdf_name = cell_text(row.get("Pdf name"))
        if not pdf_name or cell_text(row.get("status")) not in ("ok", "incomplete"):
            continue
        for item in CAPABILITY_ITEMS:
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

    positives = [r for r in evidence_rows if r["found"] is True or str(r["found"]) == "True"]
    if positives:
        verdicts: dict[str, int] = {}
        for record in positives:
            key = record["quote_verified"] or "unverified"
            verdicts[key] = verdicts.get(key, 0) + 1
        exact = verdicts.get("exact", 0)
        share = 100.0 * exact / len(positives)
        print(f"\nQuote check: {exact}/{len(positives)} positives quote the source "
              f"verbatim ({share:.1f}%). Breakdown: {verdicts}")

    statuses: dict[str, int] = {}
    for value in frame["status"].dropna():
        statuses[str(value)] = statuses.get(str(value), 0) + 1
    print(f"\nProcessed {processed} record(s) this run.")
    print(f"Status: {statuses}")
    print(f"Records:  {out_records}")
    print(f"Evidence: {out_evidence}")


if __name__ == "__main__":
    main()
