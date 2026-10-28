"""
Shared helpers for the SISY 2026 scoping review pipeline.

Provides three things used by every LLM-calling stage:

  * load_prompt()  - reads a prompt file from prompts/ (front matter + body),
                     so that no prompt text is embedded in the scripts
  * get_api_key()  - reads the API key from the environment, failing loudly
  * call_llm()     - the HTTP call to the OpenAI-compatible endpoint, with the
                     retry/backoff behaviour used during the original runs

Corresponds to: Section II of the paper (Research Methodology), which describes
the LLM-assisted screening and extraction pipeline.

MODEL AND SERVING
-----------------
All LLM stages used the model `gpt-oss:120b`, served through the Obuda
University OpenAI-compatible gateway at

    https://genai.uni-obuda.hu/api/chat/completions

This is an Open WebUI style endpoint in front of an Ollama backend. The exact
backend build and the server-side default sampling parameters were not recorded
at run time and cannot be reconstructed from the outputs.

NOTE ON DETERMINISM: no random seed was set on any call, and the endpoint does
not expose one. Re-running these scripts will therefore not reproduce the
published decisions token for token. The published dataset in data/ is the
authoritative record of what the model actually returned.
"""

from __future__ import annotations

import os
import random
import time
from pathlib import Path

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    load_dotenv = None


# Repository layout, resolved relative to this file. No absolute paths anywhere.
SCRIPTS_DIR = Path(__file__).resolve().parent
RELEASE_ROOT = SCRIPTS_DIR.parent
PROMPTS_DIR = RELEASE_ROOT / "prompts"
DATA_DIR = RELEASE_ROOT / "data"
WORK_DIR = RELEASE_ROOT / "work"

# OpenAI-compatible chat completions endpoint used for every LLM stage.
# Overridable so that the pipeline can be pointed at a different gateway.
DEFAULT_API_URL = "https://genai.uni-obuda.hu/api/chat/completions"
API_URL = os.environ.get("LLM_API_URL", DEFAULT_API_URL)

# The model is overridable because the RCI extraction runs TWO independent
# passes and they should not be the same model: two runs of one model produce
# correlated errors, so they agree while measuring nothing. Set LLM_MODEL (and
# LLM_API_URL if the second model lives elsewhere) for the second pass.
DEFAULT_MODEL = "gpt-oss:120b"
MODEL = os.environ.get("LLM_MODEL", DEFAULT_MODEL)

# The corpus PDFs. Not in this repository - they are copyrighted.
PDF_DIR = Path(os.environ.get("PDF_DIR", r"C:\Users\zsoldos.panna\Downloads\RIS\papers"))


def cell_text(value) -> str:
    """
    Return a spreadsheet cell as clean text, treating every flavour of "empty" alike.

    pandas hands back three different empty values depending on the column dtype:
    None, float NaN, and pd.NA. Plain `str(value or "")` mishandles all but the
    first - NaN is truthy and stringifies to "nan", and pd.NA raises TypeError on
    truth testing. This normalises all of them to "".
    """
    try:
        if value is None or pd.isna(value):
            return ""
    except (TypeError, ValueError):
        # pd.isna raises on array-likes; those are never empty scalars.
        pass
    text = str(value).strip()
    return "" if text.lower() in ("nan", "<na>", "none") else text


def get_api_key() -> str:
    """
    Return the LLM API key from the environment.

    Loads a local .env file if python-dotenv is available, so that a developer
    can keep credentials in an untracked .env instead of exporting them by hand.

    Raises SystemExit with an actionable message if the key is not set. The key
    is never written to disk, logged, or printed by any script in this release.
    """
    if load_dotenv is not None:
        load_dotenv(RELEASE_ROOT / ".env")

    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "ERROR: environment variable LLM_API_KEY is not set.\n"
            "\n"
            "The LLM stages of this pipeline need an API key for the\n"
            f"OpenAI-compatible endpoint at {API_URL}\n"
            "\n"
            "Set it in your shell:\n"
            "    export LLM_API_KEY=...            (Linux / macOS)\n"
            "    $env:LLM_API_KEY = '...'          (Windows PowerShell)\n"
            "\n"
            "or copy .env.example to .env and fill in the value there.\n"
            "Never commit .env - it is listed in .gitignore."
        )
    return key


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """
    Split a prompt file into its front matter mapping and its body.

    The front matter is a small `key: value` block delimited by lines of `---`.
    Only the scalar forms this project needs are supported: quoted strings,
    bare strings, integers, floats and `null`. Kept dependency-free on purpose -
    adding a YAML parser for six keys is not worth the extra requirement.
    """
    if not text.startswith("---"):
        return {}, text

    _, _, rest = text.partition("---")
    raw_meta, sep, body = rest.partition("\n---")
    if not sep:
        return {}, text

    meta: dict = {}
    for line in raw_meta.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            meta[key] = value[1:-1]
            continue
        if value in ("null", "None", ""):
            meta[key] = None
            continue
        try:
            meta[key] = int(value)
            continue
        except ValueError:
            pass
        try:
            meta[key] = float(value)
            continue
        except ValueError:
            pass
        meta[key] = value

    return meta, body.lstrip("\n")


def load_prompt(name: str) -> tuple[str, str, dict]:
    """
    Load a prompt from prompts/<name>.md.

    Returns (system_message, user_template, sampling_params).

    The user template contains a `{record}` placeholder. Callers substitute the
    record text with str.replace() rather than str.format(), because the prompt
    bodies contain literal braces and JSON-ish examples that would otherwise be
    interpreted as format fields.

    Sampling parameters live in the prompt front matter so that each stage keeps
    the exact temperature / max_tokens / presence_penalty it was run with. These
    differ per stage and must not be unified.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise SystemExit(f"ERROR: prompt file not found: {path}")

    meta, body = _parse_front_matter(path.read_text(encoding="utf-8"))

    system = meta.get("system") or ""
    params = {
        key: meta.get(key)
        for key in ("temperature", "max_tokens", "presence_penalty")
        if meta.get(key) is not None
    }
    # Qwen3.8-Flash-Next spends part of the completion budget on reasoning the
    # endpoint does not return. On long chunks it exhausts max_tokens before
    # writing any content and the reply comes back empty. LLM_MAX_TOKENS raises
    # the cap for such a re-run; it bounds output length and changes no sampling
    # behaviour. Any use is printed so it lands in the run log.
    override = os.environ.get("LLM_MAX_TOKENS")
    if override:
        params["max_tokens"] = int(override)
        print(f"NOTE: max_tokens overridden to {override} by LLM_MAX_TOKENS for prompt '{name}'")
    return system, body, params


def call_llm(
    system_message: str,
    user_message: str,
    params: dict | None = None,
    max_attempts: int = 8,
    base_delay: float = 4.0,
    timeout: int = 120,
) -> str | None:
    """
    Send one chat completion request and return the assistant's message content.

    Retries on transport errors with exponential backoff plus jitter, matching
    the behaviour of the original screening runs. Returns None if the server
    answers with an empty content field or if every attempt fails; callers
    decide how to record that.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
    }
    payload.update(params or {})

    delay = base_delay
    for attempt in range(max_attempts):
        try:
            # LLM_TIMEOUT overrides the per-request timeout. Qwen3.8-Flash-Next
            # can reason for ~7,000 tokens on a 30k-character chunk and take
            # three minutes, past the 120 s default; the timed-out call then
            # came back as an empty reply (measured 20 Oct 2026).
            response = requests.post(API_URL, headers=headers, json=payload,
                                     timeout=int(os.environ.get("LLM_TIMEOUT", timeout)))
            response.raise_for_status()
            message = response.json().get("choices", [{}])[0].get("message", {})
            content = (message.get("content") or "").strip()
            return content or None
        except requests.exceptions.RequestException as err:
            if attempt == max_attempts - 1:
                print(f"  [API] giving up after {max_attempts} attempts: {err}")
                return None
            sleep_for = delay + random.random()
            print(f"  [API] busy, retrying in {sleep_for:.1f}s...")
            time.sleep(sleep_for)
            delay *= 2
    return None


# ---------------------------------------------------------------------------
# Added for the Sensors paper. Not part of the SISY release.
#
# The SISY pipeline read the first 25 000 characters of each PDF, a window
# chosen because hardware specifications sit on pages 6-8. Measured across the
# 88-study corpus, that window truncates 74 of 88 documents (median length
# 36 556 chars, p90 87 495, max 159 323) and, more importantly, it cuts off the
# implementation and experiments sections where the evidence for RCI items 4, 6
# and 7 actually lives. See analysis/README.md for the measurement.
# ---------------------------------------------------------------------------

import json
import re


_COMMON_WORDS = {"the", "and", "of", "to", "in", "is", "for", "a", "with",
                 "robot", "that", "on", "are", "this", "by"}


def english_share(text: str) -> float:
    """Share of alphabetic tokens that are very common English words.

    Readable English text scores about 0.2-0.35. A text layer whose font
    encoding is broken scores near zero, even though its character count looks
    normal - which is why the characters-per-page guard of amendment A2 cannot
    see it.
    """
    words = re.findall(r"[A-Za-z]+", text)
    if not words:
        return 0.0
    return sum(w.lower() in _COMMON_WORDS for w in words) / len(words)


def _decode_shifted(page_text: str) -> str:
    """Repair a page whose font maps every glyph 29 code points too low.

    Found 7 Oct 2026 in paper011 and paper028: "WKH" for "the", "URERW" for
    "robot". The characters-per-page guard passed both, and pass A coded
    paper011 as reporting nothing at all. The shift is applied only when it
    makes the page markedly more English; ordinary pages are returned as is.
    Whitespace is left alone because these PDFs keep real spaces and newlines.
    """
    if english_share(page_text) >= 0.10:
        return page_text
    shifted = "".join(
        chr(ord(c) + 29) if 33 <= ord(c) <= 93 or 3 <= ord(c) <= 8 or 11 <= ord(c) <= 12 or 14 <= ord(c) <= 31 else c
        for c in page_text
    )
    before, after = english_share(page_text), english_share(shifted)
    return shifted if after >= 0.12 and after > 1.5 * before else page_text


def pdf_text(pdf_path: Path, max_chars: int | None = None) -> str:
    """
    Return a PDF's text with whitespace collapsed, in full unless capped.

    Same normalisation as the SISY pipeline's extract_pdf_text(), but the
    character cap is now opt-in rather than a hardcoded 25 000. Pass max_chars
    only when you deliberately want a truncated read; the RCI stage chunks
    instead, so that no part of the document is silently unread.

    PyMuPDF is imported here rather than at module scope so that the screening
    stages, which never touch a PDF, keep running without it installed.
    """
    import fitz  # PyMuPDF

    try:
        document = fitz.open(pdf_path)
    except Exception as error:
        print(f"  PDF read error: {pdf_path} -> {error}")
        return ""

    try:
        pages = [_decode_shifted(page.get_text("text")) for page in document]
    finally:
        document.close()

    text = " ".join("\n".join(t for t in pages if t).split())
    return text[:max_chars] if max_chars else text


def chunk_text(text: str, chunk_chars: int, overlap: int) -> list[tuple[int, str]]:
    """
    Split text into overlapping windows, returning (start_offset, chunk) pairs.

    The overlap exists so that a sentence straddling a boundary is still seen
    whole by at least one chunk - without it, the evidence quote for an item can
    be cut in half and lost by both neighbours. The start offset travels with
    the chunk so that an extracted quote can be located in the source document
    during human validation.
    """
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be positive")
    if overlap >= chunk_chars:
        raise ValueError("overlap must be smaller than chunk_chars")

    if len(text) <= chunk_chars:
        return [(0, text)]

    chunks: list[tuple[int, str]] = []
    start = 0
    step = chunk_chars - overlap
    while start < len(text):
        chunks.append((start, text[start:start + chunk_chars]))
        if start + chunk_chars >= len(text):
            break
        start += step
    return chunks


def parse_json_reply(answer: str | None) -> dict | None:
    """
    Pull a JSON object out of a model reply, tolerating the usual wrappers.

    Models wrap JSON in code fences, prepend "Here is the extraction:", or emit
    a stray trailing line. This strips fences and falls back to the outermost
    balanced {...} span. Returns None when nothing parses - callers must treat
    that as a failed extraction and record it, never as an empty result, or
    silent parse failures become fabricated "not reported" findings.
    """
    if not answer:
        return None

    text = re.sub(r"```(?:json)?", "", answer).strip()

    # strict=False: verbatim quotes copied from PDF text can carry raw control
    # characters (a multiplication sign extracted as \x03, say). Strict JSON
    # rejects those, which turned one complete, valid reply into an
    # "incomplete" record whose items all read as not found.

    try:
        value = json.loads(text, strict=False)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        value = json.loads(text[start:end + 1], strict=False)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None


def merge_free_text(values: list[str], separator: str = ",") -> str:
    """
    Collapse the same free-text field seen across many chunks into one string.

    A plain union keeps every variant a document uses, which for a long paper
    means "construction sites, construction settings, construction site,
    construction environments" - four entries carrying one fact. The controlled
    vocabulary is signed off by a human reading these raw strings, so the noise
    is paid for in the scarcest resource in the project.

    So: case-insensitive de-duplication, then drop any entry that is contained
    in another kept entry. Distinct phrasings survive; restatements do not.
    Nothing is truncated - a long list means the paper really did say many
    different things, and the human should see that.
    """
    seen: list[str] = []
    for value in values:
        for part in str(value or "").split(separator):
            part = " ".join(part.split())
            if part and part.lower() not in {s.lower() for s in seen}:
                seen.append(part)

    kept = [
        entry for entry in seen
        if not any(other is not entry and entry.lower() in other.lower() for other in seen)
    ]
    return ", ".join(kept)


# A PDF page carrying a real text layer yields on the order of a few thousand
# characters. An image-only page yields a few hundred - headers and page
# furniture picked out of the margins. The corpus shows the gap plainly: the
# lowest genuine document runs 1,981 chars/page, the median 4,795, and the one
# scanned document 360. Anything under this bound is not a short paper, it is an
# unread one.
MIN_CHARS_PER_PAGE = 1000


def pdf_page_count(pdf_path) -> int:
    """Page count, or 0 when the file cannot be opened."""
    import fitz
    try:
        with fitz.open(pdf_path) as document:
            return document.page_count
    except Exception:  # noqa: BLE001
        return 0


def text_layer_ok(text: str, pages: int) -> tuple[bool, float]:
    """
    Is there enough extracted text for the document to be judged at all?

    Returns (usable, chars_per_page). A document that fails this must NOT be
    coded: every item would come back "not reported", which is indistinguishable
    from a finding and biases every prevalence downward. Failing loudly costs one
    manual retrieval; failing silently costs a wrong number in the paper.
    """
    if pages <= 0:
        return False, 0.0
    ratio = len(text) / pages
    return ratio >= MIN_CHARS_PER_PAGE, ratio
