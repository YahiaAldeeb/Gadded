"""Regulatory: retrieval relevance, deterministic rules, citation completeness, LLM grounding."""

import os
from pathlib import Path

import pytest

from gadded.regulatory import (
    build_context,
    evaluate_rules,
    explain_with_llm,
    load_excerpts,
    load_rules,
    retrieve,
)

ROOT = Path(__file__).resolve().parents[1]


def _corpus():
    return load_excerpts(ROOT / "data" / "regulations" / "excerpts.json")


def _rules():
    return load_rules(ROOT / "data" / "regulations" / "rules.json")


def test_retrieval_ranks_relevant_excerpt_first() -> None:
    corpus = _corpus()
    top = retrieve("roof ownership authorization for self-consumption solar", corpus, top_k=1)
    assert top[0][0]["id"] == "exc-001"


def test_retrieval_net_metering_query() -> None:
    corpus = _corpus()
    top = retrieve("net metering capacity threshold interconnection study", corpus, top_k=1)
    assert top[0][0]["id"] == "exc-002"


def test_golden_case_gets_clean_applicable_finding() -> None:
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set())
    findings = evaluate_rules(ctx, _rules(), _corpus())
    codes = {f.code for f in findings}
    assert "RULE-001" in codes
    assert "RULE-002" not in codes
    f = next(f for f in findings if f.code == "RULE-001")
    assert f.conclusion == "applicable"
    assert f.citations and f.citations[0].documentId == "doc-dnera-dg-rules-2025"


def test_unknown_ownership_triggers_review() -> None:
    ctx = build_context("self_consumption", "rented_unknown", gis_finding_codes=set())
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-002")
    assert f.conclusion == "requires_review"
    assert f.severity == "warning"
    assert f.citations


def test_protected_area_intersection_triggers_critical_review() -> None:
    ctx = build_context(
        "self_consumption", "owned", gis_finding_codes={"protected_area.intersects"}
    )
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-005")
    assert f.conclusion == "requires_review"
    assert f.severity == "critical"


def test_net_metering_over_threshold_is_not_applicable() -> None:
    ctx = build_context(
        "net_metering", "owned", gis_finding_codes=set(), recommended_capacity_kw=25_000
    )
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-003")
    assert f.conclusion == "not_applicable"


def test_net_metering_under_threshold_is_applicable_with_duration() -> None:
    ctx = build_context(
        "net_metering", "owned", gis_finding_codes=set(), recommended_capacity_kw=475
    )
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-004")
    assert f.conclusion == "applicable"
    assert f.estimatedDurationDays is not None
    assert f.estimatedDurationDays.basis == "published"


def test_every_finding_has_citation_or_rule_id() -> None:
    ctx = build_context("self_consumption", "unknown", gis_finding_codes={"protected_area.intersects"})
    findings = evaluate_rules(ctx, _rules(), _corpus())
    assert findings  # multiple rules should fire
    for f in findings:
        assert f.citations or f.ruleIds


def test_condition_dsl_rejects_unknown_operator() -> None:
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set())
    bad_rules = [
        {
            "ruleId": "BAD",
            "condition": {"field": "connectionModel", "op": "__import__", "value": "os"},
            "conclusion": "applicable",
            "severity": "info",
            "title_template": "x",
            "explanation_template": "x",
            "citationExcerptIds": [],
        }
    ]
    with pytest.raises(ValueError):
        evaluate_rules(ctx, bad_rules, _corpus())


@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="no GROQ_API_KEY set")
def test_llm_explanation_is_grounded_live() -> None:
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

    corpus = _corpus()
    rules = _rules()
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set())
    findings = evaluate_rules(ctx, rules, corpus)
    retrieved = retrieve("self-consumption rooftop solar ownership requirement", corpus, top_k=2)

    text = explain_with_llm(
        "Can this factory install a self-consumption rooftop solar system?",
        retrieved,
        findings,
        client,
    )
    assert text is not None and len(text) > 0
    # Must not invent a real-sounding authority not present in the provided excerpts.
    assert "EgyptERA" not in text
    assert "NREA" not in text
