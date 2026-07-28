"""Vendors: offline extraction rules (mocked LLM) + one opt-in live discovery test."""

import json
import os
from types import SimpleNamespace

import pytest

from gadded.vendors import (
    discover_vendors,
    extract_vendor_candidates,
    search_vendor_evidence,
)


class _FakeCompletions:
    def __init__(self, responder):
        self._responder = responder
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responder(kwargs)


class _FakeClient:
    def __init__(self, responder):
        self.chat = SimpleNamespace(completions=_FakeCompletions(responder))


def _json_response(payload: dict):
    def _responder(kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )
    return _responder


def _search_response(results: list[dict]):
    def _responder(kwargs):
        msg = SimpleNamespace(
            content="found some vendors",
            executed_tools=[{"type": "search", "search_results": {"results": results}}],
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    return _responder


# --------------------------------------------------------------------------- #
# extract_vendor_candidates — offline, mocked
# --------------------------------------------------------------------------- #


def test_empty_pool_skips_llm_call() -> None:
    client = _FakeClient(_json_response({"vendors": []}))
    candidates, warnings = extract_vendor_candidates([], client)
    assert candidates == []
    assert "no search evidence" in warnings[0]
    assert client.chat.completions.calls == []


def test_valid_candidate_is_kept() -> None:
    payload = {
        "vendors": [
            {
                "name": "Nile Solar Engineering",
                "websiteUrl": "https://nilesolar.example.com",
                "supportedProjectEvidence": "Installed a 2MW rooftop system in Sadat City",
                "fitExplanation": "Operates in Egypt and offers commercial rooftop EPC services.",
                "services": ["EPC", "O&M"],
                "evidence": [
                    {
                        "title": "Nile Solar project page",
                        "url": "https://nilesolar.example.com/projects",
                        "supportingText": "Installed a 2MW rooftop system in Sadat City",
                    }
                ],
                "verificationStatus": "source_supported",
            }
        ]
    }
    client = _FakeClient(_json_response(payload))
    pool = [{"title": "x", "url": "https://nilesolar.example.com/projects", "content": "y", "score": 0.9}]
    candidates, warnings = extract_vendor_candidates(pool, client)
    assert len(candidates) == 1
    assert candidates[0].name == "Nile Solar Engineering"
    assert candidates[0].contactEmail is None
    assert warnings == []


def test_missing_evidence_is_dropped() -> None:
    payload = {
        "vendors": [
            {
                "name": "No Evidence Co",
                "websiteUrl": "https://noevidence.example.com",
                "supportedProjectEvidence": "some project",
                "fitExplanation": "does solar",
                "services": [],
                "evidence": [],
                "verificationStatus": "needs_manual_verification",
            }
        ]
    }
    client = _FakeClient(_json_response(payload))
    pool = [{"title": "x", "url": "u", "content": "y", "score": 0.5}]
    candidates, warnings = extract_vendor_candidates(pool, client)
    assert candidates == []
    assert "dropped malformed" in warnings[0]


def test_forbidden_claim_is_dropped() -> None:
    payload = {
        "vendors": [
            {
                "name": "Best Solar Co",
                "websiteUrl": "https://bestsolar.example.com",
                "supportedProjectEvidence": "some project",
                "fitExplanation": "This is the best and most reliable installer in Egypt.",
                "services": [],
                "evidence": [
                    {"title": "t", "url": "https://bestsolar.example.com", "supportingText": "s"}
                ],
                "verificationStatus": "source_supported",
            }
        ]
    }
    client = _FakeClient(_json_response(payload))
    pool = [{"title": "x", "url": "u", "content": "y", "score": 0.5}]
    candidates, warnings = extract_vendor_candidates(pool, client)
    assert candidates == []
    assert "forbidden quality claim" in warnings[0]


def test_duplicate_names_deduplicated() -> None:
    payload = {
        "vendors": [
            {
                "name": "Solar Co",
                "websiteUrl": "https://solarco.example.com",
                "supportedProjectEvidence": "a",
                "fitExplanation": "b",
                "services": [],
                "evidence": [{"title": "t", "url": "https://solarco.example.com", "supportingText": "s"}],
                "verificationStatus": "source_supported",
            },
            {
                "name": " solar co ",
                "websiteUrl": "https://solarco.example.com/about",
                "supportedProjectEvidence": "a2",
                "fitExplanation": "b2",
                "services": [],
                "evidence": [{"title": "t2", "url": "https://solarco.example.com/about", "supportingText": "s2"}],
                "verificationStatus": "source_supported",
            },
        ]
    }
    client = _FakeClient(_json_response(payload))
    pool = [{"title": "x", "url": "u", "content": "y", "score": 0.5}]
    candidates, _ = extract_vendor_candidates(pool, client)
    assert len(candidates) == 1


def test_extraction_failure_returns_empty_not_raise() -> None:
    def _bad_responder(kwargs):
        raise RuntimeError("api down")

    client = _FakeClient(_bad_responder)
    pool = [{"title": "x", "url": "u", "content": "y", "score": 0.5}]
    candidates, warnings = extract_vendor_candidates(pool, client)
    assert candidates == []
    assert "vendor extraction failed" in warnings[0]


# --------------------------------------------------------------------------- #
# search_vendor_evidence — offline, mocked
# --------------------------------------------------------------------------- #


def test_search_dedupes_by_url_across_queries() -> None:
    same = {"title": "Dup", "url": "https://dup.example.com", "content": "c", "score": 0.7}
    client = _FakeClient(_search_response([same]))
    pool, warnings = search_vendor_evidence(["query one", "query two"], client)
    assert len(pool) == 1
    assert warnings == []


def test_search_failure_is_warned_not_raised() -> None:
    def _bad_responder(kwargs):
        raise RuntimeError("network down")

    client = _FakeClient(_bad_responder)
    pool, warnings = search_vendor_evidence(["q"], client)
    assert pool == []
    assert "search failed" in warnings[0]


# --------------------------------------------------------------------------- #
# Live integration (opt-in)
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="no GROQ_API_KEY set")
def test_discover_vendors_live_structural_invariants() -> None:
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

    candidates, warnings = discover_vendors(
        "10th of Ramadan City, Egypt", 475, "self_consumption", client, max_candidates=5
    )
    assert isinstance(candidates, list)
    for c in candidates:
        assert c.evidence
        text = (c.fitExplanation + c.supportedProjectEvidence).lower()
        for claim in ["best", "licensed", "certified", "guaranteed"]:
            assert claim not in text
