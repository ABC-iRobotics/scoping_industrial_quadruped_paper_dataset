"""LLM extraction accuracy against the blind human reference standard.

The validation subsample (validation_sample.md; 18 baseline + 5 round-2 studies
after amendment A5 and the r2-0581 exclusion) was coded by P.Z. from the full
texts without seeing any model output. This compares that coding, item by item,
with each extraction pass.

WHAT IT IS AND IS NOT
    Accuracy of LLM extraction measured against one human reference coder on a
    random subsample. It is NOT inter-rater reliability between two independent
    human coders and must never be reported as such (CLAUDE.md section 6).

WHAT IS COMPARED
    - the nine RCI items and the seven capability items (binary): agreement with
      a Wilson 95% interval, prevalence on each side, Cohen's kappa with an
      asymptotic interval (undefined where a side is constant);
    - sensor_specificity and compute_specificity (three-level ordinal): exact
      agreement with a Wilson interval and linearly weighted kappa;
    - eval_environment_kind (nominal): exact agreement.

    A study is compared on an item only when the human coded it and the pass
    extracted that study completely (status ok). Excluded pairs are counted.

INPUTS
    work/validation/validation_coding_baseline_v2.xlsx   the human coding
    work/{rci,cap}_{A,B}_records.xlsx                      baseline passes
    work/{rci,cap}_{A,B}_r2_records.xlsx                   round-2 passes

OUTPUTS
    work/validation_accuracy.csv, work/validation_accuracy.md

USAGE
    python scripts/37_validation_accuracy.py
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from _common import WORK_DIR, cell_text

Z = 1.959963985
HUMAN = WORK_DIR / "validation" / "validation_coding_baseline_v2.xlsx"
SPEC = ["unspecified", "modality", "model"]


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + Z ** 2 / n
    c = (p + Z ** 2 / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z ** 2 / (4 * n ** 2)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def kappa_binary(pairs):
    n = len(pairs)
    if n == 0:
        return (None, None, None)
    a1 = sum(a for a, _ in pairs) / n
    b1 = sum(b for _, b in pairs) / n
    po = sum(a == b for a, b in pairs) / n
    pe = a1 * b1 + (1 - a1) * (1 - b1)
    if abs(1 - pe) < 1e-12:
        return (None, None, None)
    k = (po - pe) / (1 - pe)
    se = math.sqrt(max(po * (1 - po), 0.0) / n) / (1 - pe)
    return (k, max(-1.0, k - Z * se), min(1.0, k + Z * se))


def kappa_linear(pairs, levels):
    """Linearly weighted kappa for ordinal codes; point estimate only."""
    n = len(pairs)
    if n == 0:
        return None
    m = len(levels) - 1
    idx = {v: i for i, v in enumerate(levels)}
    w = lambda i, j: 1 - abs(i - j) / m
    po = sum(w(idx[a], idx[b]) for a, b in pairs) / n
    pa = [sum(idx[a] == i for a, _ in pairs) / n for i in range(len(levels))]
    pb = [sum(idx[b] == j for _, b in pairs) / n for j in range(len(levels))]
    pe = sum(w(i, j) * pa[i] * pb[j] for i in range(len(levels)) for j in range(len(levels)))
    return None if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)


def as_bool(v):
    t = cell_text(v).lower()
    if t in ("yes", "true", "1", "1.0"):
        return True
    if t in ("no", "false", "0", "0.0"):
        return False
    return None


def load_pass(tool: str, label: str) -> pd.DataFrame:
    combined = WORK_DIR / f"{tool}_{label}_all_records.xlsx"
    if combined.exists():
        return pd.read_excel(combined).set_index("Pdf name")
    frames = []
    for suffix in ("", "_r2"):
        p = WORK_DIR / f"{tool}_{label}{suffix}_records.xlsx"
        if p.exists():
            frames.append(pd.read_excel(p))
    f = pd.concat(frames, ignore_index=True).drop_duplicates("Pdf name", keep="last")
    return f.set_index("Pdf name")


def main() -> None:
    human = pd.read_excel(HUMAN, sheet_name="coding")
    human = human[human["rci1_platform_model"].notna()
                  & ~human["notes"].astype(str).str.contains("NOT CODED", na=False)].set_index("record_id")
    print(f"human-coded studies: {len(human)}")

    rows = []
    for label in ("A", "B"):
        tools = {t: load_pass(t, label) for t in ("rci", "cap")}
        # "<item>__blind" columns hold the coder's original code where it was
        # later corrected to the written rule; they are reported as a
        # sensitivity row against the same model column.
        items = [c for c in human.columns
                 if c.startswith(("rci", "cap_")) and ("__" not in c or c.endswith("__blind"))]
        for item in items:
            base = item.removesuffix("__blind")
            tool = tools["rci" if base.startswith("rci") else "cap"]
            if base not in tool.columns:
                continue
            pairs, skipped = [], 0
            for sid in human.index:
                h = as_bool(human.at[sid, item])
                if h is None or sid not in tool.index or cell_text(tool.at[sid, "status"]).lower() != "ok":
                    skipped += 1
                    continue
                m = as_bool(tool.at[sid, base])
                if m is None:
                    skipped += 1
                    continue
                pairs.append((h, m))
            n = len(pairs)
            agree = sum(a == b for a, b in pairs)
            lo, hi = wilson(agree, n)
            k, klo, khi = kappa_binary(pairs)
            rows.append({
                "pass": label, "item": item, "type": "binary", "n": n, "not_compared": skipped,
                "agreement": agree / n if n else float("nan"), "agree_lo": lo, "agree_hi": hi,
                "prev_human": sum(a for a, _ in pairs) / n if n else float("nan"),
                "prev_llm": sum(b for _, b in pairs) / n if n else float("nan"),
                "kappa": k, "kappa_lo": klo, "kappa_hi": khi,
                "human_only_yes": sum(a and not b for a, b in pairs),
                "llm_only_yes": sum(b and not a for a, b in pairs),
            })

        rci = tools["rci"]
        for item, levels in (("sensor_specificity", SPEC), ("compute_specificity", SPEC),
                             ("eval_environment_kind", None)):
            pairs, skipped = [], 0
            for sid in human.index:
                h = cell_text(human.at[sid, item]).lower()
                if not h or sid not in rci.index or cell_text(rci.at[sid, "status"]).lower() != "ok":
                    skipped += 1
                    continue
                m = cell_text(rci.at[sid, item]).lower()
                if not m or (levels and (h not in levels or m not in levels)):
                    skipped += 1
                    continue
                pairs.append((h, m))
            n = len(pairs)
            agree = sum(a == b for a, b in pairs)
            lo, hi = wilson(agree, n)
            rows.append({
                "pass": label, "item": item, "type": "ordinal" if levels else "nominal",
                "n": n, "not_compared": skipped,
                "agreement": agree / n if n else float("nan"), "agree_lo": lo, "agree_hi": hi,
                "kappa": kappa_linear(pairs, levels) if levels else None,
            })

    table = pd.DataFrame(rows)
    table.to_csv(WORK_DIR / "validation_accuracy.csv", index=False)

    def fmt(v, pct=False):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return "n/a"
        return f"{v*100:.1f}%" if pct else f"{v:.3f}"

    lines = ["# LLM extraction accuracy against the blind human reference (one coder)", "",
             f"Human-coded studies: {len(human)}. Accuracy of LLM extraction against a single "
             "human reference coder on a random subsample - not inter-rater reliability "
             "between independent human coders.", ""]
    for label in ("A", "B"):
        t = table[table["pass"] == label]
        lines += [f"## Pass {label}", "",
                  "| Item | n | Agreement (95% CI) | Prev. human | Prev. LLM | kappa (95% CI) | human-only yes | LLM-only yes |",
                  "|---|---:|---|---:|---:|---|---:|---:|"]
        for _, r in t.iterrows():
            ci = f"{fmt(r.agreement, True)} ({fmt(r.agree_lo, True)}-{fmt(r.agree_hi, True)})"
            if r["type"] == "binary":
                kap = (f"{fmt(r.kappa)} ({fmt(r.kappa_lo)}-{fmt(r.kappa_hi)})"
                       if r.kappa is not None and not pd.isna(r.kappa) else "undefined")
                lines.append(f"| `{r["item"]}` | {r.n} | {ci} | {fmt(r.prev_human, True)} | "
                             f"{fmt(r.prev_llm, True)} | {kap} | {int(r.human_only_yes)} | {int(r.llm_only_yes)} |")
            else:
                kap = f"weighted {fmt(r.kappa)}" if r["type"] == "ordinal" and r.kappa is not None and not pd.isna(r.kappa) else "-"
                lines.append(f"| `{r["item"]}` ({r["type"]}) | {r.n} | {ci} | - | - | {kap} | - | - |")
        lines.append("")
    (WORK_DIR / "validation_accuracy.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
