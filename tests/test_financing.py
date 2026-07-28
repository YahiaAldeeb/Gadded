"""Financing: offline extraction rules (mocked LLM) + one opt-in live discovery test.

search_financing_evidence uses a Groq-shaped fake client (client.chat.completions.create,
message.executed_tools); extract_financing_options uses a Gemini-shaped fake client
(client.models.generate_content) -- matching the real two-provider pipeline in
gadded.financing.
"""

import json
import os
from types import SimpleNamespace

import pytest

from gadded.financing import (
    discover_financing_options,
    extract_financing_options,
    search_financing_evidence,
)


# --------------------------------------------------------------------------- #
# Fake clients
# --------------------------------------------------------------------------- #


class _FakeGeminiModels:
    def __init__(self, responder):
        self._responder = responder
        self.calls: list[dict] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self._responder(kwargs)


class _FakeGeminiClient:
    def __init__(self, responder):
        self.models = _FakeGeminiModels(responder)


def _json_response(payload: dict):
    def _responder(kwargs):
        return SimpleNamespace(text=json.dumps(payload))
    return _responder


class _FakeGroqCompletions:
    def __init__(self, responder):
        self._responder = responder

    def create(self, **kwargs):
        return self._responder(kwargs)


class _FakeGroqClient:
    def __init__(self, responder):
        self.chat = SimpleNamespace(completions=_FakeGroqCompletions(responder))


def _search_response(results: list[dict]):
    def _responder(kwargs):
        msg = SimpleNamespace(
            content="found some banks",
            executed_tools=[{"type": "search", "search_results": {"results": results}}],
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    return _responder


# --------------------------------------------------------------------------- #
# extract_financing_options — offline, mocked (Gemini shape)
# --------------------------------------------------------------------------- #


def test_empty_pool_skips_llm_call() -> None:
    client = _FakeGeminiClient(_json_response({"options": []}))
    candidates, warnings = extract_financing_options([], client)
    assert candidates == []
    assert "no search evidence" in warnings[0]
    assert client.models.calls == []


def test_valid_option_is_kept() -> None:
    payload = {
        "options": [
            {
                "bankName": "QNB Egypt",
                "productName": "Green Loan",
                "financingRatePct": 20.0,
                "termYears": 7,
                "downPaymentPct": 20.0,
                "feesPct": None,
                "maxFinancingEgp": 400000.0,
                "notes": "Covers up to 80% of system cost.",
                "evidence": [
                    {
                        "title": "QNB Green Loan page",
                        "url": "https://qnb.example.com/green-loan",
                        "supportingText": "Covers up to 80% of system cost, tenors up to 84 months.",
                    }
                ],
                "verificationStatus": "source_supported",
            }
        ]
    }
    client = _FakeGeminiClient(_json_response(payload))
    pool = [{"title": "x", "url": "https://qnb.example.com/green-loan", "content": "y", "score": 0.9}]
    candidates, warnings = extract_financing_options(pool, client)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.bankName == "QNB Egypt"
    assert c.financingRatePct == 20.0
    assert c.feesPct == 0.0  # null coalesced to 0.0
    assert warnings == []


def test_missing_evidence_is_dropped() -> None:
    payload = {
        "options": [
            {
                "bankName": "No Evidence Bank",
                "productName": "Mystery Loan",
                "financingRatePct": 15.0,
                "termYears": 5,
                "downPaymentPct": 10.0,
                "feesPct": None,
                "evidence": [],
                "verificationStatus": "needs_manual_verification",
            }
        ]
    }
    client = _FakeGeminiClient(_json_response(payload))
    pool = [{"title": "x", "url": "u", "content": "y", "score": 0.5}]
    candidates, warnings = extract_financing_options(pool, client)
    assert candidates == []
    assert "dropped malformed" in warnings[0]


def test_forbidden_claim_is_dropped() -> None:
    payload = {
        "options": [
            {
                "bankName": "Best Bank",
                "productName": "Best Loan",
                "financingRatePct": 15.0,
                "termYears": 5,
                "downPaymentPct": 10.0,
                "feesPct": None,
                "notes": "This is the best and most reliable loan in Egypt.",
                "evidence": [{"title": "t", "url": "https://bestbank.example.com", "supportingText": "s"}],
                "verificationStatus": "source_supported",
            }
        ]
    }
    client = _FakeGeminiClient(_json_response(payload))
    pool = [{"title": "x", "url": "u", "content": "y", "score": 0.5}]
    candidates, warnings = extract_financing_options(pool, client)
    assert candidates == []
    assert "forbidden quality claim" in warnings[0]


def test_duplicate_bank_product_deduplicated() -> None:
    payload = {
        "options": [
            {
                "bankName": "Credit Agricole",
                "productName": "Solar Loan",
                "financingRatePct": 20.0,
                "termYears": 7,
                "downPaymentPct": 0.0,
                "feesPct": None,
                "evidence": [{"title": "t", "url": "https://ca.example.com", "supportingText": "s"}],
                "verificationStatus": "source_supported",
            },
            {
                "bankName": " credit agricole ",
                "productName": " solar loan ",
                "financingRatePct": 20.0,
                "termYears": 7,
                "downPaymentPct": 0.0,
                "feesPct": None,
                "evidence": [{"title": "t2", "url": "https://ca.example.com/about", "supportingText": "s2"}],
                "verificationStatus": "source_supported",
            },
        ]
    }
    client = _FakeGeminiClient(_json_response(payload))
    pool = [{"title": "x", "url": "u", "content": "y", "score": 0.5}]
    candidates, _ = extract_financing_options(pool, client)
    assert len(candidates) == 1


def test_extraction_failure_returns_empty_not_raise() -> None:
    def _bad_responder(kwargs):
        raise RuntimeError("api down")

    client = _FakeGeminiClient(_bad_responder)
    pool = [{"title": "x", "url": "u", "content": "y", "score": 0.5}]
    candidates, warnings = extract_financing_options(pool, client)
    assert candidates == []
    assert "financing extraction failed" in warnings[0]


# --------------------------------------------------------------------------- #
# search_financing_evidence — offline, mocked (Groq shape)
# --------------------------------------------------------------------------- #


def test_search_dedupes_by_url_across_queries() -> None:
    same = {"title": "Dup", "url": "https://dup.example.com", "content": "c", "score": 0.7}
    client = _FakeGroqClient(_search_response([same]))
    pool, warnings = search_financing_evidence(["query one", "query two"], client)
    assert len(pool) == 1
    assert warnings == []


def test_search_failure_is_warned_not_raised() -> None:
    def _bad_responder(kwargs):
        raise RuntimeError("network down")

    client = _FakeGroqClient(_bad_responder)
    pool, warnings = search_financing_evidence(["q"], client)
    assert pool == []
    assert "search failed" in warnings[0]


# --------------------------------------------------------------------------- #
# Live integration (opt-in)
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(
    not (os.environ.get("GROQ_API_KEY") and os.environ.get("GEMINI_API_KEY")),
    reason="needs both GROQ_API_KEY (search) and GEMINI_API_KEY (extraction)",
)
def test_discover_financing_options_live_structural_invariants() -> None:
    from dotenv import load_dotenv
    from google import genai
    from openai import OpenAI

    load_dotenv()
    search_client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
    extraction_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    candidates, warnings = discover_financing_options(
        475, 4_750_000, search_client, extraction_client, max_candidates=5
    )
    assert isinstance(candidates, list)
    for c in candidates:
        assert c.evidence
        text = (c.notes or "").lower()
        for claim in ["best", "guaranteed", "cheapest"]:
            assert claim not in text
