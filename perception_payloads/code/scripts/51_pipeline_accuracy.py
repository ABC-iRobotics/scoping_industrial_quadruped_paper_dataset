"""
Stage 51 - how accurate is the charting pipeline as run, against the blind
human reference, and where do its errors come from?

37_validation_accuracy.py compares each model pass with the human. This
stage compares what the pipeline actually produced - the agreed pass code, or
the human adjudication where the passes disagreed - before the validation
studies' codes are replaced by the human ones (42_build_final.py). Splitting
by route shows the two error sources the design has:

    agreed     both passes gave the same code and no human saw it; an error
               here is a correlated model error
    adjudicated the passes disagreed and P.Z. decided from the quotes (stage 30);
               an error here is an adjudication error

The re-adjudication with context (stage 43) excluded the validation studies,
so the adjudicated route here is the quote-only one; this is the measurement
that motivated amendment A11.

OUTPUTS
    work/pipeline_vs_human.csv   per item: n, agreed, agreed wrong (FP/FN),
                                 adjudicated, adjudicated wrong, pipeline
                                 positives, human positives
    work/pipeline_numbers.csv    macro,value - read by 40_emit_numbers.py
"""
from __future__ import annotations

import pandas as pd

from _common import WORK_DIR


def b(v):
    t = str(v).strip().lower()
    return True if t in ("yes", "true", "1", "1.0") else False if t in ("no", "false", "0", "0.0") else None


def class_validation(human: pd.DataFrame) -> dict:
    """
    The RQ1 and RQ3 variables are classes derived from free-text strings, not
    yes/no items, so Table 5 does not cover them. Here the classes the pipeline
    strings map to (pass A, pass B where pass A listed none) are compared with
    the classes the blind human strings map to, through the same signed
    codebooks, per class and study. Writes work/class_validation.csv.
    """
    import importlib.util
    import re
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("bf", Path(__file__).with_name("42_build_final.py"))
    bf = importlib.util.module_from_spec(spec); spec.loader.exec_module(bf)
    spec = importlib.util.spec_from_file_location("res", Path(__file__).with_name("50_results.py"))
    res = importlib.util.module_from_spec(spec); spec.loader.exec_module(res)
    a = pd.read_excel(WORK_DIR / "rci_A_all_records.xlsx").set_index("Pdf name")
    bb = pd.read_excel(WORK_DIR / "rci_B_all_records.xlsx").set_index("Pdf name")
    rows, out = [], {}
    for field, book_name, classes in (("optical_sensors_raw", "sensors", res.MODALITY),
                                      ("onboard_computer_raw", "compute", res.COMPUTE)):
        book = bf.codebook(book_name)
        pairs = []
        for sid in human.index:
            if sid not in a.index or str(a.at[sid, "status"]).lower() != "ok":
                continue
            raw = a.at[sid, field] if str(a.at[sid, field]) not in ("nan", "") else bb.at[sid, field]
            p_cls = set(bf.classes_for(raw, book)[0].split("; ")) & set(classes)
            h_cls = set(bf.classes_for(human.at[sid, field], book)[0].split("; ")) & set(classes)
            pairs.append((p_cls, h_cls))
        for c in classes:
            n = len(pairs); both = sum(c in p and c in h for p, h in pairs)
            ponly = sum(c in p and c not in h for p, h in pairs); honly = sum(c in h and c not in p for p, h in pairs)
            agree = n - ponly - honly
            po = agree / n
            pp, ph = (both + ponly) / n, (both + honly) / n
            pe = pp * ph + (1 - pp) * (1 - ph)
            kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
            rows.append(dict(field=book_name, cls=c, n=n, agreement=po, kappa=kappa, human_yes=both + honly,
                             pipeline_yes=both + ponly, pipeline_only=ponly, human_only=honly))
        none_agree = sum((len(p) == 0) == (len(h) == 0) for p, h in pairs) / len(pairs)
        out[f"ClassNoneAgree{book_name.capitalize()}"] = f"{100 * none_agree:.0f}"
    t = pd.DataFrame(rows)
    t.to_csv(WORK_DIR / "class_validation.csv", index=False)
    s = t[(t.field == "sensors") & (t.human_yes + t.pipeline_yes > 0)]
    c = t[(t.field == "compute") & (t.human_yes + t.pipeline_yes > 0)]
    out.update(ClassSensAgreeMin=f"{100 * s.agreement.min():.0f}", ClassSensAgreeMax=f"{100 * s.agreement.max():.0f}",
               ClassCompAgreeMin=f"{100 * c.agreement.min():.0f}", ClassCompAgreeMax=f"{100 * c.agreement.max():.0f}",
               ClassStudies=int(t.n.max()))
    m = t[(t.field == "sensors") & (t.cls == "rgb_camera")].iloc[0]
    out.update(ClassMonoAgree=f"{100 * m.agreement:.0f}", ClassMonoPipe=int(m.pipeline_yes),
               ClassMonoHuman=int(m.human_yes))
    print(t.round(2).to_string(index=False))
    return out


def screening_recall() -> dict:
    """
    Recall of the title/abstract screening procedure, estimated on a known
    gold set: the round-2 screening (02_llm_screening.py, same prompts and
    model) re-run on the 88 earlier studies, all of which were included.
    A study is retained if round 1 did not say N and round 2 did not say
    Exclude. Reported for all 88 and for the earlier studies that still meet
    the criteria as applied in round 2.
    """
    import math
    from pathlib import Path
    r1 = pd.read_excel(WORK_DIR / "recall_baseline_round1.xlsx").set_index("record_id")
    r2 = pd.read_excel(WORK_DIR / "recall_baseline_round2.xlsx").set_index("record_id")
    lost = set(r1.index[r1["Decision round 1 (gpt-oss:120b)"] == "N"]) | \
        set(r2.index[r2["Decision (gpt-oss:120b)"] == "Exclude"])
    final = pd.read_excel(Path(WORK_DIR).parent.parent / "data" / "charting_v2.xlsx").set_index("record_id")
    flagged = set(final.index[final["fails_current_criteria"].astype(bool)])

    def wilson(k: int, n: int) -> tuple[float, float]:
        z = 1.959963985; p = k / n; den = 1 + z * z / n
        c = (p + z * z / (2 * n)) / den; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
        return c - h, c + h

    n_all, k_all = len(r1), len(r1) - len(lost)
    elig = [s for s in r1.index if s not in flagged]
    k_el = sum(s not in lost for s in elig)
    lo, hi = wilson(k_all, n_all)
    lo2, hi2 = wilson(k_el, len(elig))
    return dict(RecallN=n_all, RecallKept=k_all, RecallPct=f"{100 * k_all / n_all:.0f}",
                RecallLo=f"{100 * lo:.0f}", RecallHi=f"{100 * hi:.0f}", RecallEligN=len(elig), RecallEligKept=k_el,
                RecallEligPct=f"{100 * k_el / len(elig):.0f}", RecallEligLo=f"{100 * lo2:.0f}",
                RecallEligHi=f"{100 * hi2:.0f}", RecallLostFlagged=len(lost & flagged), RecallLost=len(lost))


def main() -> None:
    human = pd.read_excel(WORK_DIR / "validation" / "validation_coding_baseline_v2.xlsx").set_index("record_id")
    human = human[human["rci1_platform_model"].map(b).notna()]
    adj = pd.concat([pd.read_excel(WORK_DIR / f"adjudication_{t}.xlsx") for t in ("rci", "cap")])
    first = {(r.pdf_name, r.item): b(r.final_code) for r in adj.itertuples()}
    rows = []
    for tool in ("rci", "cap"):
        a = pd.read_excel(WORK_DIR / f"{tool}_A_all_records.xlsx").set_index("Pdf name")
        bb = pd.read_excel(WORK_DIR / f"{tool}_B_all_records.xlsx").set_index("Pdf name")
        items = [c for c in a.columns if c.startswith("rci" if tool == "rci" else "cap_") and "__" not in c
                 and c not in ("rci_total", "n_capabilities")]
        for it in items:
            row = dict(item=it, n=0, agreed=0, agreed_wrong=0, agreed_fp=0, agreed_fn=0,
                       adjudicated=0, adjudicated_wrong=0, adjudicated_wrong_to_yes=0,
                       pipeline_yes=0, human_yes=0)
            for sid in human.index:
                if sid not in a.index:      # drawn, then excluded at full text (r2-0581)
                    continue
                h, x, y = b(human.at[sid, it]), b(a.at[sid, it]), b(bb.at[sid, it])
                if None in (h, x, y):
                    continue
                code = x if x == y else first.get((sid, it))
                if code is None:
                    continue
                row["n"] += 1; row["human_yes"] += h; row["pipeline_yes"] += code
                if x == y:
                    row["agreed"] += 1
                    if code != h:
                        row["agreed_wrong"] += 1; row["agreed_fp"] += code; row["agreed_fn"] += (not code)
                else:
                    row["adjudicated"] += 1
                    if code != h:
                        row["adjudicated_wrong"] += 1; row["adjudicated_wrong_to_yes"] += code
            rows.append(row)
    t = pd.DataFrame(rows)
    t.to_csv(WORK_DIR / "pipeline_vs_human.csv", index=False)
    s = t.sum(numeric_only=True)
    codes = int(s["n"])
    nums = {
        "PipeCodes": codes, "PipeWrong": int(s["agreed_wrong"] + s["adjudicated_wrong"]),
        "PipeWrongPct": f"{100 * (s['agreed_wrong'] + s['adjudicated_wrong']) / codes:.0f}",
        "PipeAgreed": int(s["agreed"]), "PipeAgreedWrong": int(s["agreed_wrong"]),
        "PipeAgreedWrongPct": f"{100 * s['agreed_wrong'] / s['agreed']:.0f}", "PipeAgreedFP": int(s["agreed_fp"]),
        "PipeAdj": int(s["adjudicated"]), "PipeAdjMatch": int(s["adjudicated"] - s["adjudicated_wrong"]),
        "PipeAdjWrong": int(s["adjudicated_wrong"]), "PipeAdjWrongToYes": int(s["adjudicated_wrong_to_yes"]),
        "PipeYes": int(s["pipeline_yes"]), "HumanYes": int(s["human_yes"]),
        "PipeYesInflationPct": f"{100 * (s['pipeline_yes'] / s['human_yes'] - 1):.0f}",
    }
    readj = pd.read_excel(WORK_DIR / "readjudication_yes.xlsx")
    rc = readj["final_code"].map(b)
    nums.update(ReadjN=int(rc.notna().sum()), ReadjToNo=int((rc == False).sum()),  # noqa: E712
                ReadjToNoPct=f"{100 * (rc == False).sum() / max(1, rc.notna().sum()):.0f}")  # noqa: E712
    inter = pd.concat([pd.read_csv(WORK_DIR / f"agreement_{t}_pass_A_vs_B_all.csv") for t in ("rci", "cap")])
    kap = pd.to_numeric(inter["kappa"], errors="coerce")
    nums.update(InterAgreeMin=f"{100 * inter['agreement'].min():.0f}", InterAgreeMax=f"{100 * inter['agreement'].max():.0f}",
                InterKappaMin=f"{kap.min():.2f}", InterKappaMax=f"{kap.max():.2f}",
                InterKappaLowItems=", ".join(inter.loc[kap < 0.6, "item"].str.replace("_", " ")))
    acc = pd.read_csv(WORK_DIR / "validation_accuracy.csv")
    acc = acc[(acc["pass"].astype(str) == "A") & (acc["type"] == "binary") & ~acc["item"].str.endswith("__blind")]
    nums.update(HumanAgreeMin=f"{100 * acc['agreement'].min():.0f}", HumanAgreeMax=f"{100 * acc['agreement'].max():.0f}",
                HumanAgreeLowItem=acc.loc[acc["agreement"].idxmin(), "item"].replace("cap_", "").replace("_", " "),
                HumanAgreeLowValue=f"{100 * acc['agreement'].min():.0f}")
    nums.update(class_validation(human))
    allacc = pd.read_csv(WORK_DIR / "validation_accuracy.csv")
    for item, macro in (("sensor_specificity", "SpecWkSens"), ("compute_specificity", "SpecWkComp")):
        r = allacc[(allacc["pass"].astype(str) == "A") & (allacc["item"] == item)].iloc[0]
        nums[macro] = f"{r['kappa']:.2f}"
    nums.update(screening_recall())
    pd.Series(nums).to_csv(WORK_DIR / "pipeline_numbers.csv", header=["value"])
    print(t.to_string(index=False)); print(nums)


if __name__ == "__main__":
    main()
