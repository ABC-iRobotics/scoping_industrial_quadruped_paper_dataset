"""
Stage 11 - agreement between two codings, written to disk.

WHY THIS EXISTS
    The SISY pipeline's cross-check (double_check.py) printed Hungarian verdicts
    to the console and wrote nothing, so it produced no reproducible artefact and
    was not included in the public release. For this paper that output IS the
    reliability evidence, so it has to be a file.

WHAT IT COMPUTES, PER ITEM
    n                 number of studies coded by both sides
    agree             raw percentage agreement, with a Wilson 95% interval
    prevalence        share of positive codes in each coding
    kappa             Cohen's kappa with an asymptotic 95% interval

WHY PREVALENCE IS REPORTED NEXT TO KAPPA, NOT INSTEAD OF IT
    On a rare item - artefact availability was 3 of 88 in round 1 - two coders
    can agree on 97% of studies and still produce a kappa near zero, because
    chance agreement is almost as high as observed agreement. Reporting kappa
    alone would make excellent agreement look like failure; reporting agreement
    alone would hide that the item carries almost no information. Both, always.
    Where a coding is constant (nobody said yes), kappa is undefined and is
    reported as such rather than as 0.

USAGE
    Inter-pass, whole corpus:
        python scripts/11_agreement.py --a work/rci_A_records.xlsx \
                                       --b work/rci_B_records.xlsx \
                                       --label pass_A_vs_pass_B

    Human validation subsample (the load-bearing one):
        python scripts/11_agreement.py --a work/rci_human_subsample.xlsx \
                                       --b work/rci_A_records.xlsx \
                                       --label human_vs_llm --a-name human --b-name llm

    Both sides need a `Pdf name` column and the nine boolean item columns; only
    studies present in both are compared.

LABELLING - THIS IS NOT OPTIONAL
    human_vs_llm is LLM extraction accuracy measured against a human reference
    standard on a subsample. It is NOT inter-rater reliability between two
    independent human coders, and must never be reported as such.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd

from _common import WORK_DIR, cell_text

# Which columns are binary coded items, rather than metadata or evidence.
# Discovered from the data instead of listed here: this script was written for
# the nine RCI items and silently skipped every capability item when the second
# instrument arrived, then wrote an empty file and exited 0, so the run that
# called it recorded success while measuring nothing.
ITEM_PREFIXES = ("rci", "cap_")
NOT_ITEMS = {"rci_total", "n_capabilities"}
EVIDENCE_SUFFIXES = ("__quote", "__offset", "__verified")


def discover_items(frame_a, frame_b) -> list[str]:
    """Binary item columns present in BOTH frames, in the order A declares them."""
    shared = [c for c in frame_a.columns if c in frame_b.columns]
    return [
        column for column in shared
        if column.startswith(ITEM_PREFIXES)
        and column not in NOT_ITEMS
        and not column.endswith(EVIDENCE_SUFFIXES)
    ]

Z = 1.959963985  # 95%


def as_bool(value) -> bool | None:
    """Read a spreadsheet cell as a boolean code, or None when it is not one."""
    text = cell_text(value).lower()
    if text in ("true", "yes", "y", "1", "1.0"):
        return True
    if text in ("false", "no", "n", "0", "0.0"):
        return False
    return None


def wilson(successes: int, total: int) -> tuple[float, float]:
    """Wilson score interval - behaves sanely at proportions near 0 and 1."""
    if total == 0:
        return (float("nan"), float("nan"))
    p = successes / total
    denominator = 1 + Z ** 2 / total
    centre = (p + Z ** 2 / (2 * total)) / denominator
    half = Z * math.sqrt(p * (1 - p) / total + Z ** 2 / (4 * total ** 2)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def cohen_kappa(pairs: list[tuple[bool, bool]]) -> tuple[float | None, float | None, float | None]:
    """
    Cohen's kappa with an asymptotic 95% interval.

    Returns (None, None, None) when kappa is undefined: that happens when the
    expected agreement is 1, i.e. both coders used a single category throughout.
    A constant coding carries no information about agreement beyond chance, and
    reporting 0 there would read as disagreement when the coders in fact agreed
    on everything.
    """
    n = len(pairs)
    if n == 0:
        return (None, None, None)

    both_yes = sum(1 for a, b in pairs if a and b)
    both_no = sum(1 for a, b in pairs if not a and not b)
    a_yes_b_no = sum(1 for a, b in pairs if a and not b)
    a_no_b_yes = sum(1 for a, b in pairs if not a and b)

    po = (both_yes + both_no) / n
    pa_yes = (both_yes + a_yes_b_no) / n
    pb_yes = (both_yes + a_no_b_yes) / n
    pe = pa_yes * pb_yes + (1 - pa_yes) * (1 - pb_yes)

    if abs(1 - pe) < 1e-12:
        return (None, None, None)

    kappa = (po - pe) / (1 - pe)
    se = math.sqrt(max(po * (1 - po), 0.0) / n) / (1 - pe)
    return (kappa, max(-1.0, kappa - Z * se), min(1.0, kappa + Z * se))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", required=True)
    parser.add_argument("--label", required=True, help="name for the output files")
    parser.add_argument("--a-name", default="A")
    parser.add_argument("--b-name", default="B")
    parser.add_argument("--key", default="Pdf name")
    args = parser.parse_args()

    frame_a = pd.read_excel(args.a).set_index(args.key)
    frame_b = pd.read_excel(args.b).set_index(args.key)
    shared = [k for k in frame_a.index if k in frame_b.index]

    if not shared:
        raise SystemExit(f"ERROR: no studies shared between the two files on '{args.key}'.")

    # A record whose extraction did not finish codes every unread item as
    # "not found". Counting it would enter those defaults as genuine negative
    # codes, and a partial failure on one side would show up as disagreement.
    # Only records that both sides extracted completely are compared.
    not_ok = {}
    for name, frame in ((args.a_name, frame_a), (args.b_name, frame_b)):
        if "status" in frame.columns:
            for key in shared:
                status = cell_text(frame.at[key, "status"]).lower()
                if status != "ok":
                    not_ok.setdefault(key, []).append(f"{name}={status or 'blank'}")
    if not_ok:
        print(f"excluded {len(not_ok)} record(s) not extracted completely on both sides:")
        for key, why in not_ok.items():
            print(f"  {key}: {', '.join(why)}")
        print()
    shared = [k for k in shared if k not in not_ok]
    if not shared:
        raise SystemExit("ERROR: no record was extracted completely on both sides.")

    items = discover_items(frame_a, frame_b)
    if not items:
        raise SystemExit(
            "ERROR: the two files share no binary item columns.\n"
            f"  {Path(args.a).name}: {[c for c in frame_a.columns][:8]} ...\n"
            f"  {Path(args.b).name}: {[c for c in frame_b.columns][:8]} ...\n"
            "Agreement over nothing is not agreement. Refusing to write an "
            "empty table that a caller would record as a success."
        )
    print(f"comparing {len(items)} item(s): {', '.join(items)}\n")

    rows = []
    for item in items:

        pairs = []
        unusable = 0
        for key in shared:
            va, vb = as_bool(frame_a.at[key, item]), as_bool(frame_b.at[key, item])
            if va is None or vb is None:
                unusable += 1
                continue
            pairs.append((va, vb))

        n = len(pairs)
        agree_n = sum(1 for a, b in pairs if a == b)
        lo, hi = wilson(agree_n, n)
        kappa, k_lo, k_hi = cohen_kappa(pairs)

        rows.append({
            "item": item,
            "n": n,
            "uncodable_pairs": unusable,
            "agreement": agree_n / n if n else float("nan"),
            "agreement_lo": lo,
            "agreement_hi": hi,
            f"prevalence_{args.a_name}": (sum(1 for a, _ in pairs if a) / n) if n else float("nan"),
            f"prevalence_{args.b_name}": (sum(1 for _, b in pairs if b) / n) if n else float("nan"),
            "kappa": kappa if kappa is not None else "",
            "kappa_lo": k_lo if k_lo is not None else "",
            "kappa_hi": k_hi if k_hi is not None else "",
            "kappa_note": "" if kappa is not None else "undefined: a coding was constant",
            f"only_{args.a_name}_positive": sum(1 for a, b in pairs if a and not b),
            f"only_{args.b_name}_positive": sum(1 for a, b in pairs if b and not a),
        })

    table = pd.DataFrame(rows)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = WORK_DIR / f"agreement_{args.label}.csv"
    md_path = WORK_DIR / f"agreement_{args.label}.md"
    table.to_csv(csv_path, index=False, encoding="utf-8")

    lines = [
        f"# Agreement: {args.a_name} vs {args.b_name}",
        "",
        f"- Studies compared: **{len(shared)}**",
        f"- `{args.a_name}`: `{Path(args.a).name}`",
        f"- `{args.b_name}`: `{Path(args.b).name}`",
        f"- Excluded as not extracted completely on both sides: **{len(not_ok)}**"
        + (" (" + "; ".join(f"`{k}` {', '.join(v)}" for k, v in not_ok.items()) + ")" if not_ok else ""),
        "",
        "| Item | n | Agreement (95% CI) | "
        f"Prev. {args.a_name} | Prev. {args.b_name} | Cohen's kappa (95% CI) |",
        "|---|---:|---|---:|---:|---|",
    ]
    for row in rows:
        kappa_text = (f"{row['kappa']:.3f} ({row['kappa_lo']:.3f}-{row['kappa_hi']:.3f})"
                      if row["kappa"] != "" else "undefined (constant coding)")
        lines.append(
            f"| `{row['item']}` | {row['n']} | "
            f"{row['agreement'] * 100:.1f}% ({row['agreement_lo'] * 100:.1f}-{row['agreement_hi'] * 100:.1f}) | "
            f"{row[f'prevalence_{args.a_name}'] * 100:.1f}% | "
            f"{row[f'prevalence_{args.b_name}'] * 100:.1f}% | {kappa_text} |"
        )
    lines += [
        "",
        "Prevalence is reported beside kappa because on a rare item the two can",
        "point in opposite directions: high agreement with near-zero kappa means",
        "the coders agreed on almost every study while the item carried little",
        "information, not that they disagreed.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(table.to_string(index=False))
    print(f"\nWritten: {csv_path}\n         {md_path}")


if __name__ == "__main__":
    main()
