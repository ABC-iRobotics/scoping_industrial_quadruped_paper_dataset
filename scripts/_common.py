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

MODEL = "gpt-oss:120b"


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
            response = requests.post(API_URL, headers=headers, json=payload, timeout=timeout)
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
