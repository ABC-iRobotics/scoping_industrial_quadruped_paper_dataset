#!/usr/bin/env bash
#
# Amendments A3 and A4 (26 September 2026): re-run full-text eligibility with the
# clarified Context criterion, and re-run pass B over the whole corpus with
# Qwen3.8-Flash-Next after the endpoint withdrew qwen3.6:35b-a3b.
#
# ORDER.
#   1-2. Full-text eligibility first, both passes: its output is the only thing
#        that unblocks a human (P.Z. decides every round-2 record), and the
#        round-2 RCI/capability extraction cannot start until she has.
#   3-4. Baseline pass B, both instruments, on the new model.
#   5-6. Agreement, local and cheap.
#   Grouped by model: pass A (gpt-oss:120b) once, then Qwen3.8-Flash-Next for
#   everything else, so the model switches once.
#
# NOTHING RUNS IN PARALLEL. The gateway serialises model loading; concurrent
# calls produced `busy` retries and a 400 during earlier probing.
#
# EVERY STAGE IS RESUMABLE. A failed step does not abort the chain; it is
# recorded and the next step runs. Re-running this script picks up where the
# previous run stopped.
#
# NOT RUN HERE, deliberately: 30_adjudication_package.py and the eligibility
# decision workbook (13_fulltext_eligibility.py --build-sheet). Both are built
# once, by hand, after the machine passes are checked.

set -u

cd "$(dirname "$0")" || exit 1

LOG_DIR="work/logs"
mkdir -p "$LOG_DIR"
STATUS="work/PASSB_FLASH_STATUS.md"

BASELINE="work/rci_include_list.xlsx"
MODEL_A="gpt-oss:120b"
MODEL_B="Qwen3.8-Flash-Next"

stamp() { date +"%Y-%m-%d %H:%M:%S"; }

{
  echo "# Pass-B re-run (amendments A3, A4)"
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

run_step 1 "Full-text eligibility, pass A, round 2" "$MODEL_A" "31_fte_A.log" \
  scripts/13_fulltext_eligibility.py --pass A

run_step 2 "Full-text eligibility, pass B, round 2" "$MODEL_B" "32_fte_B.log" \
  scripts/13_fulltext_eligibility.py --pass B

run_step 3 "RCI extraction, pass B, baseline 88" "$MODEL_B" "33_rci_B_flash.log" \
  scripts/10_rci_extraction.py --input "$BASELINE" --pass B

run_step 4 "Capability extraction, pass B, baseline 88" "$MODEL_B" "34_cap_B_flash.log" \
  scripts/12_capability_extraction.py --input "$BASELINE" --pass B

if [ -f work/rci_A_records.xlsx ] && [ -f work/rci_B_records.xlsx ]; then
  run_step 5 "Inter-pass agreement, RCI" "n/a" "35_agree_rci_flash.log" \
    scripts/11_agreement.py --a work/rci_A_records.xlsx --b work/rci_B_records.xlsx \
      --label rci_pass_A_vs_Bflash --a-name gpt-oss120b --b-name qwen3.8-flash-next
fi

if [ -f work/cap_A_records.xlsx ] && [ -f work/cap_B_records.xlsx ]; then
  run_step 6 "Inter-pass agreement, capabilities" "n/a" "36_agree_cap_flash.log" \
    scripts/11_agreement.py --a work/cap_A_records.xlsx --b work/cap_B_records.xlsx \
      --label cap_pass_A_vs_Bflash --a-name gpt-oss120b --b-name qwen3.8-flash-next
fi

{
  echo
  echo "Finished: $(stamp)"
  echo
  echo 'Machine passes only. Nothing here is a finding until P.Z. has made the'
  echo 'eligibility decisions, adjudicated the disagreements and coded the blind subsample.'
} >> "$STATUS"
