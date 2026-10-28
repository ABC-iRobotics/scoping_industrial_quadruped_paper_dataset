"""
Stage 50 - the results: frequencies, cross-tabulations, Figs. 2-6, and the
numbers the Results section prints.

INPUT
    ../data/charting_v2.xlsx   the frozen charting table (42_build_final.py)
    Nothing else: every count below is re-derivable from that one file.

DENOMINATORS
    Variables extracted from the full text are counted over the studies whose
    text could be read (status == ok); paper043 is a scanned PDF and is
    reported as not assessable, not as "reports nothing". The corpus size and
    year/sector counts use all included studies.

DERIVED VARIABLES
    modality      sensor_classes minus not_optical / not_onboard / unspecified.
                  A study with none left "reports no optical modality".
    compute       compute_classes minus not_onboard / unspecified.
    sector        sector_classes minus not_industrial. Sectors held by fewer
                  than OTHER_CUTOFF studies fold into "Other"; the cut-off is
                  set once here and reused by every sector-split figure.
    specificity   derived from the final codes so that Fig. 5 and the RCI agree:
                  model = RCI item 2 (or 3) is yes; modality = a class is
                  reported but not at model level; unspecified = no class.

SENSITIVITY
    Every headline number is computed twice: for all readable studies and
    without the 16 baseline studies that fail the criteria as applied in
    round 2 (fails_current_criteria, amendment A12). Both go to
    work/results_sensitivity.csv; the main text prints the first and states
    the largest difference.

OUTPUTS
    ../figures/fig2_modalities.pdf ... fig6_rci.pdf (and .png previews)
    work/results_numbers.csv     macro,value - read by 40_emit_numbers.py
    work/results_tables.md       Tables 2 and 3 in readable form
    work/results_sensitivity.csv
"""
from __future__ import annotations

import itertools
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from _common import WORK_DIR

ROOT = WORK_DIR.parent.parent
DATA = ROOT / "data" / "charting_v2.xlsx"
FIG = ROOT / "figures"
OTHER_CUTOFF = 7

MODALITY = {"lidar": "LiDAR", "rgb_camera": "Monocular camera", "depth_rgbd": "RGB-D / depth",
            "thermal_ir": "Thermal / IR", "stereo": "Stereo", "event_camera": "Event camera"}
COMPUTE = {"embedded_gpu": "Embedded GPU module", "x86_mini_pc": "x86 mini PC",
           "laptop_workstation": "Laptop/desktop-class CPU", "sbc_microcontroller": "SBC / microcontroller",
           "vendor_integrated": "Vendor-integrated computer"}
SECTOR = {"general_industrial": "General industrial", "construction": "Construction", "mining": "Mining",
          "energy_power": "Energy and power", "oil_gas_chemical": "Oil, gas and chemical",
          "nuclear": "Nuclear", "manufacturing": "Manufacturing", "logistics_warehouse": "Logistics",
          "other": "Other"}
CAPS = {"cap_slam_mapping": "SLAM / mapping", "cap_autonomous_navigation": "Autonomous navigation",
        "cap_obstacle_avoidance": "Obstacle avoidance", "cap_object_detection": "Object detection",
        "cap_instrument_reading": "Instrument reading", "cap_target_tracking": "Target tracking"}
RCI = {"rci1_platform_model": "1 Platform model", "rci2_sensors_model": "2 Sensor model",
       "rci3_compute_model": "3 Compute model", "rci4_middleware_version": "4 Middleware + version",
       "rci5_algorithms_cited": "5 Algorithms cited", "rci6_parameters": "6 Parameters",
       "rci7_eval_environment": "7 Test environment", "rci8_success_metric": "8 Success metric",
       "rci9_artifact": "9 Own code/data"}

# Chart ink and the validated ramps (dataviz reference palette, light mode;
# figures print on white paper).
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE = {100: "#cde2fb", 250: "#86b6ef", 450: "#2a78d6", 650: "#104281"}
SEQ = matplotlib.colors.LinearSegmentedColormap.from_list(
    "seq", ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
ORDINAL = [AXIS, BLUE[450], BLUE[650]]            # not reported (neutral) < class only < model
ACCENT = "#eb6834"                                # categorical slot 2, one use only


# Letter-only keys for generated macro names (LaTeX allows no digits there).
MKEY = {"lidar": "Lidar", "rgb_camera": "Mono", "depth_rgbd": "Rgbd", "thermal_ir": "Thermal",
        "stereo": "Stereo", "event_camera": "Event", "__none": "None"}
CKEY = {"cap_slam_mapping": "Slam", "cap_autonomous_navigation": "Nav", "cap_obstacle_avoidance": "Obst",
        "cap_object_detection": "Det", "cap_instrument_reading": "Instr", "cap_target_tracking": "Track"}
SKEY = {"general_industrial": "Gen", "construction": "Constr", "mining": "Mining", "energy_power": "Energy",
        "oil_gas_chemical": "Oil", "nuclear": "Nuclear", "manufacturing": "Manuf", "other": "Other"}


def yes(v) -> bool:
    return str(v).strip().lower() in ("1", "1.0", "true", "yes")


def split(v) -> list[str]:
    return [p.strip() for p in str(v).split(";") if p.strip() and str(v) != "nan"]


def setup() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
        "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "text.color": INK,
        "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
    })


def save(fig, name: str) -> None:
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=220)
    plt.close(fig)
    print(f"  {name}")


def prepare() -> pd.DataFrame:
    d = pd.read_excel(DATA).set_index("record_id")
    d["readable"] = d["status"].astype(str).eq("ok")
    d["modalities"] = d["sensor_classes"].map(lambda v: [c for c in split(v) if c in MODALITY])
    d["computes"] = d["compute_classes"].map(lambda v: [c for c in split(v) if c in COMPUTE])
    sec_n = Counter(c for v in d["sector_classes"] for c in split(v) if c in SECTOR)
    keep = {s for s, n in sec_n.items() if n >= OTHER_CUTOFF and s != "other"}
    # "General industrial" means the study names no specific sector. Where a
    # study also names one (an "industrial environment" that is a distillation
    # column), the general label is dropped rather than counted as a second sector.
    def sectors_of(v):
        named = {c if c in keep else "other" for c in split(v) if c in SECTOR}
        return sorted(named - {"general_industrial"} if len(named) > 1 else named)
    d["sectors"] = d["sector_classes"].map(sectors_of)
    d["sensor_spec"] = [("model" if yes(r.rci2_sensors_model) else "modality" if r.modalities else "unspecified")
                        for r in d.itertuples()]
    d["compute_spec"] = [("model" if yes(r.rci3_compute_model) else "modality" if r.computes else "unspecified")
                         for r in d.itertuples()]
    return d


def sector_order(d: pd.DataFrame) -> list[str]:
    n = Counter(s for v in d["sectors"] for s in v)
    return [s for s, _ in n.most_common() if s != "other"] + (["other"] if "other" in n else [])


def fig2(d: pd.DataFrame, nums: dict) -> None:
    r = d[d.readable]
    n = len(r)
    counts = Counter(m for v in r.modalities for m in v)
    order = [m for m, _ in counts.most_common()]
    none = int((r.modalities.map(len) == 0).sum())
    secs = sector_order(r)
    fig, (a, b) = plt.subplots(1, 2, figsize=(6.6, 2.7), gridspec_kw={"width_ratios": [1, 1.45], "wspace": 0.55})
    labels = [MODALITY[m] for m in order] + ["None reported"]
    vals = [counts[m] for m in order] + [none]
    y = np.arange(len(labels))[::-1]
    a.barh(y, vals, height=0.62, color=[BLUE[450]] * len(order) + [AXIS], edgecolor="white", linewidth=0.8)
    for yi, v in zip(y, vals):
        a.text(v + 1, yi, f"{v} ({100 * v / n:.0f}%)", va="center", fontsize=7, color=INK2)
    a.set_yticks(y, labels)
    a.set_xlim(0, max(vals) * 1.6)
    a.set_xlabel(f"Studies (n = {n}, multi-label)")
    a.xaxis.grid(True, color=GRID, linewidth=0.5); a.set_axisbelow(True)
    a.set_title("(a) Optical modality reported", loc="left", color=INK)
    mat = np.array([[100 * sum(1 for i in r.index if s in r.at[i, "sectors"] and m in r.at[i, "modalities"])
                     / max(1, sum(1 for i in r.index if s in r.at[i, "sectors"])) for m in order] for s in secs])
    im = b.imshow(mat, cmap=SEQ, vmin=0, vmax=100, aspect="auto")
    for (i, j), v in np.ndenumerate(mat):
        b.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.5, color="white" if v >= 55 else INK)
    sec_n = [sum(1 for v in r.sectors if s in v) for s in secs]
    b.set_yticks(range(len(secs)), [f"{SECTOR[s]} ({k})" for s, k in zip(secs, sec_n)])
    b.set_xticks(range(len(order)), [MODALITY[m] for m in order], rotation=35, ha="right")
    b.tick_params(length=0)
    for sp in b.spines.values(): sp.set_visible(False)
    b.set_title("(b) Share of studies in each sector (%)", loc="left", color=INK)
    cb = fig.colorbar(im, ax=b, fraction=0.04, pad=0.02); cb.outline.set_visible(False); cb.ax.tick_params(labelsize=6.5)
    save(fig, "fig2_modalities")
    for i, s in enumerate(secs):
        for j, m in enumerate(order):
            nums[f"S{SKEY[s]}{MKEY[m]}"] = f"{mat[i, j]:.0f}"
    for m in order:
        nums[f"Mod{MODALITY[m].split()[0].replace('-', '').replace('/', '')}"] = counts[m]
    nums.update(NreadableStudies=n, ModNone=none, OtherCutoff=OTHER_CUTOFF)


def fig3(d: pd.DataFrame, nums: dict) -> None:
    r = d[d.readable]
    combos = Counter(tuple(sorted(v, key=list(MODALITY).index)) for v in r.modalities)
    top = [c for c, _ in combos.most_common() if c][:12]
    mods = [m for m in MODALITY if any(m in c for c in top)]
    fig, (a, b) = plt.subplots(2, 1, figsize=(5.4, 3.3), sharex=True,
                               gridspec_kw={"height_ratios": [1.4, 1], "hspace": 0.06})
    x = np.arange(len(top))
    vals = [combos[c] for c in top]
    a.bar(x, vals, width=0.6, color=BLUE[450], edgecolor="white", linewidth=0.8)
    for xi, v in zip(x, vals):
        a.text(xi, v + 0.4, str(v), ha="center", fontsize=6.8, color=INK2)
    a.set_ylabel("Studies"); a.yaxis.grid(True, color=GRID, linewidth=0.5); a.set_axisbelow(True)
    for j, m in enumerate(mods):
        yy = len(mods) - 1 - j
        b.scatter(x, [yy] * len(x), s=22, color=GRID, zorder=1)
        on = [i for i, c in enumerate(top) if m in c]
        b.scatter(on, [yy] * len(on), s=26, color=BLUE[650], zorder=2)
    for i, c in enumerate(top):
        ys = [len(mods) - 1 - mods.index(m) for m in c]
        if len(ys) > 1:
            b.plot([i, i], [min(ys), max(ys)], color=BLUE[650], linewidth=1.6, zorder=1.5)
    b.set_yticks(range(len(mods))[::-1], [MODALITY[m] for m in mods])
    b.set_xticks([]); b.tick_params(length=0)
    for sp in b.spines.values(): sp.set_visible(False)
    b.set_ylim(-0.6, len(mods) - 0.4)
    save(fig, "fig3_cooccurrence")
    nums.update(TopComboName=" and ".join(MODALITY[m] for m in top[0]).replace("LiDAR", "a LiDAR", 1)
                if len(top[0]) else "none", TopComboN=combos[top[0]])
    k = r.modalities.map(len)
    lidar = r.modalities.map(lambda v: "lidar" in v)
    cam = r.modalities.map(lambda v: bool(set(v) - {"lidar"}))
    nums.update(ModAny=int((k > 0).sum()), ModMulti=int((k >= 2).sum()),
                ModMultiPctOfAny=f"{100 * (k >= 2).sum() / max(1, (k > 0).sum()):.0f}",
                LidarWithCamera=int((lidar & cam).sum()), LidarAlone=int((lidar & ~cam).sum()))
    nums.update(ModOne=int((k == 1).sum()), ModTwo=int((k == 2).sum()), ModThreePlus=int((k >= 3).sum()),
                ModCombos=len([c for c in combos if c]))


def fig4(d: pd.DataFrame, nums: dict, tables: list) -> None:
    r = d[d.readable]
    mods = [m for m, _ in Counter(m for v in r.modalities for m in v).most_common()]
    rows = mods + ["__none"]
    caps = list(CAPS)
    cnt = np.zeros((len(rows), len(caps)), int); n_row = []
    for i, m in enumerate(rows):
        sub = r[r.modalities.map(len) == 0] if m == "__none" else r[r.modalities.map(lambda v: m in v)]
        n_row.append(len(sub))
        for j, c in enumerate(caps):
            cnt[i, j] = int(sub[c].map(yes).sum())
    pct = 100 * cnt / np.maximum(1, np.array(n_row))[:, None]
    allrow = [100 * r[c].map(yes).mean() for c in caps]
    ylab = [f"{MODALITY[m]} ({k})" for m, k in zip(mods, n_row)] + [f"None reported ({n_row[-1]})"]
    # A modality held by one or two studies would print 0 or 100 %; it stays
    # in Table 3 but not in the heatmap.
    show = [i for i, k in enumerate(n_row) if k >= 3]
    nums["FigFourDropped"] = ", ".join(ylab[i] for i in range(len(rows)) if i not in show) or "none"
    fig, ax = plt.subplots(figsize=(5.6, 2.8))
    im = ax.imshow(pct[show], cmap=SEQ, vmin=0, vmax=100, aspect="auto")
    for (i, j), v in np.ndenumerate(pct[show]):
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.8, color="white" if v >= 55 else INK)
    ax.set_yticks(range(len(show)), [ylab[i] for i in show])
    ax.set_xticks(range(len(caps)), [CAPS[c].replace(" ", "\n", 1) + f"\n(all {v:.0f}%)" for c, v in zip(caps, allrow)],
                  fontsize=6.6)
    ax.tick_params(length=0)
    for sp in ax.spines.values(): sp.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.outline.set_visible(False); cb.ax.tick_params(labelsize=6.5)
    save(fig, "fig4_modality_capability")
    for i, m in enumerate(rows):
        for j, c in enumerate(caps):
            nums[f"X{MKEY[m]}{CKEY[c]}"] = f"{pct[i, j]:.0f}"
    lines = ["## Table 3 - modality x capability (studies; row n in brackets)", "",
             "| Modality | " + " | ".join(CAPS[c] for c in caps) + " |", "|---|" + "---:|" * len(caps)]
    for lab, row, k in zip(ylab, cnt, n_row):
        lines.append(f"| {lab} | " + " | ".join(f"{v} ({100 * v / max(1, k):.0f}%)" for v in row) + " |")
    tables.extend(lines + [""])
    for c in caps:
        nums[f"Cap{CAPS[c].split()[0].replace('/', '')}"] = int(r[c].map(yes).sum())
    nums["CapRealWorld"] = int(r["cap_real_world_validation"].map(yes).sum())
    geo = r[["cap_slam_mapping", "cap_autonomous_navigation", "cap_obstacle_avoidance"]].apply(
        lambda s: s.map(yes)).any(axis=1)
    sem = r[["cap_object_detection", "cap_instrument_reading", "cap_target_tracking"]].apply(
        lambda s: s.map(yes)).any(axis=1)
    nums.update(CapGeometricAny=int(geo.sum()), CapSemanticAny=int(sem.sum()),
                CapGeometricOnly=int((geo & ~sem).sum()), CapSemanticOnly=int((sem & ~geo).sum()),
                CapNeither=int((~geo & ~sem).sum()))


def fig5(d: pd.DataFrame, nums: dict) -> None:
    r = d[d.readable]
    secs = sector_order(r)
    groups = [("All studies", r)] + [(SECTOR[s], r[r.sectors.map(lambda v: s in v)]) for s in secs]
    levels = ["unspecified", "modality", "model"]
    names = {"unspecified": "Not reported", "modality": "Class only", "model": "Model named"}
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9), sharey=True, gridspec_kw={"wspace": 0.08})
    for ax, field, title in ((axes[0], "sensor_spec", "(a) Optical sensors"),
                             (axes[1], "compute_spec", "(b) Onboard compute")):
        y = np.arange(len(groups))[::-1]
        left = np.zeros(len(groups))
        for lev, col in zip(levels, ORDINAL):
            share = np.array([100 * (g[field] == lev).mean() for _, g in groups])
            ax.barh(y, share, left=left, height=0.66, color=col, edgecolor="white", linewidth=1.0,
                    label=names[lev])
            for yi, l0, s in zip(y, left, share):
                if s >= 9:
                    ax.text(l0 + s / 2, yi, f"{s:.0f}", ha="center", va="center", fontsize=6.5,
                            color="white" if lev != "unspecified" else INK)
            left += share
        ax.set_yticks(y, [f"{lab} ({len(g)})" for lab, g in groups])
        ax.set_xlim(0, 100); ax.set_xlabel("Share of studies (%)")
        ax.set_title(title, loc="left", color=INK); ax.tick_params(axis="y", length=0)
    axes[0].legend(ncol=3, frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.07), fontsize=7,
                   handlelength=1.2, columnspacing=1.2)
    save(fig, "fig5_specificity")
    for field, pre in (("sensor_spec", "SensSpec"), ("compute_spec", "CompSpec")):
        vc = r[field].value_counts()
        for lev in levels:
            nums[f"{pre}{lev.capitalize()}"] = int(vc.get(lev, 0))


def fig6(d: pd.DataFrame, nums: dict) -> None:
    r = d[d.readable & d.rci_total.notna()]
    n = len(r)
    fig = plt.figure(figsize=(6.6, 4.9))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.5], wspace=0.55, hspace=0.55)
    a, b, c = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
    tot = r.rci_total.astype(int)
    k = np.arange(0, 10)
    a.bar(k, [int((tot == v).sum()) for v in k], width=0.7, color=BLUE[450], edgecolor="white", linewidth=0.8)
    a.axvline(tot.median(), color=ACCENT, linewidth=1.2, linestyle=(0, (3, 2)))
    a.text(tot.median() - 0.35, a.get_ylim()[1] * 0.97, f"median {tot.median():.0f}", color=INK2, fontsize=6.8,
           ha="right", va="top")
    a.set_xticks(k); a.set_xlabel("RCI (items reported of 9)"); a.set_ylabel("Studies")
    a.yaxis.grid(True, color=GRID, linewidth=0.5); a.set_axisbelow(True)
    a.set_title(f"(a) RCI (n = {n})", loc="left", color=INK)
    items = list(RCI)
    share = [100 * r[i].map(yes).mean() for i in items]
    y = np.arange(len(items))[::-1]
    b.barh(y, share, height=0.62, color=BLUE[450], edgecolor="white", linewidth=0.8)
    strict = 100 * r["rci3_strict"].map(yes).mean()
    yi3 = y[items.index("rci3_compute_model")]
    b.plot([strict], [yi3], marker="|", markersize=11, markeredgewidth=1.6, color=ACCENT)
    for yi, v, it in zip(y, share, items):
        lab = f"{v:.0f}" + (f" (strict: {strict:.0f})" if it == "rci3_compute_model" else "")
        b.text(v + 1.5, yi, lab, va="center", fontsize=6.6, color=INK2)
    b.set_yticks(y, [RCI[i] for i in items], fontsize=6.8)
    b.set_xlim(0, 110); b.set_xlabel("Studies reporting the item (%)")
    b.xaxis.grid(True, color=GRID, linewidth=0.5); b.set_axisbelow(True); b.tick_params(axis="y", length=0)
    b.set_title("(b) Per item", loc="left", color=INK)
    secs = sector_order(r)
    rng = np.random.default_rng(20261028)
    for j, s in enumerate(secs[::-1]):
        vals = r.loc[r.sectors.map(lambda v: s in v), "rci_total"].astype(float).to_numpy()
        c.scatter(vals + rng.uniform(-0.18, 0.18, len(vals)), np.full(len(vals), j) + rng.uniform(-0.2, 0.2, len(vals)),
                  s=9, color=BLUE[450], alpha=0.75, linewidths=0)
        c.plot([np.median(vals)] * 2, [j - 0.34, j + 0.34], color=ACCENT, linewidth=1.6)
    c.set_yticks(range(len(secs)), [f"{SECTOR[s]} ({sum(1 for v in r.sectors if s in v)})" for s in secs[::-1]],
                 fontsize=6.8)
    c.set_xticks(range(0, 10)); c.set_xlim(-0.5, 9.5); c.set_xlabel("RCI (items reported of 9)")
    c.xaxis.grid(True, color=GRID, linewidth=0.5); c.set_axisbelow(True); c.tick_params(axis="y", length=0)
    c.set_title("(c) By sector (line = median)", loc="left", color=INK)
    save(fig, "fig6_rci")
    med = {s: r.loc[r.sectors.map(lambda v: s in v), "rci_total"].median() for s in secs}
    low = min(med, key=med.get)
    nums.update(RCISectorLowName=SECTOR[low].lower(), RCISectorLowMedian=f"{med[low]:g}",
                RCISectorHighMedian=f"{max(med.values()):g}")
    q = tot.quantile([0.25, 0.75])
    nums.update(NrciStudies=n, RCImedian=f"{tot.median():.0f}", RCIiqrLo=f"{q[0.25]:.0f}", RCIiqrHi=f"{q[0.75]:.0f}",
                RCImin=int(tot.min()), RCImax=int(tot.max()), RCIfull=int((tot == 9).sum()),
                RCIatMostThree=int((tot <= 3).sum()), RCIthreeStrict=int(r["rci3_strict"].map(yes).sum()))
    words = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    for i in items:
        nums[f"RCIitem{words[int(i[3]) - 1]}"] = int(r[i].map(yes).sum())


def headline(d: pd.DataFrame) -> dict:
    """The numbers a reader would quote, for the sensitivity comparison."""
    r = d[d.readable]
    n = len(r)
    out = {"n_readable": n}
    for m in MODALITY:
        out[f"pct_{m}"] = 100 * r.modalities.map(lambda v: m in v).mean()
    for c in list(CAPS) + ["cap_real_world_validation"]:
        out[f"pct_{c}"] = 100 * r[c].map(yes).mean()
    for i in RCI:
        out[f"pct_{i}"] = 100 * r[i].map(yes).mean()
    t = r.rci_total.dropna()
    out["rci_median"] = t.median(); out["rci_mean"] = t.mean()
    out["pct_sensor_model"] = 100 * (r.sensor_spec == "model").mean()
    out["pct_compute_unspecified"] = 100 * (r.compute_spec == "unspecified").mean()
    return out


def main() -> None:
    setup()
    d = prepare()
    nums: dict = {"NstudiesAll": len(d), "NfailsCurrent": int(d.fails_current_criteria.map(yes).sum()),
                  "NroundOne": int((d.search_round == 1).sum()), "NroundTwo": int((d.search_round == 2).sum())}
    # LaTeX command names cannot contain digits, so years and items are spelled.
    nums.update(YearFirst=int(d.Year.min()), YearLast=int(d.Year.max()),
                YearRecent=int((d.Year >= 2024).sum()), YearRecentShare=f"{100 * (d.Year >= 2024).mean():.0f}",
                YearTwentyFour=int((d.Year == 2024).sum()), YearTwentyFive=int((d.Year == 2025).sum()))
    sec = Counter(s for v in d[d.readable].sectors for s in v)   # same basis as the figures
    for s, k in sec.items():
        nums[f"Sec{SECTOR[s].split()[0].replace(',', '')}"] = k
    comp = Counter(c for v in d[d.readable].computes for c in v)
    for c, k in comp.items():
        nums[f"Comp{''.join(w[0].upper() + w[1:] for w in c.replace('x86', 'xeightsix').split('_'))}"] = k
    nums["CompNone"] = int((d[d.readable].computes.map(len) == 0).sum())
    nums["SecMulti"] = int((d[d.readable].sectors.map(len) > 1).sum())
    env = d[d.readable].eval_environment_kind.astype(str).value_counts()
    nums.update(EnvReal=int(env.get("real", 0)), EnvBoth=int(env.get("both", 0)),
                EnvSim=int(env.get("simulated", 0)), EnvUnclear=int(env.get("unclear", 0)),
                VenueConferencePct=f"{100 * d['Journal'].astype(str).str.lower().str.contains('conference|proceedings|symposium|workshop|congress').mean():.0f}")
    # Citation lists for the thin categories, so the text can point to the
    # studies behind a small count without typing record identifiers.
    def cites(mask) -> str:
        return "\\cite{" + ",".join(f"inc:{s}" for s in sorted(mask[mask].index)) + "}"
    rr = d[d.readable]
    nums.update(CiteInstrument=cites(rr["cap_instrument_reading"].map(yes)),
                CiteTracking=cites(rr["cap_target_tracking"].map(yes)),
                CiteEvent=cites(rr.modalities.map(lambda v: "event_camera" in v)),
                CiteArtefact=cites(rr["rci9_artifact"].map(yes)))
    # RQ3: does a heavier optical payload come with reported accelerated compute?
    r = d[d.readable]
    named = r[r.computes.map(len) > 0]
    gpu = named.computes.map(lambda v: "embedded_gpu" in v)
    multi = named.modalities.map(len) >= 2
    nums.update(CompMultiGpuPct=f"{100 * (multi & gpu).sum() / max(1, multi.sum()):.0f}",
                CompSingleGpuPct=f"{100 * (~multi & gpu).sum() / max(1, (~multi).sum()):.0f}")
    nums.update(CompNamed=len(named), CompGpuAmongNamed=int(gpu.sum()),
                CompMultiNamed=int(multi.sum()), CompMultiGpu=int((multi & gpu).sum()),
                CompSingleNamed=int((~multi).sum()), CompSingleGpu=int((~multi & gpu).sum()))
    # RQ4: the earlier review's holistic reproducibility judgement, at its own
    # (round-1) denominator, against the itemised index.
    base = r[(r.search_round == 1) & r.rci_total.notna()]
    rep = base["Reproducable?"].map(yes)
    nums.update(HolisticN=len(base), HolisticYes=int(rep.sum()),
                HolisticYesRCI=f"{base.loc[rep, 'rci_total'].median():.0f}",
                HolisticNoRCI=f"{base.loc[~rep, 'rci_total'].median():.0f}",
                HolisticYesArtefact=int(base.loc[rep, "rci9_artifact"].map(yes).sum()),
                HolisticYesNoSensorModel=int((~base.loc[rep, "rci2_sensors_model"].map(yes)).sum()),
                HolisticYesNoComputeModel=int((~base.loc[rep, "rci3_compute_model"].map(yes)).sum()))
    jt = d["Journal"].astype(str).str.lower()
    nums["VenueConference"] = int(jt.str.contains("conference|proceedings|symposium|workshop|congress").sum())
    tables: list[str] = []
    print("figures:")
    fig2(d, nums); fig3(d, nums); fig4(d, nums, tables); fig5(d, nums); fig6(d, nums)

    full, sens = headline(d), headline(d[~d.fails_current_criteria.map(yes)])
    s = pd.DataFrame({"all": full, "without_flagged": sens})
    s["diff_pp"] = s["without_flagged"] - s["all"]
    s.round(1).to_csv(WORK_DIR / "results_sensitivity.csv")
    pp = s.drop(index=["n_readable", "rci_median", "rci_mean"])["diff_pp"].abs()
    nums.update(NsensStudies=int(sens["n_readable"]), SensMaxDiffPP=f"{pp.max():.0f}",
                SensMaxDiffItem={**{f"pct_{k}": f"{v.split(' ', 1)[1].lower()} (RCI item {v.split()[0]})" for k, v in RCI.items()},
                                 **{f"pct_{k}": v for k, v in CAPS.items()}}.get(pp.idxmax(), pp.idxmax()),
                SensRCImedian=f"{sens['rci_median']:.0f}")

    tables = ["## Table 2 - controlled vocabulary, studies per class (readable n = "
              f"{nums['NreadableStudies']})", "",
              "| Field | Class | Studies |", "|---|---|---:|"] + \
             [f"| Sensor | {MODALITY[m]} | {k} |" for m, k in
              Counter(m for v in d[d.readable].modalities for m in v).most_common()] + \
             [f"| Compute | {COMPUTE[c]} | {k} |" for c, k in comp.most_common()] + \
             [f"| Sector | {SECTOR[x]} | {k} |" for x, k in sec.most_common()] + [""] + tables
    (WORK_DIR / "results_tables.md").write_text("\n".join(tables), encoding="utf-8")
    pd.Series(nums).to_csv(WORK_DIR / "results_numbers.csv", header=["value"])
    print(f"{len(nums)} numbers -> results_numbers.csv; sensitivity max |diff| {pp.max():.1f} pp ({pp.idxmax()})")


if __name__ == "__main__":
    main()
