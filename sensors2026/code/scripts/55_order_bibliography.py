"""
Stage 55 - number the references in order of first citation, as MDPI requires.

The hand-written references live in ../tables/bib_manual.tex and the included
studies in ../tables/bib_included.tex (stage 54). This stage reads main.tex in
reading order - following \\input{tables/...} files and the citation macros of
numbers.tex at the point where they occur - records the order in which keys
are first cited, and writes ../tables/bib_all.tex with the entries in that
order. main.tex's thebibliography holds only \\input{tables/bib_all}.

A key cited but missing from both sources, or a hand-written entry never cited,
stops the stage. Included studies not cited in the main text are listed only in
the supplementary Table S2.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TABLES = ROOT / "tables"
CITE = re.compile(r"\\cite(?:\[[^\]]*\])?\{([^}]*)\}")
INPUT = re.compile(r"\\input\{(tables/[^}]+)\}")


def entries(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?=\\bibitem)", text)
    out = {}
    for part in parts:
        m = re.match(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", part)
        if m:
            out[m.group(1)] = part.strip()
    return out


def main() -> None:
    macros = {}
    for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{(.*)\}\s*$", (ROOT / "numbers.tex").read_text(encoding="utf-8"), re.M):
        macros[m.group(1)] = m.group(2)
    text = (ROOT / "main.tex").read_text(encoding="utf-8")
    body = text[: text.index(r"\begin{thebibliography}")]
    body = re.sub(r"(?m)(?<!\\)%.*$", "", body)

    order: list[str] = []

    def scan(s: str) -> None:
        pos = 0
        token = re.compile(r"\\cite(?:\[[^\]]*\])?\{[^}]*\}|\\input\{tables/[^}]+\}|\\(" +
                           "|".join(re.escape(k) for k in macros if k.startswith("Cite")) + r")\b")
        for m in token.finditer(s):
            tok = m.group(0)
            if tok.startswith("\\cite"):
                for k in CITE.match(tok).group(1).split(","):
                    k = k.strip()
                    if k and k not in order:
                        order.append(k)
            elif tok.startswith("\\input"):
                f = ROOT / (INPUT.match(tok).group(1) + ("" if tok.endswith(".tex}") else ".tex"))
                if f.exists() and f.name != "bib_all.tex":
                    scan(f.read_text(encoding="utf-8"))
            else:
                scan(macros[m.group(1)])
            pos = m.end()

    scan(body)
    manual = entries(TABLES / "bib_manual.tex")
    pool = {**manual, **entries(TABLES / "bib_included.tex")}
    missing = [k for k in order if k not in pool]
    # Every hand-written reference must be cited; included studies are all
    # listed with full references in Supplementary Table S2, so only those the
    # main text cites enter the main reference list.
    unused = [k for k in manual if k not in order]
    if missing:
        raise SystemExit(f"ERROR: cited but not defined: {missing}")
    if unused:
        raise SystemExit(f"ERROR: defined but never cited: {unused}")
    (TABLES / "bib_all.tex").write_text("\n\n".join(pool[k] for k in order) + "\n", encoding="utf-8")
    print(f"{len(order)} references in order of first citation")


if __name__ == "__main__":
    main()
