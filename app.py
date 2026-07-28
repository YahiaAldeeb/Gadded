"""Gadded — thin Streamlit wrapper for the live pitch.

This is NOT the graded PoC (that's gadded.ipynb + src/gadded/). It is an optional,
thin demo shell over the exact same analytical modules, built for the live
presentation only (see AGENTS.md). It follows the parts of context/ui-context.md that
still apply to a non-web demo: the status system (icon + text + color, never color
alone), the metric strip, the six result tabs, chart labeling rules, the persistent
disclaimer, and the source/assumptions drawer.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

load_dotenv(ROOT / ".env")

from gadded.contracts import AssessmentInput, ResultVersions, load_assumptions
from gadded.feasibility import resolve_feasibility
from gadded.finance import build_scenarios
from gadded.gis import load_zones, screen_site
from gadded.load_ml import predict_load_ml, train_load_ml_model
from gadded.regulatory import build_context, evaluate_rules, load_excerpts, load_rules, retrieve
from gadded.optimization import optimize_capacity
from gadded.report import assemble_result, render_html
from gadded.risk import RiskInputs, run_monte_carlo
from gadded.weather import load_cached_weather

# --------------------------------------------------------------------------- #
# Theme — tokens from context/ui-context.md
# --------------------------------------------------------------------------- #

TOKENS = {
    "bg_base": "#F6F7F2", "bg_surface": "#FFFFFF", "bg_muted": "#EEF1E8",
    "text_primary": "#17211B", "text_secondary": "#526159", "text_muted": "#7A877F",
    "border": "#DCE2D9", "solar": "#E7A927", "solar_soft": "#FFF4D5",
    "energy": "#1E7A52", "energy_soft": "#E3F4EA", "technical": "#183B56",
    "ai": "#6255D9", "success": "#237A4B", "warning": "#B76A00",
    "critical": "#B93A3A", "unknown": "#667085",
}

STATUS_STYLE = {
    "likely_feasible": ("✓", "Likely feasible", TOKENS["success"], TOKENS["energy_soft"]),
    "feasible_with_conditions": ("⚠", "Feasible with conditions", TOKENS["warning"], TOKENS["solar_soft"]),
    "high_risk": ("✕", "High regulatory/site risk", TOKENS["critical"], "#FBE9E9"),
    "potentially_ineligible": ("✕", "Potentially ineligible (preliminary)", TOKENS["critical"], "#FBE9E9"),
    "insufficient_information": ("?", "Insufficient information", TOKENS["unknown"], TOKENS["bg_muted"]),
}

DISCLAIMER = (
    "This is a preliminary decision-support assessment. Verify regulatory, engineering, "
    "grid, vendor, and financing information with the responsible authorities and "
    "qualified professionals."
)


def inject_theme() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {TOKENS['bg_base']}; color: {TOKENS['text_primary']}; }}
        .gadded-disclaimer {{
            background: {TOKENS['solar_soft']}; border: 1px solid {TOKENS['solar']};
            border-radius: 12px; padding: 0.6rem 1rem; font-size: 0.85rem;
            color: {TOKENS['text_secondary']}; margin-bottom: 1rem;
        }}
        .gadded-card {{
            background: {TOKENS['bg_surface']}; border: 1px solid {TOKENS['border']};
            border-radius: 16px; padding: 0.9rem 0.5rem; text-align: center;
        }}
        .gadded-card .label {{ font-size: 0.75rem; color: {TOKENS['text_muted']}; }}
        .gadded-card .value {{
            font-size: 1.1rem; font-weight: 600; color: {TOKENS['text_primary']};
            word-break: keep-all; overflow-wrap: normal; white-space: normal;
        }}
        .gadded-status {{
            display: inline-flex; align-items: center; gap: 0.5rem;
            border-radius: 999px; padding: 0.5rem 1rem; font-weight: 600;
            border: 1px solid {TOKENS['border']};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fmt_short(value: float, unit: str) -> str:
    """Abbreviate a large figure so metric cards never break mid-number."""
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:.2f}M {unit}"
    if abs(value) >= 1_000:
        return f"{value/1_000:.0f}K {unit}"
    return f"{value:,.0f} {unit}"


def fmt_egp_short(value: float) -> str:
    return _fmt_short(value, "EGP")


def fmt_kwh_short(value: float) -> str:
    return _fmt_short(value, "kWh")


def metric_card(col, label: str, value: str) -> None:
    col.markdown(
        f'<div class="gadded-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> None:
    icon, label, color, bg = STATUS_STYLE.get(status, ("?", status, TOKENS["unknown"], TOKENS["bg_muted"]))
    st.markdown(
        f'<span class="gadded-status" style="color:{color};background:{bg};">'
        f'{icon} {label}</span>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Cached resources (loaded once per server process)
# --------------------------------------------------------------------------- #


@st.cache_resource(show_spinner="Loading assumptions...")
def get_assumptions():
    return load_assumptions(ROOT / "data" / "assumptions.json")


@st.cache_resource(show_spinner="Loading cached weather...")
def get_weather():
    return load_cached_weather(ROOT / "data" / "weather_10ramadan_cached.csv")


@st.cache_resource(show_spinner="Training load-profile ML model (KMeans + RandomForest)...")
def get_load_ml_bundle():
    return train_load_ml_model(seed=42, n_per_combo=15)


@st.cache_resource(show_spinner="Loading GIS layers...")
def get_zones():
    return load_zones(ROOT / "data" / "zones.geojson")


@st.cache_resource(show_spinner="Loading regulatory corpus and rules...")
def get_regulatory():
    corpus = load_excerpts(ROOT / "data" / "regulations" / "excerpts.json")
    rules = load_rules(ROOT / "data" / "regulations" / "rules.json")
    return corpus, rules


def get_groq_client():
    if not os.environ.get("GROQ_API_KEY"):
        return None
    from openai import OpenAI
    return OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1",
                  timeout=60.0, max_retries=1)


# --------------------------------------------------------------------------- #
# Scenario presets — same idea as the golden cases in implementation-plan.md
# --------------------------------------------------------------------------- #

GOLDEN_CASE = {
    "projectName": "10th of Ramadan Food Processing Rooftop Solar",
    "latitude": 30.3009, "longitude": 31.7411,
    "sector": "food_processing", "shiftPattern": "day_shift", "workingDaysPerWeek": 6,
    "monthly": [145000, 140000, 150000, 160000, 175000, 185000,
                190000, 188000, 172000, 162000, 150000, 146000],
    "roofArea": 3000.0, "ownership": "owned", "connectionModel": "self_consumption",
    "preference": "compare", "targetPayback": 6.0,
}

PRESETS = {
    "Golden case (default)": GOLDEN_CASE,
    "Ownership unknown -> insufficient information": {
        **GOLDEN_CASE, "ownership": "unknown",
        "projectName": "Ownership-Unverified Site",
    },
    "Site inside protected area -> high risk": {
        **GOLDEN_CASE, "latitude": 30.345, "longitude": 31.815,
        "projectName": "Protected-Area-Adjacent Site",
    },
    "Oversized roof -> optimizer picks below max": {
        **GOLDEN_CASE, "roofArea": 20000.0,
        "projectName": "Oversized Roof Scenario",
    },
}


def build_assessment_input(values: dict) -> AssessmentInput:
    data = {
        "projectId": "streamlit-demo",
        "projectName": values["projectName"],
        "projectType": "industrial_rooftop",
        "connectionModel": values["connectionModel"],
        "location": {
            "latitude": values["latitude"], "longitude": values["longitude"],
            "address": "10th of Ramadan City industrial zone, Egypt",
            "governorate": "Sharqia", "industrialZone": "10th of Ramadan City",
        },
        "factory": {
            "sector": values["sector"], "monthlyConsumptionKwh": values["monthly"],
            "workingDaysPerWeek": values["workingDaysPerWeek"], "shiftPattern": values["shiftPattern"],
        },
        "site": {"availableRoofAreaM2": values["roofArea"], "ownershipStatus": values["ownership"]},
        "finance": {"preference": values["preference"], "targetPaybackYears": values["targetPayback"]},
        "timeline": {},
    }
    return AssessmentInput.model_validate(data)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


def run_pipeline(ai: AssessmentInput, run_llm: bool):
    a = get_assumptions()
    weather = get_weather()
    bundle = get_load_ml_bundle()
    zones = get_zones()
    corpus, rules = get_regulatory()
    tol = a.number("reconciliation_tolerance_pct")

    load_profile = predict_load_ml(ai, weather.frame.index, bundle, tol)
    opt = optimize_capacity(ai, weather, load_profile.series["load_kw"], a)
    rec = opt.recommendation
    row = opt.table.loc[rec.recommendedCapacityKw]

    scenarios = build_scenarios(rec.recommendedCapacityKw, row["year1_savings_egp"], a, ai.finance.preference)

    risk_inputs = RiskInputs(
        capacity_kw=rec.recommendedCapacityKw, year1_pv_savings_egp=row["year1_savings_egp"],
        capex_egp=row["capex_egp"], opex_egp=rec.recommendedCapacityKw * a.number("opex_per_kw_year_egp"),
    )
    risk = run_monte_carlo(risk_inputs, a, target_payback_years=ai.finance.targetPaybackYears,
                            seed=int(a.number("monte_carlo_seed")), runs=int(a.number("monte_carlo_runs")))

    gis_findings = screen_site(ai.location.latitude, ai.location.longitude, zones)
    reg_ctx = build_context(ai.connectionModel, ai.site.ownershipStatus,
                             {f.code for f in gis_findings}, rec.recommendedCapacityKw)
    reg_findings = evaluate_rules(reg_ctx, rules, corpus)

    reg_explanation = None
    reg_error = None
    vendors, vendor_warnings = [], []
    if run_llm:
        client = get_groq_client()
        if client is None:
            reg_error = "GROQ_API_KEY not set — AI explanation and vendor search skipped."
        else:
            try:
                from gadded.regulatory import explain_with_llm
                question = "Can this factory install this rooftop solar system under the selected connection model?"
                retrieved = retrieve(question, corpus, top_k=2)
                reg_explanation = explain_with_llm(question, retrieved, reg_findings, client)
            except Exception as e:
                reg_error = f"Regulatory explanation unavailable this run ({type(e).__name__})."
            try:
                from gadded.vendors import discover_vendors
                vendors, vendor_warnings = discover_vendors(
                    ai.location.address or "Egypt", rec.recommendedCapacityKw,
                    ai.connectionModel, client, max_candidates=5,
                )
            except Exception as e:
                vendor_warnings = [f"vendor discovery unavailable this run ({type(e).__name__})"]

    material_warnings = [w for w in load_profile.result.warnings
                          if "exceeds tolerance" in w or "empty archetype shape" in w]
    feas = resolve_feasibility(reg_findings, gis_findings, ai.site.ownershipStatus, material_warnings)

    versions = ResultVersions(
        code="gadded-poc-0.1.0", assumptionSet=a.assumptionSet.id,
        loadModel=load_profile.result.modelVersion, pvModel="pvlib-pvwatts-0.1.0",
        regulatoryPrompt="reg-explain-0.1.0", vendorPrompt="vendor-discovery-0.1.0",
    )
    result = assemble_result(
        run_id=f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
        assessment_id=ai.projectId, status=feas.status, technical=rec, financial=scenarios,
        risk=risk, gis_findings=gis_findings, regulatory_findings=reg_findings, vendors=vendors,
        warnings=list(load_profile.result.warnings) + list(vendor_warnings), versions=versions,
    )
    return {
        "result": result, "feas": feas, "opt": opt, "load_profile": load_profile,
        "weather": weather, "assumptions": a, "reg_explanation": reg_explanation,
        "reg_error": reg_error, "vendor_warnings": vendor_warnings,
    }


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="Gadded", page_icon="☀", layout="wide")
inject_theme()

st.markdown(f'<div class="gadded-disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
st.title("Gadded")
st.caption("AI-driven solar pre-development decision support for Egyptian factories")

with st.sidebar:
    st.header("New assessment")
    preset_name = st.selectbox("Scenario preset", list(PRESETS.keys()))
    preset = PRESETS[preset_name]

    st.subheader("1. Project")
    project_name = st.text_input("Assessment name", preset["projectName"])
    connection_model = st.selectbox(
        "Connection model", ["self_consumption", "net_metering"],
        index=["self_consumption", "net_metering"].index(preset["connectionModel"]),
    )

    st.subheader("2. Location")
    latitude = st.number_input("Latitude", value=preset["latitude"], format="%.4f")
    longitude = st.number_input("Longitude", value=preset["longitude"], format="%.4f")
    st.caption("Weather is reused from the cached golden-site dataset for demo reliability.")

    st.subheader("3. Factory consumption")
    sector = st.selectbox("Sector", ["food_processing", "textiles"],
                           index=["food_processing", "textiles"].index(preset["sector"]))
    shift_pattern = st.selectbox("Shift pattern", ["day_shift", "two_shifts", "continuous"],
                                 index=["day_shift", "two_shifts", "continuous"].index(preset["shiftPattern"]))
    working_days = st.slider("Working days per week", 1, 7, preset["workingDaysPerWeek"])
    with st.expander("12 monthly consumption values (kWh)"):
        monthly = [
            st.number_input(f"Month {i+1}", value=float(v), key=f"m{i}", step=1000.0)
            for i, v in enumerate(preset["monthly"])
        ]

    st.subheader("4. Site and ownership")
    roof_area = st.number_input("Available roof area (m2)", value=preset["roofArea"], step=100.0)
    ownership = st.selectbox(
        "Ownership status", ["owned", "rented_authorized", "rented_unknown", "unknown"],
        index=["owned", "rented_authorized", "rented_unknown", "unknown"].index(preset["ownership"]),
    )

    st.subheader("5. Connection and finance")
    preference = st.selectbox("Finance preference", ["cash", "finance", "compare"],
                               index=["cash", "finance", "compare"].index(preset["preference"]))
    target_payback = st.number_input("Target payback (years)", value=preset["targetPayback"])

    run_llm = st.checkbox(
        "Run live AI stages (regulatory explanation + vendor search)", value=True,
        help="Calls the Groq API. Fails soft on rate limits/outages — technical and "
             "financial results are never affected.",
    )
    run_clicked = st.button("Run assessment", type="primary", use_container_width=True)

form_values = {
    "projectName": project_name, "latitude": latitude, "longitude": longitude,
    "sector": sector, "shiftPattern": shift_pattern, "workingDaysPerWeek": working_days,
    "monthly": monthly, "roofArea": roof_area, "ownership": ownership,
    "connectionModel": connection_model, "preference": preference, "targetPayback": target_payback,
}

if run_clicked:
    try:
        ai = build_assessment_input(form_values)
    except ValidationError as e:
        st.error("Invalid input — please fix the fields below and re-run.")
        for err in e.errors():
            st.write(f"- **{'.'.join(str(p) for p in err['loc'])}**: {err['msg']}")
        st.session_state.pop("run", None)
    else:
        with st.spinner("Running the full assessment pipeline..."):
            st.session_state["run"] = run_pipeline(ai, run_llm)
            st.session_state["ai"] = ai

if "run" not in st.session_state:
    st.info(
        "Configure an assessment in the sidebar (or pick a scenario preset) and click "
        "**Run assessment** to see the technical, financial, site, regulatory, and "
        "vendor result."
    )
    st.stop()

run = st.session_state["run"]
ai = st.session_state["ai"]
result = run["result"]
rec = result.technical

# --- summary header ---------------------------------------------------------
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader(ai.projectName)
    st.caption(f"{ai.location.address} | analysis date {datetime.now(timezone.utc).date().isoformat()}")
    status_badge(result.status)
with col2:
    html = render_html(result, ai.projectName, datetime.now(timezone.utc).isoformat())
    st.download_button("Download report (HTML)", data=html, file_name="gadded_report.html",
                        mime="text/html", use_container_width=True)

if result.status not in ("likely_feasible",):
    with st.expander("Why this status?", expanded=True):
        for r in run["feas"].reasons:
            st.write("-", r)

# --- metric strip ------------------------------------------------------------
m = st.columns(6)
metric_card(m[0], "Recommended capacity", f"{rec.recommendedCapacityKw:.0f} kW")
metric_card(m[1], "Annual generation", fmt_kwh_short(rec.annualGenerationKwh))
metric_card(m[2], "Self-consumption", f"{rec.selfConsumptionRatio*100:.1f}%")
year1_savings = next((s.yearOneSavingsEgp for s in result.financial if s.scenario == "cash"), None)
metric_card(m[3], "Annual savings (cash)", fmt_egp_short(year1_savings) if year1_savings else "n/a")
metric_card(m[4], "Median payback", f"{result.risk.paybackP50Years:.1f} yr" if result.risk.paybackP50Years else "n/a")
reg_duration = next((f.estimatedDurationDays for f in result.regulatoryFindings if f.estimatedDurationDays), None)
metric_card(m[5], "Approval-time range",
            f"{reg_duration.minimum}-{reg_duration.maximum} d" if reg_duration else "n/a")

with st.expander("Sources, assumptions, and versions"):
    st.write(f"**Assumption set:** `{result.versions.assumptionSet}`")
    st.write(f"**Load model:** `{result.versions.loadModel}`")
    st.write(f"**PV model:** `{result.versions.pvModel}`")
    st.write(f"**Weather source:** {run['weather'].source_name}, retrieved {run['weather'].retrieved_at}")
    st.caption("DEMO/SYNTHETIC-classified assumptions are placeholders and must be replaced "
               "with sourced figures before any real-world use.")

tab_tech, tab_fin, tab_site, tab_reg, tab_vendor, tab_report = st.tabs(
    ["Technical", "Financial", "Site", "Regulatory", "Vendors", "Report"]
)

# --- Technical ---------------------------------------------------------------
with tab_tech:
    best = run["opt"].best_match
    fig, ax = plt.subplots(figsize=(9, 3))
    sample = best.hourly.loc["2023-06-05":"2023-06-11"]
    ax.plot(sample.index, sample["load_kw"], label="Factory load (kW)")
    ax.plot(sample.index, sample["pv_kw"], label=f"PV output ({rec.recommendedCapacityKw:.0f} kW)")
    ax.set_xlabel("Time"); ax.set_ylabel("kW"); ax.legend()
    st.pyplot(fig)
    st.caption(f"Sample week: load vs. PV at the recommended {rec.recommendedCapacityKw:.0f} kW capacity.")

    fig2, ax2 = plt.subplots(figsize=(9, 3))
    table = run["opt"].table
    ax2.plot(table["capacity_kw"], table["npv_egp"], marker="o", markersize=3)
    ax2.axvline(rec.recommendedCapacityKw, color=TOKENS["energy"], linestyle="--", label="Recommended")
    ax2.axvline(rec.physicalMaximumKw, color=TOKENS["critical"], linestyle=":", label="Roof physical max")
    ax2.set_xlabel("Candidate capacity (kW)"); ax2.set_ylabel("Project NPV (EGP)"); ax2.legend()
    st.pyplot(fig2)
    st.caption(f"NPV across {len(rec.evaluatedCapacitiesKw)} candidate sizes. Binding constraint: "
               f"{', '.join(rec.bindingConstraints)}.")

    st.write(f"Self-sufficiency: **{rec.selfSufficiencyRatio*100:.1f}%** | "
             f"Imported: **{rec.annualImportedKwh:,.0f} kWh** | Exported: **{rec.annualExportedKwh:,.0f} kWh** | "
             f"Roof area used: **{rec.roofAreaRequiredM2:,.0f} m2** of {ai.site.availableRoofAreaM2:,.0f} m2 available")

    if run["load_profile"].result.confidence == "low":
        st.warning("Load-profile ML confidence was low this run; fell back to the deterministic "
                   "archetype baseline (see Warnings on the Report tab).")

# --- Financial ----------------------------------------------------------------
with tab_fin:
    for s in result.financial:
        with st.container(border=True):
            st.write(f"**{s.scenario.title()}**")
            c = st.columns(4)
            c[0].metric("Capex", f"{s.capexEgp:,.0f} EGP")
            c[1].metric("NPV", f"{s.npvEgp:,.0f} EGP")
            c[2].metric("IRR", f"{s.irrPct:.1f}%" if s.irrPct is not None else "n/a")
            c[3].metric("Simple payback", f"{s.simplePaybackYears:.1f} yr" if s.simplePaybackYears else "not recovered")
            st.caption("Nominal cash flows; includes O&M, tariff escalation, degradation. "
                       "Excludes tax, general inflation adjustment, replacement, residual value.")

    fig3, ax3 = plt.subplots(figsize=(9, 3))
    ax3.bar(["P10", "P50 (median)", "P90"],
            [result.risk.npvP10Egp, result.risk.npvP50Egp, result.risk.npvP90Egp],
            color=[TOKENS["critical"], TOKENS["solar"], TOKENS["success"]])
    ax3.set_ylabel("NPV (EGP)")
    st.pyplot(fig3)
    st.caption(f"Monte Carlo NPV range ({result.risk.runCount} runs, seed {result.risk.seed}). "
               f"Payback P10/P50/P90: {result.risk.paybackP10Years:.1f} / "
               f"{result.risk.paybackP50Years:.1f} / {result.risk.paybackP90Years:.1f} years.")
    if result.risk.probabilityTargetPaybackPct is not None:
        st.write(f"Probability of meeting the {ai.finance.targetPaybackYears}-year target payback: "
                 f"**{result.risk.probabilityTargetPaybackPct:.1f}%**")

    fig4, ax4 = plt.subplots(figsize=(9, 2.5))
    drivers = result.risk.topSensitivityDrivers
    ax4.barh([d.variable for d in drivers][::-1], [d.influence * 100 for d in drivers][::-1],
             color=TOKENS["technical"])
    ax4.set_xlabel("Relative influence on NPV (%)")
    st.pyplot(fig4)
    st.caption("Sensitivity drivers, one-at-a-time perturbation.")

# --- Site ----------------------------------------------------------------------
with tab_site:
    if not result.gisFindings:
        st.info("No GIS findings for this run.")
    for f in result.gisFindings:
        icon = {"info": "✓", "warning": "⚠", "critical": "✕", "unknown": "?"}[f.severity]
        color = {"info": TOKENS["success"], "warning": TOKENS["warning"],
                 "critical": TOKENS["critical"], "unknown": TOKENS["unknown"]}[f.severity]
        st.markdown(f'<span style="color:{color};font-weight:600;">{icon} {f.title}</span>',
                    unsafe_allow_html=True)
        details = f"Category: {f.category}"
        if f.value is not None:
            details += f" | Value: {f.value}{(' ' + f.unit) if f.unit else ''}"
        details += f" | Source: {f.sourceName}"
        st.caption(details)
        if f.limitations:
            st.caption("Limitations: " + " ".join(x for x in f.limitations if x))

# --- Regulatory ------------------------------------------------------------------
with tab_reg:
    if not result.regulatoryFindings:
        st.info("No regulatory findings for this run.")
    for f in result.regulatoryFindings:
        color = {"info": TOKENS["success"], "warning": TOKENS["warning"], "critical": TOKENS["critical"]}[f.severity]
        st.markdown(f'<span style="color:{color};font-weight:600;">{f.title}</span>', unsafe_allow_html=True)
        st.write(f.explanation)
        st.caption(f"Conclusion: {f.conclusion} | Confidence: {f.confidence} | "
                   f"Verification required: {'yes' if f.verificationRequired else 'no'}")
        if f.requiredDocuments:
            st.write("Required documents:", ", ".join(f.requiredDocuments))
        for c in f.citations:
            with st.expander(f"Citation: {c.documentTitle}"):
                st.write(f"**Authority:** {c.authority}")
                st.write(f"**Effective date:** {c.effectiveDate or 'n/a'}")
                st.write(f"> {c.excerpt}")
        st.divider()

    if run["reg_explanation"]:
        st.write("**AI explanation (grounded in the excerpts/rules above):**")
        st.write(run["reg_explanation"])
    elif run["reg_error"]:
        st.warning(run["reg_error"])

# --- Vendors --------------------------------------------------------------------
with tab_vendor:
    if not result.vendors:
        if run["vendor_warnings"]:
            st.warning("Vendor search unavailable this run: " + "; ".join(run["vendor_warnings"]))
        else:
            st.info("Vendor discovery was not run for this assessment.")
    else:
        st.caption("Leads to independently verify — not an endorsed or ranked list.")
        for v in result.vendors:
            with st.container(border=True):
                st.write(f"**{v.name}** — [{v.websiteUrl}]({v.websiteUrl})")
                st.write(v.fitExplanation)
                st.caption(f"Verification status: {v.verificationStatus}")
                for e in v.evidence:
                    st.caption(f"Evidence: [{e.title}]({e.url})")

# --- Report -----------------------------------------------------------------------
with tab_report:
    st.components.v1.html(html, height=600, scrolling=True)
    if result.warnings:
        st.write("**Warnings**")
        for w in result.warnings:
            st.caption("- " + w)

st.markdown(f'<div class="gadded-disclaimer">{DISCLAIMER}</div>', unsafe_allow_html=True)
