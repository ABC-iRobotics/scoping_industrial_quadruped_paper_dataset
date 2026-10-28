#!/usr/bin/env bash
#
# Re-run the RCI instrument under amendment A1 (item 9 tightened).
#
# WHY ONLY THE RCI
#   A1 changed one RCI item, so every RCI record has to be re-extracted. It did
#   not touch the capability instrument, whose only affected record is the one
#   scanned PDF caught by A2 - a single row, patched in place rather than paid
#   for with a three-hour re-run.
#
# THE PRE-AMENDMENT CODING IS KEPT, NOT OVERWRITTEN
#   pass A and pass B move to *_v1 first. The amendment log promises the effect
#   of the change stays auditable, and that promise is only worth something if
#   the earlier numbers still exist. 19-of-87 for item 9 is the evidence that
#   the amendment was needed; deleting it would leave the log asserting a
#   correction nobody can check.
#
# Launch:  mkdir -p work/logs && bash run_rerun_rci.sh > work/logs/10_rerun.log 2>&1
#   (the redirect is evaluated before the script runs, so the directory has to
#   exist first - this cost one failed start already)

set -u

cd "$(dirname "$0")" || exit 1

LOG_DIR="work/logs"
mkdir -p "$LOG_DIR"
STATUS="work/RERUN_STATUS.md"
BASELINE="work/rci_include_list.xlsx"

stamp() { date +"%Y-%m-%d %H:%M:%S"; }

# --- preserve the pre-amendment coding
for tag in A B; do
  for suffix in "_records.xlsx" "_evidence.csv"; do
    if [ -f "work/rci_${tag}${suffix}" ]; then
      mv "work/rci_${tag}${suffix}" "work/rci_${tag}_v1${suffix}"
      echo "kept work/rci_${tag}_v1${suffix}" >&2
    fi
  done
  if [ -d "work/rci_${tag}_raw" ]; then
    rm -rf "work/rci_${tag}_v1_raw"
    mv "work/rci_${tag}_raw" "work/rci_${tag}_v1_raw"
  fi
done

{
  echo "# RCI re-run under amendment A1"
  echo
  echo "Item 9 now requires the artefact to be the authors' own, and excludes"
  echo "publisher supplementary-material boilerplate. Pre-amendment coding is"
  echo "preserved as \`rci_A_v1\` / \`rci_B_v1\`."
  echo
  echo "Started: $(stamp)"
  echo
  echo "| # | Step | Model | Started | Finished | Result |"
  echo "|---|---|---|---|---|---|"
} > "$STATUS"

run_step() {
  local number="$1" name="$2" model="$3" log="$4"
  shift 4
  local started finished
  started="$(stamp)"
  echo "=== [$number] $name ($model) started $started ===" >&2
  if LLM_MODEL="$model" python -u "$@" > "$LOG_DIR/$log" 2>&1; then
    finished="$(stamp)"
    echo "| $number | $name | \`$model\` | $started | $finished | ok |" >> "$STATUS"
  else
    finished="$(stamp)"
    echo "| $number | $name | \`$model\` | $started | $finished | **FAILED** - \`$log\` |" >> "$STATUS"
  fi
  echo "=== [$number] done $(stamp) ===" >&2
}

run_step 1 "RCI pass A, amended item 9" "gpt-oss:120b" "11_rci_A_v2.log" \
  scripts/10_rci_extraction.py --input "$BASELINE" --pass A

run_step 2 "RCI pass B, amended item 9" "qwen3.6:35b-a3b" "12_rci_B_v2.log" \
  scripts/10_rci_extraction.py --input "$BASELINE" --pass B

if [ -f work/rci_A_records.xlsx ] && [ -f work/rci_B_records.xlsx ]; then
  run_step 3 "Inter-pass agreement, RCI" "n/a" "13_agree_rci_v2.log" \
    scripts/11_agreement.py --a work/rci_A_records.xlsx --b work/rci_B_records.xlsx \
      --label rci_pass_A_vs_B --a-name gpt-oss120b --b-name qwen3.6
fi

# The point of the whole exercise: what did the amendment actually change?
if [ -f work/rci_A_v1_records.xlsx ] && [ -f work/rci_A_records.xlsx ]; then
  run_step 4 "Amendment effect, pass A before vs after" "n/a" "14_amendment_effect.log" \
    scripts/11_agreement.py --a work/rci_A_v1_records.xlsx --b work/rci_A_records.xlsx \
      --label amendment_A1_effect --a-name before --b-name after
fi

{
  echo
  echo "Finished: $(stamp)"
  echo
  echo 'Read `work/agreement_amendment_A1_effect.md` first: it is the'
  echo 'before-and-after for every item. Item 9 should move substantially and'
  echo 'the other eight should barely move. If an untouched item shifts, the'
  echo 'run-to-run non-determinism is larger than the amendment, and that is'
  echo 'worth knowing before any of it is reported.'
} >> "$STATUS"
