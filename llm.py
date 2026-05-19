"""
llm.py — single Groq wrapper used by every other module.

All LLM calls in this project go through ask_json() or ask_text().
No other module imports groq directly.

Requires:
    GROQ_API_KEY  — your Groq API key (set in .env)
    MODEL         — model string, e.g. "llama-3.3-70b-versatile" (default)
                    See https://console.groq.com/docs/models for full list.
"""

import json
import os
import sys
import time

from dotenv import load_dotenv
from groq import Groq, AuthenticationError, RateLimitError, APIConnectionError

load_dotenv()

_MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Phrases that indicate the LLM violated the anti-rewrite rule.
_REWRITE_MARKERS = ("here is a rewritten", "improved version:")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    """Remove leading ```json / ``` and trailing ``` markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        newline = text.find("\n")
        text = text[newline + 1:] if newline != -1 else text[3:]
    if text.endswith("```"):
        text = text[: text.rfind("```")].rstrip()
    return text


def _parse_json(text: str) -> dict:
    """
    Parse the first JSON object in *text*, tolerating preamble and trailing
    content (e.g. "Here is the JSON:\n{...}\nHope that helps!").

    Strategy:
        1. Find the first '{' and use JSONDecoder.raw_decode() to parse exactly
           one object starting there, stopping at the matching '}' and ignoring
           anything after it.
        2. Fall back to plain json.loads() on the full text so the error message
           is useful if no '{' is found at all.

    Raises json.JSONDecodeError if parsing fails.
    """
    start = text.find("{")
    if start != -1:
        obj, _ = json.JSONDecoder().raw_decode(text, start)
        return obj  # type: ignore[return-value]
    return json.loads(text)  # type: ignore[return-value]


def _check_no_rewrite(data: object, path: str = "") -> None:
    """Raise RuntimeError if any string field contains a rewrite marker."""
    if isinstance(data, dict):
        for key, value in data.items():
            _check_no_rewrite(value, f"{path}.{key}" if path else key)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_no_rewrite(item, f"{path}[{i}]")
    elif isinstance(data, str):
        lower = data.lower()
        for marker in _REWRITE_MARKERS:
            if marker in lower:
                raise RuntimeError(
                    f"Anti-rewrite rule violation in field '{path}': "
                    f"the LLM generated résumé content ('{marker}'). "
                    "This is not allowed — check the prompt."
                )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ask_json(
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1500,
) -> dict:
    """
    Send (system, user) to the configured Groq model, expect JSON, return as dict.

    Retries up to 3 times: on RateLimitError (exponential back-off 1s, 2s)
    and on JSONDecodeError (sends a correction message asking for valid JSON).
    Raises RuntimeError on authentication failure, connection failure, or
    if JSON cannot be parsed after the retry.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for attempt in range(3):
        try:
            response = _client.chat.completions.create(
                model=_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

        except RateLimitError:
            if attempt < 2:
                sleep_secs = 2 ** attempt  # 1s, then 2s
                print(f"Rate limit; retrying in {sleep_secs}s…", file=sys.stderr)
                time.sleep(sleep_secs)
                continue
            raise RuntimeError("Rate limit exceeded after 3 attempts. Try again later.")

        except AuthenticationError as exc:
            raise RuntimeError(
                "GROQ_API_KEY is invalid or missing. Check your .env file."
            ) from exc

        except APIConnectionError as exc:
            raise RuntimeError(f"Cannot reach Groq API. Check your network connection: {exc}") from exc

        # ---- response received ----

        choice = response.choices[0]

        if choice.finish_reason == "length":
            print(
                "WARNING: finish_reason='length'; response was truncated. "
                "JSON may be incomplete.",
                file=sys.stderr,
            )

        raw = choice.message.content or ""
        raw = _strip_fences(raw)
        print("raw: ", raw)

        try:
            parsed = _parse_json(raw)
        except json.JSONDecodeError as exc:
            if attempt < 2:
                print(
                    f"JSON parse error on attempt {attempt + 1}; retrying.",
                    file=sys.stderr,
                )
                snippet = raw[max(0, exc.pos - 20): exc.pos + 80]
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Your previous output could not be parsed as JSON.\n"
                        f"Error: {exc.msg} (at position {exc.pos})\n"
                        f"Near: ...{snippet!r}...\n\n"
                        "Please return ONLY the corrected JSON object — "
                        "no prose, no markdown fences."
                    ),
                })
                continue
            raise RuntimeError(
                f"LLM returned non-JSON after {attempt + 1} attempts. "
                f"Raw (first 300 chars):\n{raw[:300]}"
            )

        # Post-hoc anti-rewrite check on every returned JSON object.
        _check_no_rewrite(parsed)
        return parsed

    raise RuntimeError("ask_json: all retry attempts exhausted")


def ask_text(
    system: str,
    user: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 600,
) -> str:
    """
    Send (system, user) to the Groq model, return plain text.

    Same retry behaviour as ask_json for RateLimitError and
    AuthenticationError. Does not request JSON mode.
    """
    for attempt in range(3):
        try:
            response = _client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

        except RateLimitError:
            if attempt < 2:
                sleep_secs = 2 ** attempt
                print(f"Rate limit; retrying in {sleep_secs}s…", file=sys.stderr)
                time.sleep(sleep_secs)
                continue
            raise RuntimeError("Rate limit exceeded after 3 attempts.")

        except AuthenticationError as exc:
            raise RuntimeError(
                "GROQ_API_KEY is invalid or missing. Check your .env file."
            ) from exc

        except APIConnectionError as exc:
            raise RuntimeError(
                f"Cannot reach Groq API. Check your network connection: {exc}"
            ) from exc

        return response.choices[0].message.content or ""

    raise RuntimeError("ask_text: all retry attempts exhausted")