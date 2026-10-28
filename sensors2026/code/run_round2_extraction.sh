#!/usr/bin/env bash
# Round-2 extraction over the 19 studies P.Z. included at full text (19 Oct 2026).
# Same instruments, models and procedure as the baseline: each pass runs with the
# prompt's own max_tokens, then incomplete records are retried once with
# LLM_MAX_TOKENS=8000 (the override is printed into the log). Strictly one job at
# a time - the gateway serialises model loading. Outputs use the pass labels
# A_r2 / B_r2 so the baseline record files are never touched.
set -u
cd "$(dirname "$0")"
PY="${PY:-python}"
mkdir -p work/logs
IN=work/r2_include_list.xlsx
PDF=work/pdf_round2
STATUS=work/ROUND2_EXTRACTION_STATUS.md
echo "# Round-2 extraction - started $(date -Iseconds)" > "$STATUS"

step() {  # name, log, command...
  local name=$1 log=$2; shift 2
  echo "- $name: running ($(date -Iseconds))" >> "$STATUS"
  "$@" > "work/logs/$log" 2>&1
  local rc=$?
  echo "- $name: exit $rc ($(date -Iseconds))" >> "$STATUS"
}

step "rci A_r2"          70_rci_A_r2.log      env LLM_MODEL=gpt-oss:120b $PY scripts/10_rci_extraction.py        --input $IN --pdf-dir $PDF --pass A_r2
step "cap A_r2"          71_cap_A_r2.log      env LLM_MODEL=gpt-oss:120b $PY scripts/12_capability_extraction.py --input $IN --pdf-dir $PDF --pass A_r2
step "rci A_r2 retry"    72_rci_A_r2_retry.log env LLM_MODEL=gpt-oss:120b LLM_MAX_TOKENS=8000 $PY scripts/10_rci_extraction.py        --input $IN --pdf-dir $PDF --pass A_r2
step "cap A_r2 retry"    73_cap_A_r2_retry.log env LLM_MODEL=gpt-oss:120b LLM_MAX_TOKENS=8000 $PY scripts/12_capability_extraction.py --input $IN --pdf-dir $PDF --pass A_r2
step "rci B_r2"          74_rci_B_r2.log      env LLM_MODEL=Qwen3.8-Flash-Next $PY scripts/10_rci_extraction.py        --input $IN --pdf-dir $PDF --pass B_r2
step "cap B_r2"          75_cap_B_r2.log      env LLM_MODEL=Qwen3.8-Flash-Next $PY scripts/12_capability_extraction.py --input $IN --pdf-dir $PDF --pass B_r2
step "rci B_r2 retry"    76_rci_B_r2_retry.log env LLM_MODEL=Qwen3.8-Flash-Next LLM_MAX_TOKENS=8000 $PY scripts/10_rci_extraction.py        --input $IN --pdf-dir $PDF --pass B_r2
step "cap B_r2 retry"    77_cap_B_r2_retry.log env LLM_MODEL=Qwen3.8-Flash-Next LLM_MAX_TOKENS=8000 $PY scripts/12_capability_extraction.py --input $IN --pdf-dir $PDF --pass B_r2
echo "- done $(date -Iseconds)" >> "$STATUS"
