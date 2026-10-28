"""
Stage 54 - cite every included study, and tabulate them.

PRISMA-ScR asks for the included sources to be listed with their charted
characteristics. This stage builds, from data/charting_v2.xlsx:

    ../tables/bib_included.tex      one \\bibitem per included study (key inc:<record_id>),
                                    bibliographic data from Crossref by DOI where a
                                    DOI exists, else from the screening record
    ../tables/tab_included.tex      longtable: citation, year, sector, optical
                                    modalities, onboard compute class, capabilities,
                                    RCI, and the sensitivity flag

Crossref replies are cached in work/crossref_cache.json, so the stage is
repeatable offline and the cache documents exactly what was fetched.
"""
from __future__ import annotations

import importlib.util
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from _common import WORK_DIR

SCRIPTS = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("res", SCRIPTS / "50_results.py")
res = importlib.util.module_from_spec(_s)
_s.loader.exec_module(res)

OUT = WORK_DIR.parent.parent / "tables"
CACHE = WORK_DIR / "crossref_cache.json"
CAP_SHORT = {"cap_slam_mapping": "M", "cap_autonomous_navigation": "N", "cap_obstacle_avoidance": "O",
             "cap_object_detection": "D", "cap_instrument_reading": "I", "cap_target_tracking": "T"}
MOD_SHORT = {"lidar": "L", "rgb_camera": "C", "depth_rgbd": "D", "thermal_ir": "T", "stereo": "S", "event_camera": "E"}
COMP_SHORT = {"embedded_gpu": "GPU", "x86_mini_pc": "x86", "laptop_workstation": "CPU",
              "sbc_microcontroller": "SBC", "vendor_integrated": "Vendor"}
SEC_SHORT = {"general_industrial": "Gen.", "construction": "Constr.", "mining": "Mining", "energy_power": "Energy",
             "oil_gas_chemical": "Oil/gas/chem.", "nuclear": "Nuclear", "manufacturing": "Manuf.", "other": "Other"}


def tex(s: str) -> str:
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def crossref(doi: str, cache: dict) -> dict | None:
    if doi in cache:
        return cache[doi]
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "scoping-review-refs/1.0"}),
                                    timeout=30) as r:
            msg = json.load(r)["message"]
    except Exception as e:  # noqa: BLE001 - a failed lookup falls back to the screening record
        print(f"  crossref failed for {doi}: {e}")
        msg = None
    cache[doi] = msg
    time.sleep(0.2)
    return msg


def authors_mdpi(names: list[tuple[str, str]]) -> str:
    out = []
    for family, given in names:
        initials = "".join(f"{p[0]}." for p in re.split(r"[\s\-]+", given) if p) if given else ""
        out.append(f"{family}, {initials}".strip().rstrip(","))
    if len(out) > 10:
        out = out[:10] + ["et al."]
    return "; ".join(out)


def bibitem(sid: str, row, msg: dict | None) -> str:
    if msg:
        names = [(a.get("family", ""), a.get("given", "")) for a in msg.get("author", []) if a.get("family")]
        title = (msg.get("title") or [row.Title])[0]
        venue = (msg.get("container-title") or [row.Journal])[0]
        year = (msg.get("issued", {}).get("date-parts") or [[row.Year]])[0][0]
        vol, page = msg.get("volume"), msg.get("page") or msg.get("article-number")
        kind = msg.get("type", "")
        doi = msg.get("DOI")
    else:
        names = [(a.split(",")[0].strip(), a.split(",")[1].strip() if "," in a else "")
                 for a in str(row.Author).split(";") if a.strip() and str(row.Author) != "nan"]
        title, venue, year, vol, page, kind, doi = row.Title, row.Journal, row.Year, None, None, "", None
        if str(row.Doi) not in ("nan", "na", ""):
            doi = str(row.Doi)
    auth = authors_mdpi(names) or "Anonymous"
    first = names[0][0] if names else "Anon."
    head = f"\\bibitem[{tex(first)}{' et al.' if len(names) > 1 else ''}({year})]{{inc:{sid}}}"
    title = tex(re.sub(r"<[^>]+>", "", str(title)))
    page = str(page).replace("-", "--") if page else page
    venue = tex(str(venue)) if str(venue) != "nan" else ""
    if "proceedings" in kind or "conference" in venue.lower() or "proceedings" in venue.lower():
        body = f"{tex(auth)} {title}. In \\emph{{{venue}}}; {year}" + (f"; pp. {tex(page)}" if page else "") + "."
    else:
        body = (f"{tex(auth)} {title}. \\emph{{{venue}}} \\textbf{{{year}}}"
                + (f", \\emph{{{tex(vol)}}}" if vol else "") + (f", {tex(page)}" if page else "") + ".")
    if doi:
        body += f" \\url{{https://doi.org/{doi.lower()}}}"
    return head + "\n" + body


def main() -> None:
    OUT.mkdir(exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    d = res.prepare().sort_values("Year", kind="stable")
    items, rows = [], []
    for sid, row in d.iterrows():
        doi = str(row.Doi).strip()
        msg = crossref(doi, cache) if doi not in ("nan", "na", "") else None
        items.append(bibitem(sid, row, msg))
        mods = "".join(MOD_SHORT[m] for m in res.MODALITY if m in row.modalities) or "--"
        comp = ", ".join(COMP_SHORT[c] for c in res.COMPUTE if c in row.computes) or "--"
        caps = "".join(v for k, v in CAP_SHORT.items() if res.yes(row[k])) or "--"
        sec = ", ".join(SEC_SHORT[s] for s in row.sectors) or "--"
        rci = "--" if pd.isna(row.rci_total) else f"{int(row.rci_total)}"
        flag = r"$\dagger$" if res.yes(row.fails_current_criteria) else ""
        authors = [a.get("family", "") for a in (msg or {}).get("author", []) if a.get("family")] or \
            [a.split(",")[0].strip() for a in str(row.Author).split(";") if a.strip() and str(row.Author) != "nan"]
        who = tex(authors[0]) + (" et al." if len(authors) > 1 else "") if authors else ""
        rows.append(f"{who}~\\cite{{inc:{sid}}}{flag} & {int(row.Year)} & {sec} & {mods} & {comp} & {caps} & {rci}\\\\")
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "bib_included.tex").write_text("\n\n".join(items) + "\n", encoding="utf-8")
    head = [r"\begin{longtable}{lllllll}", r"\toprule",
            r"\textbf{Study} & \textbf{Year} & \textbf{Sector} & \textbf{Modalities} & \textbf{Compute} & "
            r"\textbf{Capabilities} & \textbf{RCI}\\", r"\midrule", r"\endhead", r"\bottomrule", r"\endfoot"]
    (OUT / "tab_included.tex").write_text("\n".join(head + rows + [r"\end{longtable}"]) + "\n", encoding="utf-8")
    print(f"{len(items)} studies; crossref hits {sum(1 for v in cache.values() if v)} of {len(cache)} DOIs looked up")


if __name__ == "__main__":
    main()
