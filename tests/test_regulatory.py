"""Regulatory: retrieval relevance, deterministic rules (real EgyptERA/law citations), LLM grounding."""

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


def test_retrieval_ranks_site_control_excerpt_first() -> None:
    corpus = _corpus()
    top = retrieve("roof lease right of use 25 years site control", corpus, top_k=1)
    assert top[0][0]["id"] == "exc-003"


def test_retrieval_net_metering_query() -> None:
    corpus = _corpus()
    top = retrieve("net metering capacity threshold local content", corpus, top_k=1)
    assert top[0][0]["id"] in ("exc-004", "exc-005")


def test_self_consumption_small_capacity_is_applicable() -> None:
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set(), recommended_capacity_kw=350)
    findings = evaluate_rules(ctx, _rules(), _corpus())
    codes = {f.code for f in findings}
    assert "RULE-002" in codes
    assert "RULE-003" not in codes
    assert "RULE-004" not in codes
    f = next(f for f in findings if f.code == "RULE-002")
    assert f.conclusion == "applicable"
    assert f.citations and f.citations[0].authority.startswith("Egyptian Electric Utility")


def test_self_consumption_mid_capacity_requires_review() -> None:
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set(), recommended_capacity_kw=5000)
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-003")
    assert f.conclusion == "requires_review"
    assert f.severity == "warning"


def test_self_consumption_over_30mw_is_not_applicable() -> None:
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set(), recommended_capacity_kw=35_000)
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-004")
    assert f.conclusion == "not_applicable"
    assert f.severity == "critical"


def test_ownership_missing_triggers_site_control_review() -> None:
    ctx = build_context("self_consumption", "rented_unknown", gis_finding_codes=set(), recommended_capacity_kw=350)
    findings = evaluate_rules(ctx, _rules(), _corpus())
    codes = {f.code for f in findings}
    f = next(f for f in findings if f.code == "RULE-001")
    assert f.conclusion == "requires_review"
    assert f.citations
    # capacity-tier rules require confirmed ownership; they must not also fire
    assert "RULE-002" not in codes and "RULE-003" not in codes


def test_net_metering_under_ceiling_is_applicable_with_duration() -> None:
    ctx = build_context("net_metering", "owned", gis_finding_codes=set(), recommended_capacity_kw=15_000)
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-005")
    assert f.conclusion == "applicable"
    assert f.estimatedDurationDays is not None
    assert f.estimatedDurationDays.basis == "published"


def test_net_metering_over_ceiling_is_not_applicable() -> None:
    ctx = build_context("net_metering", "owned", gis_finding_codes=set(), recommended_capacity_kw=25_000)
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-006")
    assert f.conclusion == "not_applicable"
    assert f.severity == "critical"


def test_protected_area_intersection_triggers_critical_review() -> None:
    ctx = build_context(
        "self_consumption", "owned", gis_finding_codes={"protected_area.intersects"}, recommended_capacity_kw=350
    )
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-007")
    assert f.conclusion == "requires_review"
    assert f.severity == "critical"
    assert "102" in f.citations[0].documentTitle  # Protected Areas Law No. 102/1983


def test_environmental_assessment_always_required_for_industrial() -> None:
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set(), recommended_capacity_kw=350)
    findings = evaluate_rules(ctx, _rules(), _corpus())
    f = next(f for f in findings if f.code == "RULE-008")
    assert f.conclusion == "requires_review"
    assert f.severity == "warning"
    assert f.estimatedDurationDays is not None


def test_no_recommended_capacity_abstains_from_capacity_tier_rules() -> None:
    # Without a capacity, capacity-band rules cannot be safely evaluated and must not fire.
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set())
    findings = evaluate_rules(ctx, _rules(), _corpus())
    codes = {f.code for f in findings}
    assert not ({"RULE-002", "RULE-003", "RULE-004"} & codes)
    assert "RULE-008" in codes  # environmental rule has no capacity dependency


def test_every_finding_has_citation_or_rule_id() -> None:
    ctx = build_context(
        "self_consumption", "unknown", gis_finding_codes={"protected_area.intersects"}, recommended_capacity_kw=350
    )
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
def test_llm_retrieval_ranks_relevant_excerpts_live() -> None:
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

    corpus = _corpus()
    top = retrieve(
        "roof lease right of use 25 years site control", corpus, top_k=1, client=client
    )
    assert top[0][0]["id"] == "exc-003"

    top = retrieve(
        "net metering capacity threshold local content", corpus, top_k=1, client=client
    )
    assert top[0][0]["id"] in ("exc-004", "exc-005")


def test_llm_retrieval_falls_back_to_tfidf_on_client_failure() -> None:
    class _BrokenClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("simulated API failure")

    corpus = _corpus()
    top = retrieve(
        "roof lease right of use 25 years site control", corpus, top_k=1, client=_BrokenClient()
    )
    assert top[0][0]["id"] == "exc-003"


@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), reason="no GROQ_API_KEY set")
def test_llm_explanation_is_grounded_live() -> None:
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")

    corpus = _corpus()
    rules = _rules()
    ctx = build_context("self_consumption", "owned", gis_finding_codes=set(), recommended_capacity_kw=350)
    findings = evaluate_rules(ctx, rules, corpus)
    retrieved = retrieve("self-consumption rooftop solar permit and licence requirement", corpus, top_k=2)

    text = explain_with_llm(
        "Can this factory install a self-consumption rooftop solar system at 350 kW?",
        retrieved,
        findings,
        client,
    )
    assert text is not None and len(text) > 0
    # Sanity: no leftover fictional placeholder authority from the old synthetic corpus.
    assert "DNERA" not in text
