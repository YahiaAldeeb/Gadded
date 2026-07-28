"""Shared Gemini call primitives used by regulatory.py, vendors.py, and financing.py.

Every LLM-backed stage in this project needs exactly one of two things:

1. A JSON-mode or plain-text call over text already in hand (scoring, extraction,
   grounded explanation) — `gemini_json_call` / `gemini_text_call`.
2. A Google-Search-grounded call that returns real web evidence — `gemini_grounded_search`.

Gemini does not support combining server-side Google Search grounding with structured
JSON output in the same call, which is exactly why every caller in this project already
runs search and extraction as two separate stages: `gemini_grounded_search` for stage 1,
`gemini_json_call` for stage 2.

All three helpers return `None` (never raise) on any failure, so an LLM outage in one
stage never invalidates the deterministic results computed elsewhere.

`gemini-flash-latest` (the default model) always has thinking enabled and cannot be
disabled on this account tier (a `thinking_config(thinking_budget=0)` override was
rejected with 400 INVALID_ARGUMENT) — hidden reasoning tokens count against
`max_output_tokens`, so every call here budgets generously or the visible output comes
back truncated/empty, mirroring the same issue hit with Groq's reasoning model.
"""

from __future__ import annotations

import json

from google.genai import types

DEFAULT_MODEL = "gemini-flash-latest"


def gemini_json_call(
    client, model: str, system_instruction: str, user_content: str, max_output_tokens: int = 4000
) -> dict | None:
    """One JSON-mode call. Returns the parsed dict, or None on any failure."""
    try:
        resp = client.models.generate_content(
            model=model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                max_output_tokens=max_output_tokens,
            ),
        )
        return json.loads(resp.text)
    except Exception:
        return None


def gemini_text_call(
    client, model: str, system_instruction: str, user_content: str, max_output_tokens: int = 1500
) -> str | None:
    """One plain-text call. Returns the response text, or None on any failure."""
    try:
        resp = client.models.generate_content(
            model=model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_output_tokens,
            ),
        )
        return resp.text
    except Exception:
        return None


def gemini_grounded_search(
    client, model: str, query: str, max_output_tokens: int = 2000
) -> tuple[str, list[dict]] | None:
    """One Google-Search-grounded call.

    Returns `(answer_text, sources)` where `sources` is a list of
    `{"title", "url", "domain"}` dicts drawn from the grounding metadata, or None on
    any failure (including a response with no grounded sources).
    """
    try:
        resp = client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                max_output_tokens=max_output_tokens,
            ),
        )
        text = resp.text or ""
        candidate = resp.candidates[0]
        grounding = candidate.grounding_metadata
        chunks = (grounding.grounding_chunks if grounding else None) or []
        sources = [
            {"title": c.web.title, "url": c.web.uri, "domain": c.web.domain}
            for c in chunks
            if c.web and c.web.uri
        ]
        if not sources:
            return None
        return text, sources
    except Exception:
        return None
