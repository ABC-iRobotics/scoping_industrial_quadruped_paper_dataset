"""
Stage 3 - LLM-assisted structured data extraction from the full texts.

WHAT IT DOES
    For each included study, extracts the first 25 000 characters of the PDF and
    asks the model to return 15 pipe-separated values: five free-text fields
    (robot platform, onboard compute, optical sensors, high-level goal, AI/ML
    solutions), nine yes/no capability flags, and a success-metric description.

    Rows whose PDF is missing or unreadable are marked in the Robot platform
    column ("PDF not found" / "PDF unreadable" / "API error") rather than being
    silently skipped, so that failures stay visible in the output.

INPUTS
    work/05_include_list.xlsx   the manually curated list of included studies,
                                carrying a `Pdf name` column that matches the
                                PDF filenames (without extension)
    input/papers/*.pdf          the full texts. Not included in this repository:
                                the PDFs are copyrighted and not redistributable.
    prompts/data_extraction.md
    LLM_API_KEY in the environment or in .env

OUTPUTS
    work/06_extraction.xlsx     the full extraction, all 15 variables

PAPER REFERENCE
    Section II-C (Data Extraction). Produces the extracted variables that the
    published dataset is drawn from.

CONSOLIDATED FROM
    full_text_screening.py in the original working directory. Despite its name
    that script performed data extraction, not screening.

NOTE ON THE INPUT
    The include list is a manual artifact: the primary reviewer decided the final
    inclusion set and matched each study to a downloaded PDF by hand. One study
    (paper088) was added after the automated rounds had finished. This stage
    therefore cannot be run end to end from stage 2 output alone. See README.md,
    "Manual steps in the pipeline".

NOTE ON REPRODUCIBILITY
    This stage sends no temperature or max_tokens, so the server-side defaults
    applied. Those defaults were not recorded and no seed was set. Re-running
    will not reproduce the published extraction exactly.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import fitz  # PyMuPDF
import pandas as pd

from _common import RELEASE_ROOT, WORK_DIR, call_llm, cell_text, load_prompt

# Output columns, in the order the model returns them.
EXTRACTION_COLUMNS = [
    "Robot platform",
    "Onboard Computer",
    "Optical Sensors",
    "High-level goal",
    "AI / ML solutions for vision qualities?",
    "SLAM/mapping?",
    "Autonomous navigation?",
    "Obstacle Avoidance",
    "Object detection?",
    "Instrument reading?",
    "Target tracking?",
    "Environmental challenges?",
    "Real-world validation?",
    "Reproducable?",
    "Success metric for goal task?",
]

# Indices 5..13 are the yes/no capability flags.
YES_NO_RANGE = range(5, 14)

MAX_PDF_CHARS = 25_000


def extract_pdf_text(pdf_path: Path, max_chars: int = MAX_PDF_CHARS) -> str:
    """
    Return the first `max_chars` characters of a PDF's text, whitespace collapsed.

    The 25 000 character window was chosen so that hardware specifications, which
    typically appear on pages 6-8 of these papers, fall inside it.
    """
    try:
        document = fitz.open(pdf_path)
    except Exception as error:
        print(f"  PDF read error: {pdf_path} -> {error}")
        return ""

    pages = [page.get_text("text") for page in document]
    full_text = "\n".join(text for text in pages if text)
    return " ".join(full_text.split())[:max_chars]


def normalize_yes_no(text: str) -> str:
    """Map a free-text yes/no answer onto 'Yes' / 'No', leaving anything else as-is."""
    if not text:
        return "N/A"
    upper = text.strip().upper()
    if upper.startswith("Y"):
        return "Yes"
    if upper.startswith("N"):
        return "No"
    return text.strip()


def parse_extraction(answer: str | None) -> list[str]:
    """
    Split a reply into the 15 extracted values.

    The model occasionally wraps its answer in a code fence or adds a stray line,
    so the line containing the most pipe characters is taken as the data line.
    Short replies are padded with N/A rather than raising.
    """
    if not answer:
        return ["N/A"] * 15

    answer = answer.replace("```text", "").replace("```", "").strip()
    best_line = max(answer.split("\n"), key=lambda line: line.count("|"))
    parts = [part.strip() for part in best_line.split("|")]
    while len(parts) < 15:
        parts.append("N/A")

    values = [part if part else "N/A" for part in parts[:15]]
    for index in YES_NO_RANGE:
        values[index] = normalize_yes_no(values[index])
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", default=str(WORK_DIR / "05_include_list.xlsx"))
    parser.add_argument("--pdf-dir", default=str(RELEASE_ROOT / "input" / "papers"))
    parser.add_argument("--output", default=str(WORK_DIR / "06_extraction.xlsx"))
    parser.add_argument("--autosave", type=int, default=2, help="save every N processed records")
    parser.add_argument("--delay", type=float, default=3.0, help="seconds to wait between requests")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(
            f"ERROR: include list not found: {input_path}\n"
            "This file is produced manually - see README.md, 'Manual steps in the pipeline'."
        )

    pdf_dir = Path(args.pdf_dir)
    output_path = Path(args.output)

    frame = pd.read_excel(output_path) if output_path.exists() else pd.read_excel(input_path)
    for column in EXTRACTION_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA

    system, template, params = load_prompt("data_extraction")

    total = len(frame)
    processed = 0
    for position, (index, row) in enumerate(frame.iterrows(), start=1):
        pdf_name = cell_text(row.get("Pdf name"))
        if not pdf_name:
            continue

        # Resume: skip rows that already hold a real extraction result.
        existing = cell_text(row.get("Robot platform"))
        if existing and existing not in ("PDF not found", "PDF unreadable", "API error"):
            continue

        pdf_path = pdf_dir / f"{pdf_name}.pdf"
        if not pdf_path.exists():
            pdf_path = pdf_dir / pdf_name
        if not pdf_path.exists():
            print(f"  {position}/{total}  PDF not found -> {pdf_name}")
            frame.at[index, "Robot platform"] = "PDF not found"
            continue

        print(f"  {position}/{total}  processing {pdf_name}...")
        pdf_text = extract_pdf_text(pdf_path)
        if len(pdf_text.strip()) < 100:
            print("    -> PDF unreadable or empty")
            frame.at[index, "Robot platform"] = "PDF unreadable"
            continue

        answer = call_llm(system, template.replace("{record}", pdf_text), params, timeout=300)
        if answer is None:
            print("    -> API error, empty response")
            frame.at[index, "Robot platform"] = "API error"
            continue

        values = parse_extraction(answer)
        for column, value in zip(EXTRACTION_COLUMNS, values):
            frame.at[index, column] = value

        print(f"    -> {values[0][:40]} | {values[1][:30]}")
        processed += 1

        if processed % args.autosave == 0:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_excel(output_path, index=False)

        time.sleep(args.delay)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_excel(output_path, index=False)
    print(f"\nExtracted {processed} record(s).")
    print(f"Written to: {output_path}")


if __name__ == "__main__":
    main()
