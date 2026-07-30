"""
Stage 4 - analysis and figures.

WHAT IT DOES
    Reads the published dataset, consolidates the free-text coded variables into
    the categories reported in the paper, prints every headline statistic, and
    regenerates Figures 2, 3 and 4.

INPUTS
    data/SISY2026_ScopingIndustrialQuadruped.xlsx
    data/sector_mapping.csv     raw "Industry sector" value -> consolidated sector
    data/usecase_mapping.csv    raw "High-level goal" value  -> use case category

OUTPUTS
    figures/fig2_usecases_by_sector.png
    figures/fig3_platforms.png
    figures/fig4_validation_opensource_by_sector.png
    printed summary of every statistic reported in Section III

PAPER REFERENCE
    Section III (Results), Figures 2, 3 and 4.

IMPORTANT - THIS SCRIPT IS NEW CODE
    The original working directory contained no analysis or plotting script. The
    figures and percentages in the paper were produced outside the codebase. This
    script reconstructs that analysis from the published dataset. Treat any
    mismatch against the paper as a finding to investigate, not as a bug to
    silence - see README.md, "Known discrepancies".

THE TWO MAPPING FILES
    The paper reports eight consolidated industry sectors and five use case
    categories, but the dataset stores both as free text (23 distinct sector
    values, 87 distinct goal values). The lookup tables that produced the
    consolidation were not preserved.

    sector_mapping.csv and usecase_mapping.csv make that consolidation explicit
    and reviewable. Run this script with --init-mappings to generate stubs listing
    every raw value, then fill in the target category. Rows left blank are
    reported as unmapped and the affected figure is skipped rather than being
    drawn from partial data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (backend must be set first)

from _common import DATA_DIR, RELEASE_ROOT  # noqa: E402

FIGURES_DIR = RELEASE_ROOT / "figures"
SECTOR_MAP_PATH = DATA_DIR / "sector_mapping.csv"
USECASE_MAP_PATH = DATA_DIR / "usecase_mapping.csv"
OVERRIDES_PATH = DATA_DIR / "record_overrides.csv"

# Robot platform consolidation. Rules are tried in order and the first match
# wins, so the Unitree test deliberately precedes the Custom test: a record
# labelled "Custom quadruped robot (Unitree)" counts as Unitree.
PLATFORM_OVERRIDES = {
    # A commercial walking excavator, not a custom quadruped research platform.
    "menzi muck m545 (custom heap)": "Other / Unknown",
}
PLATFORM_RULES = [
    ("anymal", "ANYbotics ANYmal"),
    ("spot", "Boston Dynamics Spot"),
    ("unitree", "Unitree"),
    ("custom", "Custom"),
    ("unspecified", "Other / Unknown"),
]
PLATFORM_ORDER = ["Unitree", "Custom", "Boston Dynamics Spot", "ANYbotics ANYmal", "Other / Unknown"]

USECASE_ORDER = [
    "Visual & Thermal Inspection",
    "3D Mapping & Digital Twins",
    "Safety & Hazard Detection",
    "Logistics & Handling",
    "Exploration & Other",
]

# Colours follow the figures in the paper.
USECASE_COLORS = ["#1f77b4", "#2ca02c", "#ff7f0e", "#7fc3e8", "#a6a6a6"]
PLATFORM_COLORS = ["#1f77b4", "#2ca02c", "#ff7f0e", "#7fc3e8", "#a6a6a6"]


def classify_platform(value: str) -> str:
    """Map a free-text platform string onto one of the five reported groups."""
    lowered = str(value).strip().lower()
    if lowered in PLATFORM_OVERRIDES:
        return PLATFORM_OVERRIDES[lowered]
    for needle, group in PLATFORM_RULES:
        if needle in lowered:
            return group
    return "Other / Unknown"


def load_mapping(path: Path, key_column: str, value_column: str) -> dict[str, str]:
    """Load a raw-value -> category lookup, ignoring rows with a blank target."""
    if not path.exists():
        return {}
    frame = pd.read_csv(path).fillna("")
    return {
        str(row[key_column]).strip(): str(row[value_column]).strip()
        for _, row in frame.iterrows()
        if str(row[value_column]).strip()
    }


def init_mappings(frame: pd.DataFrame) -> None:
    """Write stub mapping files listing every distinct raw value."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sectors = sorted(frame["Industry sector"].astype(str).str.strip().unique())
    pd.DataFrame(
        {"raw_value": sectors, "consolidated_sector": [""] * len(sectors)}
    ).to_csv(SECTOR_MAP_PATH, index=False, encoding="utf-8")

    goals = sorted(frame["High-level goal"].astype(str).str.strip().unique())
    pd.DataFrame(
        {"raw_value": goals, "use_case": [""] * len(goals)}
    ).to_csv(USECASE_MAP_PATH, index=False, encoding="utf-8")

    print(f"Wrote stub: {SECTOR_MAP_PATH}  ({len(sectors)} distinct values)")
    print(f"Wrote stub: {USECASE_MAP_PATH}  ({len(goals)} distinct values)")
    print("\nFill in the empty column in each file, then re-run without --init-mappings.")


def apply_overrides(frame: pd.DataFrame) -> int:
    """
    Apply per-record category overrides from record_overrides.csv.

    The consolidation was a per-record reviewer decision, not a pure lookup: a
    handful of studies belong to a different sector or use case than their raw
    free-text label implies. Each override carries a written justification in
    the CSV so the reasoning is auditable rather than buried in code.

    Returns the number of cells overridden.
    """
    if not OVERRIDES_PATH.exists():
        return 0

    overrides = pd.read_csv(OVERRIDES_PATH).fillna("")
    # Lines whose first field starts with '#' are commentary, not overrides. Plain CSV
    # has no comment syntax, and read_csv(comment='#') would also truncate any
    # justification text containing a '#', so filter on the key column instead.
    overrides = overrides[~overrides["pdf_name"].astype(str).str.strip().str.startswith("#")]

    applied = 0
    for _, row in overrides.iterrows():
        mask = frame["Pdf name"].astype(str).str.strip() == str(row["pdf_name"]).strip()
        if not mask.any():
            print(f"  WARNING: override for unknown record {row['pdf_name']!r} - ignored")
            continue
        for column, key in (("Sector", "sector"), ("Use case", "use_case")):
            value = str(row.get(key, "")).strip()
            if value and column in frame.columns:
                frame.loc[mask, column] = value
                applied += 1
    return applied


def report_unmapped(series: pd.Series, mapping: dict[str, str], label: str) -> bool:
    """Print any raw values missing from a mapping. Returns True if complete."""
    values = series.astype(str).str.strip()
    missing = sorted({value for value in values if value not in mapping})
    if not missing:
        return True
    print(f"\n  {label}: {len(missing)} raw value(s) not mapped - figure skipped:")
    for value in missing:
        count = int((values == value).sum())
        print(f"    {count:3d}  {value!r}")
    return False


def plot_usecases_by_sector(frame: pd.DataFrame, sector_order: list[str]) -> Path:
    """Figure 2 - stacked bars of use case counts within each sector."""
    table = (
        pd.crosstab(frame["Sector"], frame["Use case"])
        .reindex(index=sector_order, columns=USECASE_ORDER)
        .fillna(0)
        .astype(int)
    )
    table = table.loc[table.sum(axis=1).sort_values(ascending=True).index]

    fig, axes = plt.subplots(figsize=(10, 5))
    left = [0] * len(table)
    for column, color in zip(USECASE_ORDER, USECASE_COLORS):
        axes.barh(table.index, table[column], left=left, label=column, color=color)
        left = [a + b for a, b in zip(left, table[column])]

    for index, total in enumerate(table.sum(axis=1)):
        axes.text(total + 0.2, index, str(total), va="center", fontsize=9)

    labels = [f"{name} (n={total})" for name, total in zip(table.index, table.sum(axis=1))]
    axes.set_yticks(range(len(table)))
    axes.set_yticklabels(labels)
    axes.set_xlabel("Number of studies")
    axes.legend(loc="lower right", fontsize=8)
    axes.grid(axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()

    path = FIGURES_DIR / "fig2_usecases_by_sector.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_platforms(frame: pd.DataFrame) -> Path:
    """Figure 3 - donut chart of platform shares."""
    counts = frame["Platform"].value_counts().reindex(PLATFORM_ORDER).fillna(0).astype(int)
    total = int(counts.sum())

    fig, axes = plt.subplots(figsize=(6.5, 6.5))
    wedges, _, _ = axes.pie(
        counts,
        labels=counts.index,
        autopct=lambda pct: f"{pct:.1f}%",
        startangle=90,
        counterclock=False,
        colors=PLATFORM_COLORS,
        wedgeprops={"width": 0.45},
        pctdistance=0.78,
    )
    axes.text(0, 0, f"n = {total}", ha="center", va="center", fontsize=13)
    axes.set_aspect("equal")
    fig.tight_layout()

    path = FIGURES_DIR / "fig3_platforms.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def plot_validation_opensource(frame: pd.DataFrame, sector_order: list[str]) -> Path:
    """Figure 4 - validation and open-source rates within each sector."""
    grouped = frame.groupby("Sector")
    validation = grouped["Validated"].mean().reindex(sector_order) * 100
    open_source = grouped["OpenSource"].mean().reindex(sector_order) * 100

    positions = range(len(sector_order))
    height = 0.38

    fig, axes = plt.subplots(figsize=(8, 5))
    axes.barh(
        [p + height / 2 for p in positions], validation, height,
        label="Real-world validation", color="#1f77b4",
    )
    axes.barh(
        [p - height / 2 for p in positions], open_source, height,
        label="Open-source availability", color="#e8a33d",
    )

    for position, value in zip(positions, validation):
        axes.text(value - 2, position + height / 2, f"{value:.1f}%", va="center",
                  ha="right", color="white", fontsize=8)
    for position, value in zip(positions, open_source):
        axes.text(value + 1, position - height / 2, f"{value:.1f}%", va="center", fontsize=8)

    axes.set_yticks(list(positions))
    axes.set_yticklabels(sector_order)
    axes.invert_yaxis()
    axes.set_xlim(0, 105)
    axes.set_xlabel("Share of studies within sector")
    axes.legend(fontsize=8)
    axes.grid(axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()

    path = FIGURES_DIR / "fig4_validation_opensource_by_sector.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--input", default=str(DATA_DIR / "SISY2026_ScopingIndustrialQuadruped.xlsx"))
    parser.add_argument("--init-mappings", action="store_true",
                        help="write stub mapping files and exit")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"ERROR: input not found: {input_path}\nRun 05_build_public_dataset.py first.")

    frame = pd.read_excel(input_path)

    if args.init_mappings:
        init_mappings(frame)
        return

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Dataset: {input_path}")
    print(f"Included studies: {len(frame)}")

    # --- Platform (Figure 3, RQ2) -----------------------------------------
    frame["Platform"] = frame["Robot platform"].map(classify_platform)
    print("\nRobot platforms (Fig. 3):")
    counts = frame["Platform"].value_counts().reindex(PLATFORM_ORDER).fillna(0).astype(int)
    for name, count in counts.items():
        print(f"  {count:3d}  {count / len(frame):6.1%}  {name}")

    # --- Validation and open source (RQ3) ---------------------------------
    frame["Validated"] = frame["Real-world validation?"].astype(str).str.strip().str.upper().str.startswith("Y")
    frame["OpenSource"] = frame["Open source?"].astype(str).str.strip().str.upper().str.startswith("Y")
    validated = int(frame["Validated"].sum())
    open_source = int(frame["OpenSource"].sum())
    print(f"\nReal-world validation: {validated}/{len(frame)} ({validated / len(frame):.1%})")
    print(f"Open source:           {open_source}/{len(frame)} ({open_source / len(frame):.1%})")

    figures = [plot_platforms(frame)]

    # --- Sector and use case (Figures 2 and 4, RQ1) -----------------------
    sector_map = load_mapping(SECTOR_MAP_PATH, "raw_value", "consolidated_sector")
    usecase_map = load_mapping(USECASE_MAP_PATH, "raw_value", "use_case")

    sectors_ok = report_unmapped(frame["Industry sector"], sector_map, "Industry sector")
    usecases_ok = report_unmapped(frame["High-level goal"], usecase_map, "High-level goal")

    if not sector_map and not usecase_map:
        print(f"\n  No mapping files found. Run with --init-mappings to create stubs at\n"
              f"    {SECTOR_MAP_PATH}\n    {USECASE_MAP_PATH}")

    if sectors_ok:
        frame["Sector"] = frame["Industry sector"].astype(str).str.strip().map(sector_map)
        if usecases_ok:
            frame["Use case"] = frame["High-level goal"].astype(str).str.strip().map(usecase_map)

        overridden = apply_overrides(frame)
        if overridden:
            print(f"\nPer-record overrides applied: {overridden}"
                  f" (see {OVERRIDES_PATH.name} for the justification of each)")

        sector_order = list(frame["Sector"].value_counts().index)

        print("\nIndustry sectors (Fig. 2 row totals):")
        for name, count in frame["Sector"].value_counts().items():
            print(f"  {count:3d}  {name}")

        print("\nPer-sector validation and open source (Fig. 4):")
        grouped = frame.groupby("Sector")
        for name in sector_order:
            group = grouped.get_group(name)
            print(f"  {name:24s}  n={len(group):3d}  validated {group['Validated'].mean():6.1%}"
                  f"   open source {group['OpenSource'].mean():6.1%}")

        figures.append(plot_validation_opensource(frame, sector_order))

        if usecases_ok:
            print("\nUse case categories (Fig. 2 segments):")
            for name in USECASE_ORDER:
                count = int((frame["Use case"] == name).sum())
                print(f"  {count:3d}  {name}")

            print("\nSector x use case cross-tabulation (Fig. 2):")
            table = (
                pd.crosstab(frame["Sector"], frame["Use case"])
                .reindex(index=sector_order, columns=USECASE_ORDER)
                .fillna(0)
                .astype(int)
            )
            print(table.to_string())

            figures.append(plot_usecases_by_sector(frame, sector_order))

    print("\nFigures written:")
    for path in figures:
        print(f"  {path}")


if __name__ == "__main__":
    main()
