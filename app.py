"""Gadded — Dashboard for AI Empower Egypt 2026.
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
# Design System & Tokens
# --------------------------------------------------------------------------- #

TOKENS = {
    "bg_base": "#F8FAFC", "bg_surface": "#FFFFFF", "bg_muted": "#F1F5F9",
    "text_primary": "#0F172A", "text_secondary": "#475569", "text_muted": "#64748B",
    "border": "#E2E8F0", "solar": "#D97706", "solar_soft": "#FEF3C7",
    "energy": "#059669", "energy_soft": "#D1FAE5", "technical": "#1E293B",
    "ai": "#6255D9", "success": "#166534", "warning": "#92400E",
    "critical": "#991B1B", "unknown": "#475569",
}

STATUS_STYLE = {
    "likely_feasible": ("✓", "Likely Feasible", TOKENS["success"], TOKENS["energy_soft"], "border-emerald-300 text-emerald-800 bg-emerald-50"),
    "feasible_with_conditions": ("⚠", "Feasible with Conditions", TOKENS["warning"], TOKENS["solar_soft"], "border-amber-300 text-amber-800 bg-amber-50"),
    "high_risk": ("✕", "High Regulatory / Site Risk", TOKENS["critical"], "#FEE2E2", "border-rose-300 text-rose-800 bg-rose-50"),
    "potentially_ineligible": ("✕", "Potentially Ineligible (Preliminary)", TOKENS["critical"], "#FEE2E2", "border-rose-300 text-rose-800 bg-rose-50"),
    "insufficient_information": ("?", "Insufficient Information", TOKENS["unknown"], TOKENS["bg_muted"], "border-slate-300 text-slate-700 bg-slate-100"),
}

DISCLAIMER = (
    "Preliminary decision-support assessment for industrial solar pre-development. "
    "Verify regulatory, engineering, grid connection, and financing requirements with responsible authorities."
)


def inject_tailwind_theme() -> None:
    st.markdown(
        f"""
        <!-- Tailwind CSS CDN -->
        <script src="https://cdn.tailwindcss.com"></script>
        <!-- Google Fonts -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Cairo:wght@600;700;800&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">

        <style>
        /* Global Reset & Typography */
        html, body, [class*="css"], .stApp {{
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            background-color: #F8FAFC !important;
            color: #0F172A !important;
        }}

        code, pre, .font-mono {{
            font-family: 'Geist Mono', monospace !important;
        }}

        /* Responsive Container */
        .main .block-container {{
            max-width: 1280px !important;
            padding-top: 1rem !important;
            padding-bottom: 3rem !important;
        }}

        /* STREAMLIT CONTROLS OVERRIDES */
        label, div[data-testid="stMarkdownContainer"] p, .stMarkdown label, .stSlider label {{
            color: #0F172A !important;
            font-weight: 700 !important;
            font-size: 0.9rem !important;
        }}

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        div[data-baseweb="base-input"],
        input, select, textarea,
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div {{
            background-color: #FFFFFF !important;
            color: #0F172A !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 12px !important;
            font-size: 0.925rem !important;
            font-weight: 600 !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
        }}

        div[data-baseweb="select"] span {{
            color: #0F172A !important;
            font-weight: 700 !important;
        }}

        .stNumberInput button {{
            background-color: #F1F5F9 !important;
            color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }}

        /* STREAMLIT EXPANDER OVERRIDE (Fix dark summary bar & dark contrast) */
        .stExpander {{
            background-color: #FFFFFF !important;
            border: 1.5px solid #E2E8F0 !important;
            border-radius: 16px !important;
            box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.04) !important;
            margin-bottom: 1.25rem !important;
            overflow: hidden !important;
        }}

        .stExpander > details > summary {{
            background-color: #F8FAFC !important;
            color: #0F172A !important;
            border-bottom: 1.5px solid #E2E8F0 !important;
            font-weight: 800 !important;
            font-size: 1rem !important;
            padding: 0.85rem 1.25rem !important;
            border-radius: 16px 16px 0 0 !important;
        }}

        .stExpander > details > summary:hover {{
            background-color: #F1F5F9 !important;
        }}

        .stExpander > details > summary p,
        .stExpander > details > summary span,
        .stExpander > details > summary div {{
            color: #0F172A !important;
            font-weight: 800 !important;
            font-size: 1rem !important;
        }}

        /* CLEAN MINIMAL HERO BANNER WITH HIGH CONTRAST TEXT */
        .gadded-hero-minimal {{
            background: linear-gradient(135deg, #064E3B 0%, #0F172A 100%);
            color: #FFFFFF;
            border-radius: 20px;
            padding: 2rem 2.25rem;
            box-shadow: 0 12px 28px -6px rgba(6, 78, 59, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }}

        /* SECTION BANNER STYLING */
        .gadded-section-banner {{
            display: flex;
            align-items: center;
            gap: 0.85rem;
            background: #FFFFFF;
            border: 1.5px solid #E2E8F0;
            border-left: 5px solid #059669;
            border-radius: 14px;
            padding: 0.85rem 1.25rem;
            margin-top: 1.25rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        }}

        /* PRESET CARD STYLING */
        .gadded-preset-card {{
            background: #FFFFFF;
            border: 1.5px solid #E2E8F0;
            border-radius: 16px;
            padding: 1.2rem;
            box-shadow: 0 2px 8px -2px rgba(0, 0, 0, 0.04);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .gadded-preset-card:hover {{
            box-shadow: 0 12px 20px -4px rgba(0, 0, 0, 0.08);
            border-color: #059669;
            transform: translateY(-2px);
        }}
        .gadded-preset-card.active {{
            border-color: #059669;
            box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.2), 0 6px 14px -2px rgba(5, 150, 105, 0.15);
        }}

        .gadded-glass-card {{
            background: #FFFFFF;
            border: 1.5px solid #E2E8F0;
            border-radius: 16px;
            padding: 1.25rem;
            box-shadow: 0 2px 8px -2px rgba(0, 0, 0, 0.04);
            transition: all 0.2s ease;
        }}
        .gadded-glass-card:hover {{
            box-shadow: 0 8px 16px -2px rgba(0, 0, 0, 0.06);
            border-color: #059669;
        }}

        /* KPI METRIC CARDS */
        .gadded-kpi-card {{
            background: #FFFFFF;
            border: 1.5px solid #E2E8F0;
            border-radius: 16px;
            padding: 1.2rem 0.85rem;
            text-align: center;
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
            height: 100%;
            transition: all 0.2s ease;
        }}
        .gadded-kpi-card:hover {{
            transform: translateY(-2px);
            border-color: #059669;
            box-shadow: 0 8px 16px -2px rgba(5, 150, 105, 0.12);
        }}
        .gadded-kpi-card .kpi-icon-bg {{
            width: 38px;
            height: 38px;
            border-radius: 10px;
            background-color: #F1F5F9;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.45rem;
        }}
        .gadded-kpi-card .kpi-label {{
            font-size: 0.75rem;
            font-weight: 700;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.25rem;
        }}
        .gadded-kpi-card .kpi-value {{
            font-size: 1.35rem;
            font-weight: 800;
            color: #0F172A;
            word-break: keep-all;
        }}

        /* Status Badge */
        .gadded-status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            border-radius: 9999px;
            padding: 0.55rem 1.25rem;
            font-weight: 800;
            font-size: 0.95rem;
            border: 1.5px solid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}

        /* Primary Action Buttons */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 800 !important;
            font-size: 1rem !important;
            padding: 0.75rem 1.75rem !important;
            box-shadow: 0 4px 14px rgba(5, 150, 105, 0.3) !important;
            transition: all 0.2s ease-in-out !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(5, 150, 105, 0.4) !important;
        }}

        /* Preset Action Buttons */
        .stButton > button:not([kind="primary"]) {{
            background-color: #059669 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            font-size: 0.85rem !important;
            box-shadow: 0 2px 6px rgba(5, 150, 105, 0.2) !important;
            transition: all 0.2s ease !important;
        }}
        .stButton > button:not([kind="primary"]):hover {{
            background-color: #047857 !important;
            box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3) !important;
            transform: translateY(-1px) !important;
        }}

        /* DOWNLOAD REPORT BUTTON STYLING */
        div.stDownloadButton > button {{
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            font-weight: 800 !important;
            font-size: 0.9rem !important;
            padding: 0.7rem 1.35rem !important;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.25) !important;
            transition: all 0.2s ease !important;
        }}
        div.stDownloadButton > button:hover {{
            background: linear-gradient(135deg, #1E293B 0%, #334155 100%) !important;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.35) !important;
            transform: translateY(-1px) !important;
        }}

        /* Streamlit Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.5rem !important;
            background-color: #E2E8F0 !important;
            padding: 0.45rem !important;
            border-radius: 14px !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 10px !important;
            padding: 0.65rem 1.35rem !important;
            font-weight: 700 !important;
            color: #475569 !important;
            background-color: transparent !important;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #FFFFFF !important;
            color: #059669 !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fmt_short(value: float, unit: str) -> str:
    """Abbreviate large numbers for metric cards."""
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:.2f}M {unit}"
    if abs(value) >= 1_000:
        return f"{value/1_000:.0f}K {unit}"
    return f"{value:,.0f} {unit}"


def fmt_egp_short(value: float) -> str:
    return _fmt_short(value, "EGP")


def fmt_kwh_short(value: float) -> str:
    return _fmt_short(value, "kWh")


def section_banner(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="gadded-section-banner">
            <span class="text-2xl">{icon}</span>
            <div>
                <div class="font-extrabold text-[15px] text-slate-900 leading-snug">{title}</div>
                <div class="text-[12px] text-slate-600 font-medium">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(col, label: str, value: str, icon: str = "⚡") -> None:
    col.markdown(
        f"""
        <div class="gadded-kpi-card">
            <div class="kpi-icon-bg">
                <span class="text-lg">{icon}</span>
            </div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> None:
    icon, label, color, bg, css_classes = STATUS_STYLE.get(
        status, ("?", status, TOKENS["unknown"], TOKENS["bg_muted"], "border-slate-300 text-slate-700 bg-slate-100")
    )
    st.markdown(
        f"""
        <div class="gadded-status-pill {css_classes}">
            <span>{icon}</span>
            <span>{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Cached Resources
# --------------------------------------------------------------------------- #

@st.cache_resource(show_spinner="Loading decision parameters...")
def get_assumptions():
    return load_assumptions(ROOT / "data" / "assumptions.json")


@st.cache_resource(show_spinner="Loading solar irradiance weather dataset...")
def get_weather():
    return load_cached_weather(ROOT / "data" / "weather_10ramadan_cached.csv")


@st.cache_resource(show_spinner="Initializing load-profile ML models...")
def get_load_ml_bundle():
    return train_load_ml_model(seed=42, n_per_combo=15)


@st.cache_resource(show_spinner="Loading GIS spatial layers...")
def get_zones():
    return load_zones(ROOT / "data" / "zones.geojson")


@st.cache_resource(show_spinner="Loading Egyptian solar regulations...")
def get_regulatory():
    corpus = load_excerpts(ROOT / "data" / "regulations" / "excerpts.json")
    rules = load_rules(ROOT / "data" / "regulations" / "rules.json")
    return corpus, rules


def get_groq_client():
    if not os.environ.get("GROQ_API_KEY"):
        return None
    from openai import OpenAI
    return OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
        timeout=60.0,
        max_retries=1,
    )


# --------------------------------------------------------------------------- #
# Presets
# --------------------------------------------------------------------------- #

GOLDEN_CASE = {
    "projectName": "10th of Ramadan Food Factory Rooftop Solar",
    "latitude": 30.3203, "longitude": 31.7466,
    "sector": "food_processing", "shiftPattern": "day_shift", "workingDaysPerWeek": 6,
    "monthly": [145000, 140000, 150000, 160000, 175000, 185000,
                190000, 188000, 172000, 162000, 150000, 146000],
    "roofArea": 3000.0, "ownership": "owned", "connectionModel": "self_consumption",
    "preference": "compare", "targetPayback": 6.0,
}

PRESETS = {
    "Golden Case (10th Ramadan Factory)": {
        "icon": "🏭",
        "data": GOLDEN_CASE,
        "badge": "Likely Feasible",
        "badge_color": "bg-emerald-100 text-emerald-800 border-emerald-300",
        "desc": "Real factory in Sharqia, 3,000 m² roof, 6-day shift, self-consumption model.",
    },
    "Ownership Unknown (Fallback check)": {
        "icon": "❓",
        "data": {**GOLDEN_CASE, "ownership": "unknown", "projectName": "Ownership-Unverified Factory Site"},
        "badge": "Insufficient Info",
        "badge_color": "bg-slate-100 text-slate-700 border-slate-300",
        "desc": "Site ownership status missing -> triggers deterministic unknown verification status.",
    },
    "Protected Area (GIS Boundary Check)": {
        "icon": "⚠️",
        "data": {**GOLDEN_CASE, "latitude": 30.345, "longitude": 31.815, "projectName": "Protected-Area Adjacent Site"},
        "badge": "High Risk",
        "badge_color": "bg-rose-100 text-rose-800 border-rose-300",
        "desc": "Location near protected area boundary -> flags critical environmental risk.",
    },
    "Oversized Roof (NPV Optimization)": {
        "icon": "📐",
        "data": {**GOLDEN_CASE, "roofArea": 20000.0, "projectName": "Large Industrial Park Site"},
        "badge": "Economic Optimum",
        "badge_color": "bg-amber-100 text-amber-800 border-amber-300",
        "desc": "20,000 m² roof area -> NPV optimizer picks optimal sizing below maximum physical roof limit.",
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
            "address": "10th of Ramadan City Industrial Zone, Sharqia, Egypt",
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
# Pipeline Execution
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
    risk = run_monte_carlo(
        risk_inputs, a, target_payback_years=ai.finance.targetPaybackYears,
        seed=int(a.number("monte_carlo_seed")), runs=int(a.number("monte_carlo_runs"))
    )

    gis_findings = screen_site(ai.location.latitude, ai.location.longitude, zones)
    reg_ctx = build_context(
        ai.connectionModel, ai.site.ownershipStatus,
        {f.code for f in gis_findings}, rec.recommendedCapacityKw
    )
    reg_findings = evaluate_rules(reg_ctx, rules, corpus)

    reg_explanation = None
    reg_error = None
    vendors, vendor_warnings = [], []
    if run_llm:
        client = get_groq_client()
        if client is None:
            reg_error = "GROQ_API_KEY not set in environment — AI legal explanation and vendor web search skipped."
        else:
            try:
                from gadded.regulatory import explain_with_llm
                question = "Can this factory install this rooftop solar system under the selected connection model?"
                retrieved = retrieve(question, corpus, top_k=2, client=client)
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

    material_warnings = [
        w for w in load_profile.result.warnings
        if "exceeds tolerance" in w or "empty archetype shape" in w
    ]
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
# Main Application Shell
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="Gadded — AI Empower Egypt 2026",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_tailwind_theme()

# --- Top Minimal Header Banner with High Contrast Text ---
st.markdown(
    f"""
    <div class="gadded-hero-minimal mb-5">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
                <h1 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Gadded — Dashboard for AI Empower Egypt 2026</h1>
                <p class="text-emerald-300 font-extrabold text-base sm:text-lg mt-1 tracking-wide" style="font-family: 'Cairo', sans-serif;">
                    جدد — منصة دعم قرارات الطاقة الشمسية للمصانع المصرية (تمكين مصر 2026)
                </p>
            </div>
            <div class="bg-white/20 backdrop-blur px-3.5 py-1.5 rounded-xl border border-white/30 text-xs text-white font-extrabold whitespace-nowrap self-start sm:self-center">
                ☀️ Official PoC Engine
            </div>
        </div>
    </div>

    <div class="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-950 flex items-start gap-2.5 mb-5 shadow-sm">
        <span class="text-base leading-none">ℹ️</span>
        <div><strong>Disclaimer:</strong> {DISCLAIMER}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- SECTION 1: SCENARIO SELECTION ---
section_banner("🎯", "SECTION 1 — Select Scenario Preset or Build Custom Assessment", "Choose a pre-configured Egyptian industrial scenario or customize your parameters below:")

preset_cols = st.columns(4)
selected_preset_key = st.session_state.get("active_preset", "Golden Case (10th Ramadan Factory)")

for i, (name, details) in enumerate(PRESETS.items()):
    col = preset_cols[i]
    is_active = (selected_preset_key == name)
    active_class = "active" if is_active else ""
    
    with col:
        st.markdown(
            f"""
            <div class="gadded-preset-card {active_class} mb-2 flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="text-xl">{details.get('icon', '☀️')}</span>
                        <span class="px-2.5 py-0.5 text-[10px] font-extrabold rounded border {details['badge_color']}">
                            {details['badge']}
                        </span>
                    </div>
                    <div class="font-extrabold text-xs text-slate-900 mb-1">{name}</div>
                    <div class="text-[11px] text-slate-600 font-medium leading-relaxed mb-3">{details['desc']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"Load Preset", key=f"btn_preset_{i}", use_container_width=True):
            st.session_state["active_preset"] = name
            st.rerun()

preset = PRESETS[st.session_state.get("active_preset", "Golden Case (10th Ramadan Factory)")]["data"]

# --- SECTION 2: INPUT WIZARD ---
section_banner("⚙️", "SECTION 2 — Configure Factory & Site Parameters", "Adjust project location, energy consumption, site constraints, and financial targets:")

with st.expander("📝 View & Edit Factory Assessment Parameters", expanded=True):
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("#### 🏢 Project & Location Details")
        project_name = st.text_input("Assessment Name", value=preset["projectName"], help="Descriptive name for this factory assessment.")
        connection_model = st.selectbox(
            "Regulatory Connection Model", ["self_consumption", "net_metering"],
            index=["self_consumption", "net_metering"].index(preset["connectionModel"]),
            help="Self-consumption (ex-Circular 3/2023) vs Net-Metering (Circular 4/2026).",
        )
        c_lat, c_lon = st.columns(2)
        latitude = c_lat.number_input("Latitude", value=preset["latitude"], format="%.4f", help="Site latitude in Egypt.")
        longitude = c_lon.number_input("Longitude", value=preset["longitude"], format="%.4f", help="Site longitude in Egypt.")
        
        st.markdown("#### 🏭 Site & Ownership Constraints")
        roof_area = st.number_input("Available Roof Area (m²)", value=preset["roofArea"], step=100.0, help="Total structurally sound rooftop area available for PV installation.")
        ownership = st.selectbox(
            "Land / Roof Ownership Status", ["owned", "rented_authorized", "rented_unknown", "unknown"],
            index=["owned", "rented_authorized", "rented_unknown", "unknown"].index(preset["ownership"]),
            help="Required under EgyptERA Circular 6/2023 for self-consumption grid clearance.",
        )

    with col_b:
        st.markdown("#### ⚡ Factory Energy Consumption Profile")
        sector = st.selectbox(
            "Industrial Sector", ["food_processing", "textiles"],
            index=["food_processing", "textiles"].index(preset["sector"]),
            help="Determines the baseline hourly demand shape.",
        )
        shift_pattern = st.selectbox(
            "Shift Pattern", ["day_shift", "two_shifts", "continuous"],
            index=["day_shift", "two_shifts", "continuous"].index(preset["shiftPattern"]),
            help="Operating schedule of factory machinery.",
        )
        working_days = st.slider("Working Days / Week", 1, 7, preset["workingDaysPerWeek"])
        
        with st.expander("📊 View / Edit 12 Monthly Consumption Values (kWh)", expanded=False):
            monthly_cols = st.columns(3)
            monthly = []
            for idx, val in enumerate(preset["monthly"]):
                m_col = monthly_cols[idx % 3]
                m_val = m_col.number_input(f"Month {idx+1}", value=float(val), step=5000.0, key=f"m_val_{idx}")
                monthly.append(m_val)

        st.markdown("#### 💰 Financial Assumptions & Targets")
        f_col1, f_col2 = st.columns(2)
        preference = f_col1.selectbox(
            "Finance Preference", ["cash", "finance", "compare"],
            index=["cash", "finance", "compare"].index(preset["preference"])
        )
        target_payback = f_col2.number_input("Target Payback (Years)", value=preset["targetPayback"], help="Maximum acceptable simple payback period in years.")

    st.divider()
    cta_col1, cta_col2 = st.columns([3, 1])
    with cta_col1:
        run_llm = st.checkbox(
            "Enable Groq AI Stages (Grounded Legal Explanation + Live Vendor Web Search)",
            value=True,
            help="Calls Groq LLM endpoint. Fails soft if API key is missing or rate limited.",
        )
    with cta_col2:
        run_clicked = st.button("🚀 Run Assessment", type="primary", use_container_width=True)

form_values = {
    "projectName": project_name, "latitude": latitude, "longitude": longitude,
    "sector": sector, "shiftPattern": shift_pattern, "workingDaysPerWeek": working_days,
    "monthly": monthly, "roofArea": roof_area, "ownership": ownership,
    "connectionModel": connection_model, "preference": preference, "targetPayback": target_payback,
}

# Automatically run golden assessment on initial load
if "run" not in st.session_state or run_clicked:
    try:
        ai = build_assessment_input(form_values)
    except ValidationError as e:
        st.error("Validation Error — please review input parameters.")
        for err in e.errors():
            st.write(f"- **{'.'.join(str(p) for p in err['loc'])}**: {err['msg']}")
    else:
        with st.spinner("Simulating solar physics, ML load profiles, financial risk, and regulatory rules..."):
            st.session_state["run"] = run_pipeline(ai, run_llm)
            st.session_state["ai"] = ai

run = st.session_state["run"]
ai = st.session_state["ai"]
result = run["result"]
rec = result.technical

# --- SECTION 3: EXECUTIVE DECISION DASHBOARD ---
section_banner("📊", "SECTION 3 — Executive Decision Dashboard & Feasibility Status", "Deterministic feasibility status, core financial metrics, and executive KPIs:")

hdr_col1, hdr_col2 = st.columns([3, 1])
with hdr_col1:
    st.subheader(ai.projectName)
    st.caption(f"📍 {ai.location.address} | Coordinates: ({ai.location.latitude:.4f}, {ai.location.longitude:.4f})")
    status_badge(result.status)

with hdr_col2:
    html_report = render_html(result, ai.projectName, datetime.now(timezone.utc).isoformat())
    st.download_button(
        "📥 Download Report (HTML)",
        data=html_report,
        file_name=f"Gadded_Assessment_{result.assessmentId}.html",
        mime="text/html",
        use_container_width=True,
    )

if result.status != "likely_feasible":
    with st.expander("⚠️ Decision Rationale & Status Rationale Details", expanded=True):
        for reason in run["feas"].reasons:
            st.markdown(f"- **{reason}**")

# Metric Strip (6 Executive KPIs)
st.markdown("<div class='my-4'></div>", unsafe_allow_html=True)
m_cols = st.columns(6)
metric_card(m_cols[0], "Rec. Capacity", f"{rec.recommendedCapacityKw:.0f} kW", "⚡")
metric_card(m_cols[1], "Annual Gen.", fmt_kwh_short(rec.annualGenerationKwh), "☀️")
metric_card(m_cols[2], "Self-Consumpt.", f"{rec.selfConsumptionRatio*100:.1f}%", "🔄")

cash_savings = next((s.yearOneSavingsEgp for s in result.financial if s.scenario == "cash"), None)
metric_card(m_cols[3], "Year 1 Savings", fmt_egp_short(cash_savings) if cash_savings else "n/a", "💵")
metric_card(m_cols[4], "Median Payback", f"{result.risk.paybackP50Years:.1f} yr" if result.risk.paybackP50Years else "n/a", "📈")

reg_dur = next((f.estimatedDurationDays for f in result.regulatoryFindings if f.estimatedDurationDays), None)
metric_card(m_cols[5], "Approval Time", f"{reg_dur.minimum}-{reg_dur.maximum} d" if reg_dur else "📋", "⏱️")

st.markdown("<div class='mb-6'></div>", unsafe_allow_html=True)

# --- SECTION 4: DETAILED ANALYTICAL BREAKDOWN ---
section_banner("🔍", "SECTION 4 — Detailed Technical, Financial, GIS & Legal Breakdown", "Explore specialized analytical modules, physics simulations, and legal compliance:")

tab_tech, tab_fin, tab_site, tab_reg, tab_vendor, tab_report = st.tabs(
    ["⚡ Technical & PV", "💰 Financial Risk", "🗺️ Site & GIS", "📜 Regulatory", "🏢 Vendors", "📄 Full Report"]
)

# --- Tab 1: Technical & PV Physics ---
with tab_tech:
    st.markdown("#### Technical Sizing & Energy Yield Simulation")
    best = run["opt"].best_match

    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        fig, ax = plt.subplots(figsize=(8, 3.2))
        sample = best.hourly.loc["2023-06-05":"2023-06-11"]
        ax.plot(sample.index, sample["load_kw"], label="Factory Load (kW)", color=TOKENS["technical"], linewidth=1.5)
        ax.plot(sample.index, sample["pv_kw"], label=f"PV Output ({rec.recommendedCapacityKw:.0f} kW)", color=TOKENS["solar"], linewidth=1.5)
        ax.set_facecolor("#F8FAFC")
        fig.patch.set_facecolor("#FFFFFF")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.set_ylabel("kW")
        ax.legend(frameon=True, facecolor="#FFFFFF")
        st.pyplot(fig)
        st.caption("Sample 7-day hourly load vs solar PV production curve.")

    with col_t2:
        fig2, ax2 = plt.subplots(figsize=(6, 3.2))
        table = run["opt"].table
        ax2.plot(table["capacity_kw"], table["npv_egp"] / 1e6, marker="o", color=TOKENS["energy"], linewidth=1.5)
        ax2.axvline(rec.recommendedCapacityKw, color=TOKENS["solar"], linestyle="--", label="Recommended")
        ax2.axvline(rec.physicalMaximumKw, color=TOKENS["critical"], linestyle=":", label="Physical Max")
        ax2.set_facecolor("#F8FAFC")
        fig2.patch.set_facecolor("#FFFFFF")
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.set_xlabel("Candidate Capacity (kW)")
        ax2.set_ylabel("Project NPV (Million EGP)")
        ax2.legend(frameon=True, facecolor="#FFFFFF")
        st.pyplot(fig2)
        st.caption(f"NPV Grid Search curve across candidate system capacities.")

    st.info(
        f"**Self-Sufficiency Ratio:** {rec.selfSufficiencyRatio*100:.1f}% | "
        f"**Annual Imported Grid Energy:** {rec.annualImportedKwh:,.0f} kWh | "
        f"**Roof Utilization:** {rec.roofAreaRequiredM2:,.0f} m² used of {ai.site.availableRoofAreaM2:,.0f} m² available "
        f"({rec.roofAreaRequiredM2/ai.site.availableRoofAreaM2*100:.1f}%)."
    )

# --- Tab 2: Financial Risk & Monte Carlo ---
with tab_fin:
    st.markdown("#### Financial Analysis & Monte Carlo Risk Simulation")
    
    fin_cols = st.columns(len(result.financial))
    for idx, s in enumerate(result.financial):
        with fin_cols[idx]:
            st.markdown(
                f"""
                <div class="gadded-glass-card">
                    <div class="font-extrabold text-slate-900 text-lg mb-2">{s.scenario.title()} Scenario</div>
                    <div class="text-xs text-slate-500 font-semibold mb-1">Capital Expenditure</div>
                    <div class="text-xl font-extrabold text-emerald-700 mb-3">{s.capexEgp:,.0f} EGP</div>
                    <div class="space-y-1.5 text-xs">
                        <div class="flex justify-between border-b border-slate-100 pb-1"><span>NPV:</span> <span class="font-bold text-slate-900">{s.npvEgp:,.0f} EGP</span></div>
                        <div class="flex justify-between border-b border-slate-100 pb-1"><span>IRR:</span> <span class="font-bold text-slate-900">{f'{s.irrPct:.1f}%' if s.irrPct else 'n/a'}</span></div>
                        <div class="flex justify-between"><span>Simple Payback:</span> <span class="font-bold text-slate-900">{f'{s.simplePaybackYears:.1f} yrs' if s.simplePaybackYears else 'n/a'}</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div class='my-4'></div>", unsafe_allow_html=True)
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        fig3, ax3 = plt.subplots(figsize=(6, 3))
        ax3.bar(
            ["P10 (Conservative)", "P50 (Median)", "P90 (Optimistic)"],
            [result.risk.npvP10Egp / 1e6, result.risk.npvP50Egp / 1e6, result.risk.npvP90Egp / 1e6],
            color=[TOKENS["critical"], TOKENS["solar"], TOKENS["success"]],
        )
        ax3.set_ylabel("NPV (Million EGP)")
        ax3.set_facecolor("#F8FAFC")
        fig3.patch.set_facecolor("#FFFFFF")
        st.pyplot(fig3)
        st.caption(f"Monte Carlo NPV uncertainty range ({result.risk.runCount} simulations).")

    with f_col2:
        fig4, ax4 = plt.subplots(figsize=(6, 3))
        drivers = result.risk.topSensitivityDrivers
        ax4.barh([d.variable for d in drivers][::-1], [d.influence * 100 for d in drivers][::-1], color=TOKENS["technical"])
        ax4.set_xlabel("Relative NPV Sensitivity (%)")
        ax4.set_facecolor("#F8FAFC")
        fig4.patch.set_facecolor("#FFFFFF")
        st.pyplot(fig4)
        st.caption("One-at-a-time sensitivity ranking on project NPV.")

# --- Tab 3: Site & GIS Spatial Screening ---
with tab_site:
    st.markdown("#### GIS Spatial & Environmental Screening")
    if not result.gisFindings:
        st.info("No spatial constraints recorded for this site.")
    for f in result.gisFindings:
        badge_style = {
            "info": ("✓ Clear", "bg-emerald-100 text-emerald-800 border-emerald-300"),
            "warning": ("⚠ Condition", "bg-amber-100 text-amber-800 border-amber-300"),
            "critical": ("✕ Blocker", "bg-rose-100 text-rose-800 border-rose-300"),
            "unknown": ("? Unknown", "bg-slate-100 text-slate-700 border-slate-300"),
        }.get(f.severity, ("?", "bg-slate-100 text-slate-700 border-slate-300"))
        
        border_left = {
            "info": "border-l-4 border-l-emerald-500",
            "warning": "border-l-4 border-l-amber-500",
            "critical": "border-l-4 border-l-rose-500",
            "unknown": "border-l-4 border-l-slate-400",
        }.get(f.severity, "")

        st.markdown(
            f"""
            <div class="gadded-glass-card {border_left} mb-3">
                <div class="flex items-center justify-between mb-1">
                    <div class="font-extrabold text-slate-900">{f.title}</div>
                    <span class="px-2.5 py-0.5 rounded text-xs font-bold border {badge_style[1]}">{badge_style[0]}</span>
                </div>
                <div class="text-xs text-slate-600 mb-2">Category: <strong>{f.category}</strong> | Source: <strong>{f.sourceName}</strong></div>
                {f'<div class="text-xs font-bold text-slate-900 mb-1">Value: {f.value} {f.unit or ""}</div>' if f.value is not None else ''}
                {'<div class="text-[11px] text-slate-500 italic">Limitations: ' + ' '.join(f.limitations) + '</div>' if f.limitations else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

# --- Tab 4: Regulatory Compliance & AI ---
with tab_reg:
    st.markdown("#### Egyptian Solar Legal Framework (Circular 3/2023 & EEAA)")
    if not result.regulatoryFindings:
        st.info("No regulatory findings evaluated.")
    for f in result.regulatoryFindings:
        st.markdown(
            f"""
            <div class="gadded-glass-card mb-4 border-l-4 border-l-emerald-600">
                <div class="font-extrabold text-slate-900 text-base mb-1">{f.title}</div>
                <p class="text-xs text-slate-700 font-medium mb-2">{f.explanation}</p>
                <div class="text-xs text-slate-500 mb-2">
                    Conclusion: <strong>{f.conclusion}</strong> | Confidence: <strong>{f.confidence}</strong> | Verification Required: <strong>{'Yes' if f.verificationRequired else 'No'}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if f.citations:
            for c in f.citations:
                with st.expander(f"📜 Authority Citation: {c.documentTitle} ({c.authority})"):
                    st.write(f"**Effective Date:** {c.effectiveDate or 'n/a'}")
                    st.write(f"> *{c.excerpt}*")

    if run["reg_explanation"]:
        st.markdown("##### 🤖 Grounded Groq AI Legal Analysis")
        st.info(run["reg_explanation"])
    elif run["reg_error"]:
        st.warning(run["reg_error"])

# --- Tab 5: Vendor Discovery ---
with tab_vendor:
    st.markdown("#### Local EPC Vendor Discovery")
    if not result.vendors:
        if run["vendor_warnings"]:
            st.warning("Vendor discovery note: " + "; ".join(run["vendor_warnings"]))
        else:
            st.info("Vendor discovery was not executed for this run.")
    else:
        st.caption("Screened vendor candidates with verified web evidence links.")
        for v in result.vendors:
            st.markdown(
                f"""
                <div class="gadded-glass-card mb-3">
                    <div class="flex items-center justify-between mb-2">
                        <div class="font-extrabold text-slate-900 text-base">{v.name}</div>
                        <a href="{v.websiteUrl}" target="_blank" class="text-xs font-bold text-emerald-700 hover:underline">Visit Website ↗</a>
                    </div>
                    <p class="text-xs text-slate-700 mb-2 font-medium">{v.fitExplanation}</p>
                    <div class="text-[11px] text-slate-500">Verification Status: <strong>{v.verificationStatus}</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# --- Tab 6: Full Report & System Metadata ---
with tab_report:
    st.markdown("#### Rendered Assessment Report & Metadata")
    st.components.v1.html(html_report, height=600, scrolling=True)
    
    with st.expander("🔧 System Model Versions & Assumption Set"):
        st.write(f"**Assumption Set ID:** `{result.versions.assumptionSet}`")
        st.write(f"**Load Model Version:** `{result.versions.loadModel}`")
        st.write(f"**PV Model:** `{result.versions.pvModel}`")
        st.write(f"**Weather Dataset:** {run['weather'].source_name} (Retrieved {run['weather'].retrieved_at})")

# Persistent footer disclaimer
st.markdown(f"<div class='text-center text-xs text-slate-400 mt-8 mb-4'>{DISCLAIMER}</div>", unsafe_allow_html=True)
