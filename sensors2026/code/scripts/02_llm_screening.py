"""
Stage 2 - two-round LLM-assisted title/abstract screening.

WHAT IT DOES
    Round 1  Screens every deduplicated record on title + abstract and records a
             single-letter decision: Y (include), N (exclude), U (uncertain).
             Only the first character of the model's reply is kept, matching the
             original run.
    Filter   Keeps the Y and U records for the second round; N records stop here.
    Round 2  Re-screens the surviving records against a more detailed criteria
             set and records Include / Exclude / Maybe plus a one-sentence
             reason and a short extracted note.

    Both rounds are resumable: rows that already carry a decision are skipped, so
    the script can be interrupted and restarted. Progress is written to disk
    every `--autosave` records.

INPUTS
    work/02_deduplicated.xlsx   output of 01_deduplicate.py
    prompts/abstract_screening_round1.md
    prompts/abstract_screening_round2.md
    LLM_API_KEY in the environment or in .env

OUTPUTS
    work/03_screening_round1.xlsx   all records, with the round 1 decision
    work/04_screening_round2.xlsx   Y/U records only, with the round 2 decision

PAPER REFERENCE
    Section II-D (Study Selection). Round 1 produces the "Records excluded" and
    "Reports sought for retrieval" boxes of the PRISMA-ScR flow diagram in Fig. 1;
    round 2 feeds the eligibility assessment.

CONSOLIDATED FROM
    ai_screening.py (round 1), filteringByDecision.py (the Y/U filter) and
    final_decision.py (round 2) in the original working directory. Despite its
    name, final_decision.py implemented the second screening round, not the
    final inclusion decision - that was made manually afterwards.

NOTE ON REPRODUCIBILITY
    No random seed was set and the endpoint does not expose one, so re-running
    this stage will not reproduce the published decisions exactly. See the note
    in _common.py and README.md, "Reproducing the pipeline".

NOTE ON THE MANUAL STEP THAT FOLLOWS
    The transition from this stage's output to the full-text extraction input was
    manual: the primary reviewer assessed the round 2 output, removed records
    whose full text could not be retrieved, made the final inclusion decision,
    and matched each included study to a downloaded PDF. That step is not
    scripted and is not reproducible from this repository. See README.md,
    "Manual steps in the pipeline".
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from _common import WORK_DIR, call_llm, cell_text, load_prompt

ROUND1_COLUMN = "Decision round 1 (gpt-oss:120b)"
ROUND2_COLUMN = "Decision (gpt-oss:120b)"
ROUND2_REASON = "Reason"
ROUND2_NOTE = "Extracted note"

ROUND1_VALID = {"Y", "N", "U"}
ROUND2_VALID = {"Include", "Exclude", "Maybe"}


def record_text(row: pd.Series) -> str:
    """Format one record the way both screening prompts expect it."""
    title = cell_text(row.get("Title"))
    abstract = cell_text(row.get("Abstract"))
    return f"Title: {title} _Abstract: {abstract}"


def parse_round2(answer: str) -> tuple[str, str, str]:
    """
    Split a round 2 reply into (decision, reason, note).

    Anything that does not start with a recognised decision word is recorded as
    Maybe, with the raw reply preserved in the reason field so that unexpected
    model output stays visible in the data rather than being silently dropped.
    """
    parts = [part.strip() for part in answer.split("|")]
    decision = parts[0] if parts else "Maybe"
    reason = parts[1] if len(parts) > 1 else ""
    note = parts[2] if len(parts) > 2 else ""

    lowered = decision.lower()
    if lowered.startswith("include"):
        return "Include", reason, note
    if lowered.startswith("exclude"):
        return "Exclude", reason, note
    if lowered.startswith("maybe"):
        return "Maybe", reason, note
    return "Maybe", f"Unexpected model output: {answer}", ""


def save(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_excel(path, index=False)


def run_round1(frame: pd.DataFrame, output: Path, autosave: int) -> pd.DataFrame:
    system, template, params = load_prompt("abstract_screening_round1")

    if ROUND1_COLUMN not in frame.columns:
        frame[ROUND1_COLUMN] = pd.NA

    total = len(frame)
    for position, (index, row) in enumerate(frame.iterrows(), start=1):
        existing = cell_text(row.get(ROUND1_COLUMN))
        if existing in ROUND1_VALID:
            continue

        answer = call_llm(system, template.replace("{record}", record_text(row)), params)
        # The original run kept only the leading decision letter.
        decision = answer[0].upper() if answer else "U"
        if decision not in ROUND1_VALID:
            decision = "U"
        frame.at[index, ROUND1_COLUMN] = decision

        print(f"  round 1  {position}/{total} -> {decision}")
        if position % autosave == 0:
            save(frame, output)

    save(frame, output)
    return frame


def run_round2(frame: pd.DataFrame, output: Path, autosave: int) -> pd.DataFrame:
    system, template, params = load_prompt("abstract_screening_round2")

    for column in (ROUND2_COLUMN, ROUND2_REASON, ROUND2_NOTE):
        if column not in frame.columns:
            frame[column] = pd.NA

    total = len(frame)
    for position, (index, row) in enumerate(frame.iterrows(), start=1):
        existing = cell_text(row.get(ROUND2_COLUMN))
        if existing in ROUND2_VALID:
            continue

        title = cell_text(row.get("Title"))
        abstract = cell_text(row.get("Abstract"))
        if not title and not abstract:
            print(f"  round 2  {position}/{total} -> skipped (no title or abstract)")
            continue

        answer = call_llm(system, template.replace("{record}", record_text(row)), params)
        if answer is None:
            decision, reason, note = "Maybe", "No response from API.", ""
        else:
            decision, reason, note = parse_round2(answer)

        frame.at[index, ROUND2_COLUMN] = decision
        frame.at[index, ROUND2_REASON] = reason
        frame.at[index, ROUND2_NOTE] = note

        print(f"  round 2  {position}/{total} -> {decision}")
        if position % autosave == 0:
            save(frame, output)

    save(frame, output)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", default=str(WORK_DIR / "02_deduplicated.xlsx"))
    parser.add_argument("--round1-output", default=str(WORK_DIR / "03_screening_round1.xlsx"))
    parser.add_argument("--round2-output", default=str(WORK_DIR / "04_screening_round2.xlsx"))
    parser.add_argument("--autosave", type=int, default=1, help="save every N records")
    parser.add_argument(
        "--only",
        choices=["round1", "round2", "both"],
        default="both",
        help="run only one round (default: both)",
    )
    args = parser.parse_args()

    round1_output = Path(args.round1_output)
    round2_output = Path(args.round2_output)

    if args.only in ("round1", "both"):
        source = round1_output if round1_output.exists() else Path(args.input)
        if not source.exists():
            raise SystemExit(f"ERROR: input not found: {source}\nRun 01_deduplicate.py first.")
        print(f"Round 1 - screening from {source}")
        frame = run_round1(pd.read_excel(source), round1_output, args.autosave)

        counts = frame[ROUND1_COLUMN].value_counts().to_dict()
        print(f"\nRound 1 decisions: {counts}")
        print(f"Written to: {round1_output}")

    if args.only in ("round2", "both"):
        if round2_output.exists():
            source_frame = pd.read_excel(round2_output)
            print(f"\nRound 2 - resuming from {round2_output}")
        else:
            if not round1_output.exists():
                raise SystemExit(f"ERROR: {round1_output} not found. Run round 1 first.")
            source_frame = pd.read_excel(round1_output)
            kept = source_frame[ROUND1_COLUMN].astype(str).str.strip().str.upper()
            source_frame = source_frame[kept.isin({"Y", "U"})].copy()
            print(f"\nRound 2 - {len(source_frame)} records carried over from round 1 (Y/U)")

        frame = run_round2(source_frame, round2_output, args.autosave)

        counts = frame[ROUND2_COLUMN].value_counts().to_dict()
        print(f"\nRound 2 decisions: {counts}")
        print(f"Written to: {round2_output}")


if __name__ == "__main__":
    main()
