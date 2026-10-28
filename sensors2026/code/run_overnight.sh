#!/usr/bin/env bash
#
# Unattended run: screening, then the four extraction passes over the baseline.
#
# ORDER IS NOT ARBITRARY.
#   1. Screening comes first because it is the only step whose output unblocks a
#      human: the include list decides which full texts have to be retrieved.
#   2. The two pass-A jobs follow, both on gpt-oss:120b.
#   3. The two pass-B jobs run last, both on qwen3.6:35b-a3b.
#   Grouping by model means ONE model switch across the whole night. The gateway
#   serialises model loading - a cold 26B load measured 247 s - so interleaving
#   would pay that cost four times and could stall a job behind a reload.
#
# NOTHING RUNS IN PARALLEL, for the same reason. Concurrency against this
# endpoint produced `busy` retries and one 400 during earlier probing.
#
# EVERY STAGE IS RESUMABLE. The extraction scripts skip records already marked
# `ok` and retry anything `incomplete`; the screening script skips rows that
# already carry a decision. A failed step does not abort the chain: the run
# continues and the failure is recorded, so one bad stage does not cost the
# whole night.

set -u

cd "$(dirname "$0")" || exit 1

LOG_DIR="work/logs"
mkdir -p "$LOG_DIR"
STATUS="work/OVERNIGHT_STATUS.md"

BASELINE="work/rci_include_list.xlsx"     # the 88 studies whose PDFs exist
SCREEN_IN="work/r2_03_to_screen.xlsx"     # the 1,549 new records

stamp() { date +"%Y-%m-%d %H:%M:%S"; }

{
  echo "# Overnight run"
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
  echo "=== [$number] $name  ($model)  started $started ===" >&2

  if LLM_MODEL="$model" python -u "$@" > "$LOG_DIR/$log" 2>&1; then
    finished="$(stamp)"
    echo "| $number | $name | \`$model\` | $started | $finished | ok |" >> "$STATUS"
    echo "=== [$number] $name  DONE $finished ===" >&2
  else
    finished="$(stamp)"
    echo "| $number | $name | \`$model\` | $started | $finished | **FAILED** - see \`$log\` |" >> "$STATUS"
    echo "=== [$number] $name  FAILED $finished ===" >&2
  fi
}

run_step 1 "Title/abstract screening, 1549 new records" "gpt-oss:120b" "01_screening.log" \
  scripts/02_llm_screening.py \
    --input "$SCREEN_IN" \
    --round1-output work/r2_04_screening_round1.xlsx \
    --round2-output work/r2_05_screening_round2.xlsx

run_step 2 "RCI extraction, pass A, baseline 88" "gpt-oss:120b" "02_rci_A.log" \
  scripts/10_rci_extraction.py --input "$BASELINE" --pass A

run_step 3 "Capability extraction, pass A, baseline 88" "gpt-oss:120b" "03_cap_A.log" \
  scripts/12_capability_extraction.py --input "$BASELINE" --pass A

run_step 4 "RCI extraction, pass B, baseline 88" "qwen3.6:35b-a3b" "04_rci_B.log" \
  scripts/10_rci_extraction.py --input "$BASELINE" --pass B

run_step 5 "Capability extraction, pass B, baseline 88" "qwen3.6:35b-a3b" "05_cap_B.log" \
  scripts/12_capability_extraction.py --input "$BASELINE" --pass B

# Agreement is computed only if both passes of an instrument produced a file.
# It is cheap, local, and it is the first thing worth reading in the morning.
if [ -f work/rci_A_records.xlsx ] && [ -f work/rci_B_records.xlsx ]; then
  run_step 6 "Inter-pass agreement, RCI" "n/a" "06_agree_rci.log" \
    scripts/11_agreement.py --a work/rci_A_records.xlsx --b work/rci_B_records.xlsx \
      --label rci_pass_A_vs_B --a-name gpt-oss120b --b-name qwen3.6
fi

if [ -f work/cap_A_records.xlsx ] && [ -f work/cap_B_records.xlsx ]; then
  run_step 7 "Inter-pass agreement, capabilities" "n/a" "07_agree_cap.log" \
    scripts/11_agreement.py --a work/cap_A_records.xlsx --b work/cap_B_records.xlsx \
      --label cap_pass_A_vs_B --a-name gpt-oss120b --b-name qwen3.6
fi

{
  echo
  echo "Finished: $(stamp)"
  echo
  echo "## What to read first"
  echo
  echo '- `work/OVERNIGHT_STATUS.md` (this file) for what ran and what failed'
  echo '- `work/agreement_rci_pass_A_vs_B.md` and `work/agreement_cap_pass_A_vs_B.md`'
  echo '  for where the two models disagree - those records are the adjudication set'
  echo '- `work/r2_05_screening_round2.xlsx` for the records that survived screening'
  echo '- each stage prints a quote check; anything below 100% verbatim needs a look'
  echo
  echo 'Nothing here is a finding until a human has adjudicated the disagreements'
  echo 'and coded the blind subsample. These are machine passes, not results.'
} >> "$STATUS"

echo "ALL STEPS ATTEMPTED - see $STATUS" >&2
