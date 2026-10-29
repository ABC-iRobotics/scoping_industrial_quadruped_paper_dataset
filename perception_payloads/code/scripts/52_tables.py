"""
Stage 52 - the Results tables as LaTeX fragments, so no table cell is typed
by hand.

    ../tables/tab_codebook.tex    Table 2: controlled vocabulary, rule, studies
    ../tables/tab_crosstab.tex    Table 3: modality x capability
    ../tables/tab_agreement.tex   Table 6: per item, final prevalence, inter-pass
                                  agreement, same-model retest, pass A against
                                  the human reference, and pipeline errors by route

Inputs: data/charting_v2.xlsx (through 50_results.prepare), the agreement and
accuracy CSVs written by stages 11, 37 and 51. main.tex \\input's the files.
"""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import pandas as pd

from _common import WORK_DIR

SCRIPTS = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("res", SCRIPTS / "50_results.py")
res = importlib.util.module_from_spec(_s)
_s.loader.exec_module(res)

OUT = WORK_DIR.parent.parent / "tables"

RULES = {
    "lidar": "names a LiDAR, laser scanner or a LiDAR product",
    "rgb_camera": "a single passive 2D imager, colour or monochrome (generic camera, PTZ, 360$^\\circ$, optical-flow sensor)",
    "depth_rgbd": "an RGB-D, time-of-flight or active near-infrared depth camera, as one device",
    "thermal_ir": "thermal or infrared imaging",
    "stereo": "a stereo camera pair, including tracking cameras with two imagers",
    "event_camera": "an event (neuromorphic) camera",
    "embedded_gpu": "an NVIDIA Jetson-class module",
    "x86_mini_pc": "a small-form-factor x86 computer (NUC, UP board, Pico-ITX)",
    "laptop_workstation": "a laptop- or desktop-class CPU carried on the robot",
    "sbc_microcontroller": "a single-board computer or microcontroller (Raspberry Pi, ARM SoC board, STM32)",
    "vendor_integrated": "the robot vendor's own payload computer (Spot CORE)",
}


def pct(k: int, n: int) -> str:
    return f"{k} ({100 * k / n:.0f})" if n else "--"


def codebook(d: pd.DataFrame) -> None:
    r = d[d.readable]
    n = len(r)
    sens = Counter(m for v in r.modalities for m in v)
    comp = Counter(c for v in r.computes for c in v)
    lines = ["\\begin{tabularx}{\\fulllength}{llXr}", "\\toprule",
             "\\textbf{Field} & \\textbf{Class} & \\textbf{Assigned when the reported string names\\ldots} & "
             "\\textbf{Studies, $n$ (\\%)}\\\\", "\\midrule"]
    for field, counts, names in (("Sensor", sens, res.MODALITY), ("Compute", comp, res.COMPUTE)):
        for i, (c, k) in enumerate(counts.most_common()):
            lines.append(f"{field if i == 0 else ''} & {names[c]} & {RULES[c]} & {pct(k, n)}\\\\")
        none = int((r.modalities if field == 'Sensor' else r.computes).map(len).eq(0).sum())
        why = "only vague or non-optical mentions, or nothing" if field == "Sensor" else "only vague mentions such as an onboard computer, or nothing"
        lines.append(f" & Not reported & no class above ({why}) & {pct(none, n)}\\\\")
        lines.append("\\midrule" if field == "Sensor" else "\\bottomrule")
    lines.append("\\end{tabularx}")
    (OUT / "tab_codebook.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def crosstab(d: pd.DataFrame) -> None:
    r = d[d.readable]
    mods = [m for m, _ in Counter(m for v in r.modalities for m in v).most_common()]
    caps = list(res.CAPS)
    lines = ["\\begin{tabularx}{\\fulllength}{l" + "C" * len(caps) + "}", "\\toprule",
             "\\textbf{Modality ($n$)} & " + " & ".join(f"\\textbf{{{res.CAPS[c]}}}" for c in caps) + "\\\\",
             "\\midrule"]
    for m in mods + ["__none"]:
        sub = r[r.modalities.map(len) == 0] if m == "__none" else r[r.modalities.map(lambda v: m in v)]
        lab = "None reported" if m == "__none" else res.MODALITY[m]
        cells = [pct(int(sub[c].map(res.yes).sum()), len(sub)) for c in caps]
        lines.append(f"{lab} ({len(sub)}) & " + " & ".join(cells) + "\\\\")
    lines += ["\\midrule", f"All readable ({len(r)}) & " +
              " & ".join(pct(int(r[c].map(res.yes).sum()), len(r)) for c in caps) + "\\\\",
              "\\bottomrule", "\\end{tabularx}"]
    (OUT / "tab_crosstab.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def agreement(d: pd.DataFrame) -> None:
    r = d[d.readable]
    inter = pd.concat([pd.read_csv(WORK_DIR / f"agreement_{t}_pass_A_vs_B_all.csv") for t in ("rci", "cap")]).set_index("item")
    retest = pd.read_csv(WORK_DIR / "agreement_amendment_A1_effect.csv").set_index("item")
    acc = pd.read_csv(WORK_DIR / "validation_accuracy.csv")
    acc = acc[acc["pass"].astype(str).str.upper().str.endswith("A")].set_index("item") if "pass" in acc else acc.set_index("item")
    pipe = pd.read_csv(WORK_DIR / "pipeline_vs_human.csv").set_index("item")
    items = list(res.RCI) + list(res.CAPS) + ["cap_real_world_validation"]
    label = {**res.RCI, **res.CAPS, "cap_real_world_validation": "Real-world validation"}

    def ag(row) -> str:
        k = row["kappa"]
        ks = "--" if pd.isna(k) or str(k) == "" else f"{float(k):.2f}"
        return f"{100 * row['agreement']:.0f} ({ks})"

    lines = ["\\begin{tabularx}{\\fulllength}{lCCCCC}", "\\toprule",
             "\\textbf{Item} & \\textbf{Reported, \\%} & \\textbf{Pass A vs.\\ B, \\% ($\\kappa$)} & "
             "\\textbf{Pass A retest, \\%} & \\textbf{Pass A vs.\\ human, \\% ($\\kappa$)} & "
             "\\textbf{Pipeline errors: agreed / adjudicated}\\\\", "\\midrule"]
    for it in items:
        rep = f"{100 * r[it].map(res.yes).mean():.0f}"
        rt = f"{100 * retest.loc[it, 'agreement']:.0f}" if it in retest.index and it != "rci9_artifact" else "--"
        hu = ag(acc.loc[it]) if it in acc.index else "--"
        pp = pipe.loc[it]
        er = f"{int(pp['agreed_wrong'])}/{int(pp['agreed'])} \\,;\\, {int(pp['adjudicated_wrong'])}/{int(pp['adjudicated'])}"
        lines.append(f"{label[it]} & {rep} & {ag(inter.loc[it])} & {rt} & {hu} & {er}\\\\")
        if it == "rci9_artifact":
            lines.append("\\midrule")
    lines += ["\\bottomrule", "\\end{tabularx}"]
    (OUT / "tab_agreement.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def sensitivity() -> None:
    s = pd.read_csv(WORK_DIR / "results_sensitivity.csv", index_col=0)
    label = {**{f"pct_{k}": f"Modality: {v}" for k, v in res.MODALITY.items()},
             **{f"pct_{k}": f"Capability: {v}" for k, v in res.CAPS.items()},
             "pct_cap_real_world_validation": "Capability: real-world validation",
             **{f"pct_{k}": f"RCI item {v}" for k, v in res.RCI.items()},
             "pct_sensor_model": "Sensor named at model level",
             "pct_compute_unspecified": "Onboard computer not reported",
             "rci_median": "RCI median", "rci_mean": "RCI mean"}
    n_all, n_wo = int(s.loc["n_readable", "all"]), int(s.loc["n_readable", "without_flagged"])
    lines = [r"\begin{tabularx}{\textwidth}{XCCC}", r"\toprule",
             rf"\textbf{{Quantity}} & \textbf{{All ($n={n_all}$)}} & "
             rf"\textbf{{Without flagged ($n={n_wo}$)}} & \textbf{{Difference}}\\", r"\midrule"]
    for k in s.index:
        if k == "n_readable":
            continue
        unit = "" if k.startswith("rci_m") else r"\,\%"
        lines.append(f"{label.get(k, k)} & {s.at[k, 'all']:.1f}{unit} & {s.at[k, 'without_flagged']:.1f}{unit} & "
                     f"{s.at[k, 'diff_pp']:+.1f}" + r"\\")
    lines += [r"\bottomrule", r"\end{tabularx}"]
    (OUT / "tab_sensitivity.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def validation_full() -> None:
    acc = pd.read_csv(WORK_DIR / "validation_accuracy.csv")
    acc = acc[acc["type"] == "binary"]
    label = {**res.RCI, **res.CAPS, "cap_real_world_validation": "Real-world validation"}
    lines = [r"\begin{tabularx}{\fulllength}{lcCCCCC}", r"\toprule",
             r"\textbf{Item} & \textbf{Pass} & \textbf{Agreement, \% (95\% CI)} & \textbf{Prev.\ human, \%} & "
             r"\textbf{Prev.\ model, \%} & \textbf{$\kappa$ (95\% CI)} & \textbf{Model-only / human-only positives}\\",
             r"\midrule"]
    items = list(res.RCI) + list(res.CAPS) + ["cap_real_world_validation",
                                              "rci4_middleware_version__blind", "rci2_sensors_model__blind"]
    for it in items:
        for ps in ("A", "B"):
            r = acc[(acc["item"] == it) & (acc["pass"].astype(str) == ps)]
            if r.empty:
                continue
            r = r.iloc[0]
            k = "undefined" if pd.isna(r.kappa) else f"{r.kappa:.2f} ({r.kappa_lo:.2f}, {r.kappa_hi:.2f})"
            name = label.get(it.replace("__blind", ""), it) + (" (blind codes)" if it.endswith("__blind") else "")
            lines.append(f"{name if ps == 'A' else ''} & {ps} & {100 * r.agreement:.0f} "
                         f"({100 * r.agree_lo:.0f}--{100 * r.agree_hi:.0f}) & {100 * r.prev_human:.0f} & "
                         f"{100 * r.prev_llm:.0f} & {k} & {int(r.llm_only_yes)} / {int(r.human_only_yes)}" + r"\\")
    lines += [r"\bottomrule", r"\end{tabularx}"]
    (OUT / "tab_validation_full.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def class_validation() -> None:
    t = pd.read_csv(WORK_DIR / "class_validation.csv")
    names = {**res.MODALITY, **res.COMPUTE}
    lines = [r"\begin{tabularx}{\textwidth}{llCCCC}", r"\toprule",
             r"\textbf{Field} & \textbf{Class} & \textbf{Agr., \%} & \textbf{$\kappa$} & "
             r"\textbf{Human positives} & \textbf{Pipeline positives}\\", r"\midrule"]
    for r in t.itertuples():
        k = "--" if pd.isna(r.kappa) else f"{r.kappa:.2f}"
        lines.append(f"{'Sensor' if r.field == 'sensors' else 'Compute'} & {names[r.cls]} & "
                     f"{100 * r.agreement:.0f} & {k} & {r.human_yes} & {r.pipeline_yes}" + r"\\")
    lines += [r"\bottomrule", r"\end{tabularx}"]
    (OUT / "tab_class_validation.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    d = res.prepare()
    codebook(d); crosstab(d); agreement(d); sensitivity(); validation_full(); class_validation()
    print("written", ", ".join(p.name for p in sorted(OUT.glob("tab_*.tex"))))


if __name__ == "__main__":
    main()
