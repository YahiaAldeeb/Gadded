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
import streamlit.components.v1 as components
from dotenv import load_dotenv
from pydantic import ValidationError

load_dotenv(ROOT / ".env")

from gadded.contracts import AssessmentInput, ResultVersions, load_assumptions
from gadded.feasibility import resolve_feasibility
from gadded.finance import build_scenarios, finance_scenario, savings_stream
from gadded.financing import discover_financing_options
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
    "text_primary": "#0B1220", "text_secondary": "#475569", "text_muted": "#64748B",
    "border": "#E2E8F0", "solar": "#D97706", "solar_soft": "#FEF3C7",
    "energy": "#059669", "energy_soft": "#D1FAE5", "technical": "#0B1220",
    "ai": "#6255D9", "success": "#059669", "warning": "#B45309",
    "critical": "#BE123C", "unknown": "#475569",
    # Sequential ramp (single hue, light -> dark) for magnitude-only series,
    # e.g. Monte Carlo P10/P50/P90 — same measure, not distinct categories.
    "seq_light": "#A7E8CB", "seq_mid": "#10B981", "seq_dark": "#065F46",
    # Neutral reference/boundary line color (kept out of the rose "critical" slot
    # so a physical/roof limit line never reads as a regulatory blocker).
    "boundary": "#94A3B8",
}

STATUS_STYLE = {
    "likely_feasible": ("✓", "Likely Feasible", TOKENS["success"], TOKENS["energy_soft"], "border-emerald-300 text-emerald-800 bg-emerald-50"),
    "feasible_with_conditions": ("⚠", "Feasible with Conditions", TOKENS["warning"], TOKENS["solar_soft"], "border-amber-300 text-amber-800 bg-amber-50"),
    "high_risk": ("✕", "High Regulatory / Site Risk", TOKENS["critical"], "#FFE4E9", "border-rose-300 text-rose-800 bg-rose-50"),
    "potentially_ineligible": ("✕", "Potentially Ineligible (Preliminary)", TOKENS["critical"], "#FFE4E9", "border-rose-300 text-rose-800 bg-rose-50"),
    "insufficient_information": ("?", "Insufficient Information", TOKENS["unknown"], "#F1F5F9", "border-slate-300 text-slate-700 bg-slate-100"),
}

DISCLAIMER = (
    "Preliminary decision-support assessment for industrial solar pre-development. "
    "Verify regulatory, engineering, grid connection, and financing requirements with responsible authorities."
)


def inject_tailwind_theme() -> None:
    # st.markdown(unsafe_allow_html=True) never executes injected <script> tags — that's a
    # hard browser rule for HTML inserted via innerHTML, not a Streamlit limitation. The
    # Tailwind Play CDN tag was silently dead: no Tailwind utility class anywhere in this file
    # was ever actually being applied. components.html() renders in a real iframe, where
    # scripts DO execute; since the iframe is same-origin, it can reach into
    # window.parent.document and attach a real <script> element there via createElement (not
    # innerHTML), which the browser does execute. Tailwind's CDN script then JIT-scans the
    # actual Streamlit page — including on reruns, via its own MutationObserver.
    components.html(
        """
        <script>
        if (!window.parent.document.getElementById('gadded-tailwind-cdn')) {
            const s = window.parent.document.createElement('script');
            s.id = 'gadded-tailwind-cdn';
            s.src = 'https://cdn.tailwindcss.com';
            window.parent.document.head.appendChild(s);
        }
        </script>
        """,
        height=0,
    )
    st.markdown(
        f"""
        <!-- Google Fonts -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Cairo:wght@600;700;800&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">

        <style>
        :root {{
            --ink: #0B1220;
            --ink-soft: #334155;
            --muted: #64748B;
            --muted-soft: #94A3B8;
            --line: #E2E8F0;
            --line-soft: #EDF1F5;
            --surface: #FFFFFF;
            --surface-alt: #FBFCFE;
            --canvas: #F6F8FA;
            --brand: #059669;
            --brand-dark: #047857;
            --brand-deep: #065F46;
            --brand-light: #10B981;
            --brand-soft: #ECFDF5;
            --brand-ring: rgba(5, 150, 105, 0.16);
            --solar: #D97706;
            --solar-dark: #B45309;
            --solar-soft: #FFFBEB;
            --violet: #6255D9;
            --violet-dark: #4C3FC4;
            --violet-soft: #F1EFFE;
            --rose: #E11D48;
            --rose-dark: #BE123C;
            --rose-soft: #FFF1F2;
            --radius-sm: 10px;
            --radius-md: 14px;
            --radius-lg: 18px;
            --radius-xl: 24px;
            --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05);
            --shadow-md: 0 6px 16px -4px rgba(15, 23, 42, 0.08);
            --shadow-lg: 0 16px 36px -10px rgba(15, 23, 42, 0.14);
            --shadow-brand: 0 10px 24px -8px rgba(5, 150, 105, 0.35);
        }}

        /* Global Reset & Typography */
        html, body, [class*="css"], .stApp {{
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            background-color: var(--canvas) !important;
            color: var(--ink) !important;
        }}

        .stApp {{
            background-image:
                radial-gradient(circle at 8% 0%, rgba(5, 150, 105, 0.05), transparent 32%),
                radial-gradient(circle at 92% 6%, rgba(217, 119, 6, 0.045), transparent 30%) !important;
            background-attachment: fixed !important;
        }}

        code, pre, .font-mono {{
            font-family: 'Geist Mono', monospace !important;
        }}

        .tabnum {{ font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1; }}

        ::selection {{ background: var(--brand-ring); color: var(--ink); }}

        /* Responsive Container */
        .main .block-container {{
            max-width: 1180px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 4rem !important;
        }}

        @media (max-width: 640px) {{
            .main .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
        }}

        /* STREAMLIT CONTROLS OVERRIDES */
        label, div[data-testid="stMarkdownContainer"] p, .stMarkdown label, .stSlider label {{
            color: var(--ink) !important;
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
            background-color: var(--surface) !important;
            color: var(--ink) !important;
            border: 1.5px solid #CBD5E1 !important;
            border-radius: 10px !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            transition: border-color 0.15s ease !important;
        }}

        div[data-baseweb="select"]:focus-within > div,
        div[data-baseweb="base-input"]:focus-within {{
            border-color: var(--brand) !important;
        }}

        div[data-baseweb="select"] span {{
            color: var(--ink) !important;
            font-weight: 700 !important;
        }}

        .stNumberInput button {{
            background-color: #F1F5F9 !important;
            color: var(--ink) !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
        }}

        hr {{ border-color: var(--line) !important; }}

        /* STREAMLIT EXPANDER OVERRIDE */
        .stExpander {{
            background-color: var(--surface) !important;
            border: 1.5px solid var(--line) !important;
            border-radius: 14px !important;
            box-shadow: var(--shadow-sm) !important;
            margin-bottom: 1rem !important;
            overflow: hidden !important;
        }}

        .stExpander > details > summary {{
            background-color: var(--surface) !important;
            color: var(--ink) !important;
            font-weight: 800 !important;
            font-size: 0.95rem !important;
            padding: 0.8rem 1.15rem !important;
        }}

        .stExpander > details[open] > summary {{
            border-bottom: 1.5px solid var(--line-soft) !important;
        }}

        .stExpander > details > summary:hover {{
            background-color: #FAFBFC !important;
        }}

        .stExpander > details > summary p,
        .stExpander > details > summary span,
        .stExpander > details > summary div {{
            color: var(--ink) !important;
            font-weight: 800 !important;
            font-size: 0.95rem !important;
        }}

        /* ---------- HERO ---------- */
        /* Higher-specificity override: the global stMarkdownContainer p rule above forces
           dark --ink text on every <p>, which would make the hero's light-on-dark copy
           unreadable. */
        div[data-testid="stMarkdownContainer"] .gadded-hero p {{
            color: rgba(226, 232, 240, 0.92) !important;
            font-weight: 500 !important;
            font-size: inherit !important;
        }}
        div[data-testid="stMarkdownContainer"] .gadded-hero p.gadded-hero-arabic {{
            color: #6EE7B7 !important;
            font-weight: 800 !important;
        }}
        .gadded-hero {{
            position: relative;
            background: radial-gradient(circle at 12% 15%, rgba(16, 185, 129, 0.38), transparent 42%),
                        radial-gradient(circle at 88% -4%, rgba(217, 119, 6, 0.24), transparent 38%),
                        linear-gradient(160deg, #04241C 0%, #0A1A16 38%, #0B1220 78%, #0D1526 100%);
            color: #FFFFFF;
            border-radius: var(--radius-xl);
            padding: 2.5rem 2.6rem 2rem;
            box-shadow: var(--shadow-lg);
            overflow: hidden;
        }}
        .gadded-hero::after {{
            content: "";
            position: absolute; inset: 0;
            background-image: radial-gradient(rgba(255,255,255,0.09) 1px, transparent 1px);
            background-size: 22px 22px;
            mask-image: linear-gradient(180deg, rgba(0,0,0,0.5), transparent 75%);
            pointer-events: none;
        }}
        .gadded-hero-badge {{
            background: rgba(255,255,255,0.10);
            backdrop-filter: blur(6px);
            border: 1px solid rgba(255,255,255,0.22);
        }}
        .gadded-hero-badge .pulse-dot {{
            width: 7px; height: 7px; border-radius: 9999px;
            background: #34D399;
            box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.6);
            animation: gadded-pulse 2.2s ease-out infinite;
        }}
        @keyframes gadded-pulse {{
            0%   {{ box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.55); }}
            70%  {{ box-shadow: 0 0 0 7px rgba(52, 211, 153, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }}
        }}
        .gadded-hero-meter {{
            margin-top: 1.75rem;
            height: 4px;
            border-radius: 9999px;
            background: linear-gradient(90deg, #34D399 0%, #A7F3D0 28%, #FCD34D 55%, #D97706 78%, rgba(217,119,6,0.15) 100%);
            opacity: 0.85;
        }}
        .gadded-hero-stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.75rem;
            margin-top: 1.1rem;
        }}
        .gadded-hero-stat-label {{
            font-size: 0.66rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: rgba(255,255,255,0.45);
            margin-bottom: 0.2rem;
        }}
        .gadded-hero-stat-value {{
            font-size: 0.92rem;
            font-weight: 700;
            color: rgba(255,255,255,0.92);
        }}

        /* ---------- EYEBROW SECTION HEADERS ---------- */
        .gadded-eyebrow-row {{
            display: flex;
            align-items: center;
            gap: 0.7rem;
            margin-top: 2.75rem;
            margin-bottom: 0.4rem;
        }}
        .gadded-eyebrow-num {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-family: 'Geist Mono', monospace;
            font-size: 0.72rem;
            font-weight: 700;
            color: var(--surface);
            background: linear-gradient(145deg, var(--ink) 0%, #1E293B 100%);
            border-radius: 9999px;
            width: 24px;
            height: 24px;
            letter-spacing: 0;
            flex: none;
        }}
        .gadded-eyebrow-line {{
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, var(--line) 0%, transparent 100%);
        }}
        .gadded-eyebrow-label {{
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--brand-dark);
            background: var(--brand-soft);
            padding: 0.2rem 0.55rem;
            border-radius: 9999px;
            white-space: nowrap;
        }}
        .gadded-section-title {{
            font-size: 1.45rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.015em;
            margin-bottom: 0.2rem;
        }}
        .gadded-section-sub {{
            font-size: 0.86rem;
            color: var(--muted);
            font-weight: 500;
            margin-bottom: 1.25rem;
            max-width: 62ch;
        }}

        /* ---------- CARDS ---------- */
        .gadded-preset-card {{
            position: relative;
            background: var(--surface);
            border: 1.5px solid var(--line);
            border-radius: 16px;
            padding: 1.2rem;
            box-shadow: var(--shadow-sm);
            transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .gadded-preset-card:hover {{
            box-shadow: var(--shadow-md);
            border-color: #A7D8C4;
            transform: translateY(-3px);
        }}
        .gadded-preset-card.active {{
            border-color: var(--brand);
            box-shadow: 0 0 0 3px rgba(5, 150, 105, 0.14), var(--shadow-md);
        }}
        .gadded-preset-check {{
            position: absolute;
            top: -9px; right: -9px;
            width: 24px; height: 24px;
            border-radius: 9999px;
            background: var(--brand);
            color: #fff;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.7rem; font-weight: 900;
            box-shadow: var(--shadow-md);
            border: 2px solid var(--canvas);
        }}
        .gadded-preset-icon {{
            width: 34px; height: 34px;
            border-radius: 10px;
            display: inline-flex; align-items: center; justify-content: center;
            font-size: 1.05rem;
            background: var(--canvas);
            border: 1px solid var(--line-soft);
        }}

        .gadded-glass-card {{
            background: var(--surface);
            border: 1.5px solid var(--line);
            border-radius: var(--radius-md);
            padding: 1.35rem 1.4rem;
            box-shadow: var(--shadow-sm);
            transition: all 0.18s ease;
            height: 100%;
        }}
        .gadded-glass-card:hover {{
            box-shadow: var(--shadow-md);
            border-color: #CBD5E1;
            transform: translateY(-2px);
        }}
        .gadded-glass-card.accent-brand {{ border-top: 3px solid var(--brand); }}
        .gadded-glass-card.accent-ink {{ border-top: 3px solid var(--ink); }}
        .gadded-scenario-row {{
            display: flex; justify-content: space-between; align-items: baseline;
            padding: 0.42rem 0; border-bottom: 1px dashed var(--line-soft);
            font-size: 0.78rem; color: var(--ink-soft);
        }}
        .gadded-scenario-row:last-child {{ border-bottom: none; }}
        .gadded-scenario-row .val {{
            font-weight: 800; color: var(--ink); font-family: 'Geist Mono', monospace;
            font-variant-numeric: tabular-nums;
        }}

        /* Unified finding/list card (GIS, Regulatory, Vendor, Financing evidence) */
        .gadded-finding-card {{
            background: var(--surface);
            border: 1.5px solid var(--line);
            border-radius: var(--radius-md);
            padding: 1.1rem 1.3rem;
            box-shadow: var(--shadow-sm);
            display: flex;
            gap: 0.95rem;
            align-items: flex-start;
            transition: all 0.15s ease;
        }}
        .gadded-finding-card:hover {{
            border-color: #CBD5E1;
            box-shadow: var(--shadow-md);
        }}
        .gadded-finding-icon {{
            flex: none;
            width: 36px; height: 36px;
            border-radius: 11px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1rem;
            font-weight: 800;
        }}

        /* ---------- KPI METRIC CARDS ---------- */
        .gadded-kpi-card {{
            position: relative;
            background: var(--surface);
            border: 1.5px solid var(--line);
            border-radius: var(--radius-md);
            padding: 1.2rem 1.15rem;
            box-shadow: var(--shadow-sm);
            height: 100%;
            transition: all 0.18s ease;
            overflow: hidden;
        }}
        .gadded-kpi-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            border-color: #CBD5E1;
        }}
        .gadded-kpi-card .kpi-icon-bg {{
            width: 38px;
            height: 38px;
            border-radius: 11px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.7rem;
            font-size: 1.05rem;
        }}
        .kpi-icon-brand {{ background: var(--brand-soft); }}
        .kpi-icon-solar {{ background: var(--solar-soft); }}
        .kpi-icon-violet {{ background: var(--violet-soft); }}
        .kpi-icon-slate {{ background: #F1F5F9; }}
        .gadded-kpi-card .kpi-label {{
            font-size: 0.7rem;
            font-weight: 700;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.32rem;
        }}
        .gadded-kpi-card .kpi-value {{
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--ink);
            word-break: keep-all;
            letter-spacing: -0.015em;
            line-height: 1.15;
        }}

        /* ---------- VERDICT PANEL (status + headline KPIs — the money shot) ---------- */
        div[data-testid="stVerticalBlockBorderWrapper"].st-key-verdict_panel,
        .st-key-verdict_panel > div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: linear-gradient(180deg, var(--surface) 0%, var(--surface-alt) 100%) !important;
            border: 1.5px solid var(--line) !important;
            border-radius: var(--radius-xl) !important;
            box-shadow: var(--shadow-lg) !important;
            padding: 0.4rem 0.5rem !important;
            position: relative;
            overflow: hidden;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"].st-key-verdict_panel::before,
        .st-key-verdict_panel > div[data-testid="stVerticalBlockBorderWrapper"]::before {{
            content: "";
            position: absolute; top: 0; left: 0; right: 0; height: 4px;
            background: linear-gradient(90deg, var(--brand) 0%, var(--brand-light) 45%, var(--solar) 100%);
        }}
        .gadded-project-title {{
            font-size: 1.3rem;
            font-weight: 800;
            color: var(--ink);
            letter-spacing: -0.01em;
            margin-bottom: 0.15rem;
        }}
        .gadded-project-meta {{
            font-size: 0.8rem;
            color: var(--muted);
            font-weight: 600;
            margin-bottom: 0.75rem;
        }}
        .gadded-verdict-divider {{
            height: 1px;
            background: var(--line-soft);
            margin: 1.1rem 0 1.15rem;
        }}
        .gadded-verdict-footnote {{
            font-size: 0.76rem;
            color: var(--muted);
            font-weight: 500;
            margin-top: 0.6rem;
        }}

        /* Status Badge */
        .gadded-status-pill {{
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            border-radius: 9999px;
            padding: 0.48rem 1.05rem;
            font-weight: 800;
            font-size: 0.85rem;
            border: 1.5px solid;
        }}
        .gadded-status-icon {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 20px; height: 20px;
            border-radius: 9999px;
            font-size: 0.68rem;
            font-weight: 900;
            background: rgba(255,255,255,0.65);
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
            box-shadow: var(--shadow-brand) !important;
            transition: all 0.18s ease-in-out !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 14px 28px -8px rgba(5, 150, 105, 0.45) !important;
        }}

        /* Preset Action Buttons */
        .stButton > button:not([kind="primary"]) {{
            background-color: var(--ink) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 9px !important;
            font-weight: 700 !important;
            font-size: 0.82rem !important;
            box-shadow: var(--shadow-sm) !important;
            transition: all 0.18s ease !important;
        }}
        .stButton > button:not([kind="primary"]):hover {{
            background-color: var(--brand-dark) !important;
            box-shadow: var(--shadow-md) !important;
            transform: translateY(-1px) !important;
        }}

        /* DOWNLOAD REPORT BUTTON STYLING */
        div.stDownloadButton > button {{
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%) !important;
            color: #FFFFFF !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            font-weight: 800 !important;
            font-size: 0.88rem !important;
            padding: 0.7rem 1.35rem !important;
            box-shadow: var(--shadow-md) !important;
            transition: all 0.18s ease !important;
        }}
        div.stDownloadButton > button:hover {{
            background: linear-gradient(135deg, #1E293B 0%, #334155 100%) !important;
            box-shadow: var(--shadow-lg) !important;
            transform: translateY(-1px) !important;
        }}

        /* Button labels render as a <p> inside stMarkdownContainer, which the global
           stMarkdownContainer-p rule above forces to dark --ink — invisible on these dark
           button backgrounds. Override with higher selector specificity. */
        .stButton div[data-testid="stMarkdownContainer"] p,
        div.stDownloadButton div[data-testid="stMarkdownContainer"] p {{
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: inherit !important;
        }}

        /* Streamlit Tabs */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0.3rem !important;
            background-color: #EAEEF2 !important;
            padding: 0.4rem !important;
            border-radius: var(--radius-md) !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 10px !important;
            padding: 0.6rem 1.25rem !important;
            font-weight: 700 !important;
            font-size: 0.87rem !important;
            color: var(--ink-soft) !important;
            background-color: transparent !important;
            transition: all 0.15s ease !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{
            color: var(--brand-dark) !important;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: var(--surface) !important;
            color: var(--brand-dark) !important;
            box-shadow: var(--shadow-sm) !important;
        }}
        .stTabs [data-baseweb="tab-highlight"] {{ background-color: transparent !important; }}
        .stTabs [data-baseweb="tab-border"] {{ display: none !important; }}

        /* Info / warning / error callouts */
        div[data-testid="stAlert"] {{
            border-radius: var(--radius-md) !important;
            border: 1.5px solid var(--line) !important;
            box-shadow: var(--shadow-sm) !important;
        }}

        /* Footer */
        .gadded-footer {{
            display: flex; align-items: center; justify-content: center; gap: 0.5rem;
            color: var(--muted); font-size: 0.78rem; font-weight: 500;
            padding-top: 1.75rem; margin-top: 2rem;
            border-top: 1px solid var(--line);
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


def lifetime_savings_egp(scenario, assumptions) -> float:
    """Undiscounted total net savings over the full analysis period for one scenario.

    Plain-language "total money back" headline number. Reuses the exact
    `savings_stream` cash-flow function the scenario itself was built from, so it is
    always internally consistent with the scenario's own NPV/payback (just not
    discounted — clearly labeled as such wherever it is shown).
    """
    n = int(assumptions.number("analysis_period_years"))
    esc = assumptions.number("tariff_escalation_pct") / 100.0
    deg = assumptions.number("degradation_pct_year") / 100.0
    year1_gross = scenario.yearOneSavingsEgp + scenario.annualOpexEgp
    return sum(savings_stream(year1_gross, scenario.annualOpexEgp, n, esc, deg))


def section_banner(num: str, icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="gadded-eyebrow-row">
            <span class="gadded-eyebrow-num">{num}</span>
            <span class="gadded-eyebrow-label">{icon} &nbsp;STEP</span>
            <span class="gadded-eyebrow-line"></span>
        </div>
        <div class="gadded-section-title">{title}</div>
        <div class="gadded-section-sub">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(col, label: str, value: str, icon: str = "⚡", variant: str = "slate") -> None:
    col.markdown(
        f"""
        <div class="gadded-kpi-card">
            <div class="kpi-icon-bg kpi-icon-{variant}">
                <span class="text-lg">{icon}</span>
            </div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value tabnum">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def finding_card(
    icon: str, icon_bg: str, title: str, badge_label: str, badge_class: str,
    meta_html: str = "", body_html: str = "",
) -> str:
    """Unified list-item card markup for GIS findings, regulatory findings, and vendors."""
    meta_block = f'<div class="text-xs text-slate-500 mb-2 font-semibold">{meta_html}</div>' if meta_html else ""
    return f"""
        <div class="gadded-finding-card mb-3">
            <div class="gadded-finding-icon" style="background:{icon_bg}">{icon}</div>
            <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-2 mb-1">
                    <div class="font-extrabold text-slate-900 text-[15px]">{title}</div>
                    <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold border whitespace-nowrap {badge_class}">{badge_label}</span>
                </div>{meta_block}{body_html}
            </div>
        </div>
        """


def style_chart(fig, axes) -> None:
    """Consistent flat, modern styling applied to every matplotlib chart in the app.

    Palette and mark language follow the dataviz skill: hairline recessive
    gridlines on one axis only, no top/right/left spines, ink titles, muted
    axis text, and a lightly bordered legend that never floats free.
    """
    fig.patch.set_facecolor("#FFFFFF")
    ax_list = axes if isinstance(axes, (list, tuple)) or hasattr(axes, "__iter__") else [axes]
    for ax in ax_list:
        ax.set_facecolor("#FFFFFF")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color(TOKENS["border"])
        ax.spines["bottom"].set_linewidth(1)
        ax.tick_params(colors=TOKENS["text_muted"], labelsize=9.5, length=0)
        ax.grid(True, axis="y", linestyle="-", linewidth=1, alpha=0.6, color=TOKENS["border"])
        ax.set_axisbelow(True)
        ax.title.set_color(TOKENS["text_primary"])
        ax.title.set_fontweight("bold")
        ax.title.set_fontsize(12)
        ax.title.set_ha("left")
        ax.title.set_position((0.0, 1.03))
        ax.xaxis.label.set_color(TOKENS["text_secondary"])
        ax.xaxis.label.set_fontweight("medium")
        ax.yaxis.label.set_color(TOKENS["text_secondary"])
        ax.yaxis.label.set_fontweight("medium")
        legend = ax.get_legend()
        if legend is not None:
            frame = legend.get_frame()
            frame.set_edgecolor(TOKENS["border"])
            frame.set_linewidth(1)
            frame.set_facecolor("#FFFFFF")
            frame.set_alpha(0.96)
            for text in legend.get_texts():
                text.set_color(TOKENS["text_secondary"])
                text.set_fontsize(9)


def _round_bars(ax, radius_frac: float = 0.24, horizontal: bool = False) -> None:
    """Redraw bar/barh rectangle patches with a rounded data-end and a square
    baseline (per dataviz mark spec: '4px rounded data-end, square at the
    baseline'). Purely cosmetic — does not touch the underlying values.
    """
    import matplotlib.patches as mpatches
    import matplotlib.path as mpath

    Path = mpath.Path
    for patch in list(ax.patches):
        if not isinstance(patch, mpatches.Rectangle):
            continue
        x, y, w, h = patch.get_x(), patch.get_y(), patch.get_width(), patch.get_height()
        thickness = abs(h) if horizontal else abs(w)
        r = min(thickness * radius_frac, abs(w) / 2, abs(h) / 2)
        # Signed step back toward the baseline (patch.get_y()/get_x()) from the
        # data-end — handles bars that dip below a zero baseline (negative h/w)
        # without rounding the wrong corner.
        rh = r if h >= 0 else -r
        rw = r if w >= 0 else -r
        if horizontal:
            verts = [
                (x, y), (x + w - rw, y),
                (x + w, y), (x + w, y + rh),
                (x + w, y + h - rh),
                (x + w, y + h), (x + w - rw, y + h),
                (x, y + h), (x, y),
            ]
        else:
            verts = [
                (x, y), (x, y + h - rh),
                (x, y + h), (x + rw, y + h),
                (x + w - rw, y + h),
                (x + w, y + h), (x + w, y + h - rh),
                (x + w, y), (x, y),
            ]
        codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3,
                 Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
        new_patch = mpatches.PathPatch(
            Path(verts, codes), facecolor=patch.get_facecolor(),
            edgecolor="none", zorder=3, label=patch.get_label(),
        )
        patch.set_visible(False)
        ax.add_patch(new_patch)


def status_badge(status: str) -> None:
    icon, label, color, bg, css_classes = STATUS_STYLE.get(
        status, ("?", status, TOKENS["unknown"], TOKENS["bg_muted"], "border-slate-300 text-slate-700 bg-slate-100")
    )
    st.markdown(
        f"""
        <div class="gadded-status-pill {css_classes}">
            <span class="gadded-status-icon" style="color:{color}">{icon}</span>
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


def get_gemini_client():
    if not os.environ.get("GEMINI_API_KEY"):
        return None
    from google import genai
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def get_groq_client():
    """Used only for vendor/financing web search (groq/compound) — Gemini's Google
    Search grounding needs a billing-enabled project even on a free API key."""
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
    financing_options, financing_warnings = [], []
    if run_llm:
        client = get_gemini_client()
        search_client = get_groq_client()
        if client is None:
            reg_error = "GEMINI_API_KEY not set in environment — AI legal explanation and vendor/financing extraction skipped."
        else:
            try:
                from gadded.regulatory import explain_with_llm
                question = "Can this factory install this rooftop solar system under the selected connection model?"
                retrieved = retrieve(question, corpus, top_k=2, client=client)
                reg_explanation = explain_with_llm(question, retrieved, reg_findings, client)
            except Exception as e:
                reg_error = f"Regulatory explanation unavailable this run ({type(e).__name__})."
            if search_client is None:
                vendor_warnings = ["GROQ_API_KEY not set in environment — vendor/financing web search skipped."]
                financing_warnings = list(vendor_warnings)
            else:
                try:
                    from gadded.vendors import discover_vendors
                    vendors, vendor_warnings = discover_vendors(
                        ai.location.address or "Egypt", rec.recommendedCapacityKw,
                        ai.connectionModel, search_client, client, max_candidates=5,
                    )
                except Exception as e:
                    vendor_warnings = [f"vendor discovery unavailable this run ({type(e).__name__})"]
                try:
                    financing_options, financing_warnings = discover_financing_options(
                        rec.recommendedCapacityKw, row["capex_egp"], search_client, client, max_candidates=5,
                    )
                except Exception as e:
                    financing_warnings = [f"financing discovery unavailable this run ({type(e).__name__})"]

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
        "financing_options": financing_options, "financing_warnings": financing_warnings,
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

# --- Hero Header ---
st.markdown(
    f"""
    <div class="gadded-hero mb-4">
        <div class="relative flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
                <div class="inline-flex items-center gap-2 text-emerald-300 text-[11px] font-extrabold tracking-[0.18em] uppercase mb-3">
                    <span>☀️</span> AI Empower Egypt 2026 &middot; Renewable Energy Track
                </div>
                <h1 class="text-3xl sm:text-[2.6rem] font-extrabold text-white tracking-tight leading-none">Gadded</h1>
                <p class="text-slate-300 text-sm sm:text-[15px] font-medium mt-2.5 max-w-xl leading-relaxed">
                    AI-driven solar pre-development assessment for Egyptian industrial factories —
                    from raw energy bills to a financed, permit-checked rooftop system.
                </p>
                <p class="gadded-hero-arabic text-base mt-3 tracking-wide" style="font-family: 'Cairo', sans-serif;">
                    جدد — منصة دعم قرارات الطاقة الشمسية للمصانع المصرية
                </p>
            </div>
            <div class="gadded-hero-badge px-4 py-2.5 rounded-xl text-xs text-white font-extrabold whitespace-nowrap self-start flex items-center gap-2">
                <span class="pulse-dot"></span> Live Analytical Engine
            </div>
        </div>
        <div class="gadded-hero-meter"></div>
        <div class="gadded-hero-stats">
            <div>
                <div class="gadded-hero-stat-label">Physics</div>
                <div class="gadded-hero-stat-value">pvlib PVWatts</div>
            </div>
            <div>
                <div class="gadded-hero-stat-label">Load ML</div>
                <div class="gadded-hero-stat-value">Clustering + Regression</div>
            </div>
            <div>
                <div class="gadded-hero-stat-label">Regulatory</div>
                <div class="gadded-hero-stat-value">LLM-scored RAG</div>
            </div>
            <div>
                <div class="gadded-hero-stat-label">Risk</div>
                <div class="gadded-hero-stat-value">Monte Carlo Finance</div>
            </div>
        </div>
    </div>

    <div class="bg-amber-50/80 border border-amber-200 rounded-xl px-4 py-3 text-xs text-amber-900 flex items-start gap-2.5 mb-5 mt-4">
        <span class="text-sm leading-none mt-0.5">ℹ️</span>
        <div><strong>Disclaimer:</strong> {DISCLAIMER}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- SECTION 1: SCENARIO SELECTION ---
section_banner("01", "🎯", "Choose Your Starting Point", "Pick a pre-configured Egyptian industrial scenario, or build a custom assessment below.")

preset_cols = st.columns(4)
selected_preset_key = st.session_state.get("active_preset", "Golden Case (10th Ramadan Factory)")

for i, (name, details) in enumerate(PRESETS.items()):
    col = preset_cols[i]
    is_active = (selected_preset_key == name)
    active_class = "active" if is_active else ""

    with col:
        check_badge = '<div class="gadded-preset-check">&#10003;</div>' if is_active else ""
        st.markdown(
            f"""
            <div class="gadded-preset-card {active_class} mb-2 flex flex-col justify-between">{check_badge}
                <div>
                    <div class="flex items-center justify-between mb-2.5">
                        <span class="gadded-preset-icon">{details.get('icon', '☀️')}</span>
                        <span class="px-2.5 py-0.5 text-[10px] font-extrabold rounded-full border {details['badge_color']}">
                            {details['badge']}
                        </span>
                    </div>
                    <div class="font-extrabold text-xs text-slate-900 mb-1.5 leading-snug">{name}</div>
                    <div class="text-[11px] text-slate-500 font-medium leading-relaxed mb-3">{details['desc']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Selected ✓" if is_active else "Load Preset", key=f"btn_preset_{i}", use_container_width=True, disabled=is_active):
            st.session_state["active_preset"] = name
            st.rerun()

preset = PRESETS[st.session_state.get("active_preset", "Golden Case (10th Ramadan Factory)")]["data"]

# --- SECTION 2: INPUT WIZARD ---
section_banner("02", "⚙️", "Configure Factory & Site", "Location, energy consumption, site constraints, and financial targets.")

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
            "Enable AI Stages (Gemini Legal Explanation + Groq Web Search)",
            value=True,
            help="Calls the Gemini and Groq APIs. Fails soft if either key is missing or rate limited.",
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
section_banner("03", "📊", "Your Decision Dashboard", "The deterministic feasibility status and the numbers that actually matter for a buy decision.")

# --- Headline sales pitch: the status + 4 numbers that actually convince someone to buy,
# unified in a single "verdict panel" so it reads as one unmissable decision surface.
cash_scn = next((s for s in result.financial if s.scenario == "cash"), None)
best_scn = cash_scn or result.financial[0]
lifetime_years = int(run["assumptions"].number("analysis_period_years"))
lifetime_total = lifetime_savings_egp(best_scn, run["assumptions"])

with st.container(border=True, key="verdict_panel"):
    hdr_col1, hdr_col2 = st.columns([3, 1])
    with hdr_col1:
        st.markdown(
            f"""
            <div class="gadded-project-title">{ai.projectName}</div>
            <div class="gadded-project-meta">📍 {ai.location.address} &nbsp;·&nbsp; ({ai.location.latitude:.4f}, {ai.location.longitude:.4f})</div>
            """,
            unsafe_allow_html=True,
        )
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

    st.markdown('<div class="gadded-verdict-divider"></div>', unsafe_allow_html=True)

    pitch_cols = st.columns(4)
    metric_card(pitch_cols[0], "You Save Every Year", fmt_egp_short(best_scn.yearOneSavingsEgp), "💵", "brand")
    metric_card(
        pitch_cols[1], "Pays for Itself In",
        f"{result.risk.paybackP50Years:.1f} yrs" if result.risk.paybackP50Years else "n/a", "⏱️", "violet",
    )
    metric_card(pitch_cols[2], f"Total Savings ({lifetime_years} yrs)", fmt_egp_short(lifetime_total), "📈", "brand")
    metric_card(pitch_cols[3], "Powered by the Sun", f"{rec.selfSufficiencyRatio*100:.0f}%", "☀️", "solar")

    st.markdown(
        f"""<div class="gadded-verdict-footnote">'{lifetime_years}-year total' adds up every year's savings
        without adjusting for future money being worth less today — see Financial Risk for the
        risk-adjusted (NPV) view.</div>""",
        unsafe_allow_html=True,
    )

if result.status != "likely_feasible":
    with st.expander("⚠️ Decision Rationale & Status Rationale Details", expanded=True):
        for reason in run["feas"].reasons:
            st.markdown(f"- **{reason}**")

with st.expander("🔬 Full Technical Snapshot (system size, generation, approval time)"):
    tech_cols = st.columns(4)
    metric_card(tech_cols[0], "Recommended System Size", f"{rec.recommendedCapacityKw:.0f} kW", "⚡", "brand")
    metric_card(tech_cols[1], "Solar Electricity Produced / Year", fmt_kwh_short(rec.annualGenerationKwh), "☀️", "solar")
    metric_card(tech_cols[2], "Share of Solar Actually Used On-Site", f"{rec.selfConsumptionRatio*100:.1f}%", "🔄", "violet")
    reg_dur = next((f.estimatedDurationDays for f in result.regulatoryFindings if f.estimatedDurationDays), None)
    metric_card(tech_cols[3], "Regulatory Approval Time", f"{reg_dur.minimum}-{reg_dur.maximum} days" if reg_dur else "n/a", "📋", "slate")

st.markdown("<div class='mb-6'></div>", unsafe_allow_html=True)

# --- SECTION 4: DETAILED ANALYTICAL BREAKDOWN ---
section_banner("04", "🔍", "Full Technical Breakdown", "Physics simulations, financial risk, GIS screening, and legal compliance — module by module.")

tab_tech, tab_fin, tab_site, tab_reg, tab_vendor, tab_report = st.tabs(
    ["⚡ Technical & PV", "💰 Financial Risk", "🗺️ Site & GIS", "📜 Regulatory", "🏢 Vendors", "📄 Full Report"]
)

# --- Tab 1: Technical & PV Physics ---
with tab_tech:
    st.markdown("#### Will the Sun Be There When Your Factory Needs Power?")
    best = run["opt"].best_match

    fig, ax = plt.subplots(figsize=(9, 3.2))
    sample = best.hourly.loc["2023-06-05":"2023-06-11"]
    ax.plot(sample.index, sample["load_kw"], label="Your Factory's Power Use", color=TOKENS["technical"], linewidth=2, solid_capstyle="round")
    ax.plot(sample.index, sample["pv_kw"], label=f"Solar Power Produced ({rec.recommendedCapacityKw:.0f} kW system)", color=TOKENS["solar"], linewidth=2, solid_capstyle="round")
    ax.fill_between(sample.index, sample["pv_kw"], color=TOKENS["solar"], alpha=0.10, linewidth=0)
    ax.set_ylabel("kW")
    ax.legend(loc="upper right", frameon=True)
    style_chart(fig, ax)
    st.pyplot(fig)
    st.caption(
        "One sample week. Where the orange (solar) line sits under the dark (factory use) "
        "line, your panels are directly covering what you'd otherwise buy from the grid."
    )

    st.info(
        f"☀️ Your solar system covers **{rec.selfSufficiencyRatio*100:.0f}% of all the electricity your factory uses** "
        f"across the year. The rest ({rec.annualImportedKwh:,.0f} kWh/yr) still comes from the grid as normal. "
        f"It uses **{rec.roofAreaRequiredM2/ai.site.availableRoofAreaM2*100:.0f}% of your available roof space** "
        f"({rec.roofAreaRequiredM2:,.0f} of {ai.site.availableRoofAreaM2:,.0f} m²)."
    )

    with st.expander("🔬 Advanced: How we picked this exact system size"):
        st.caption(
            "We test many system sizes (limited by your roof space) and pick the one that "
            "creates the most long-term financial value — not simply the biggest one that fits."
        )
        fig2, ax2 = plt.subplots(figsize=(8, 3.2))
        table = run["opt"].table
        ax2.plot(
            table["capacity_kw"], table["npv_egp"] / 1e6, color=TOKENS["energy"], linewidth=2,
            marker="o", markersize=4.5, markerfacecolor=TOKENS["energy"], markeredgecolor="#FFFFFF", markeredgewidth=1,
        )
        ax2.axvline(rec.recommendedCapacityKw, color=TOKENS["solar"], linestyle="--", linewidth=1.6, label="Recommended")
        ax2.axvline(rec.physicalMaximumKw, color=TOKENS["boundary"], linestyle=":", linewidth=1.6, label="Roof's Physical Limit")
        ax2.set_xlabel("System Size Tested (kW)")
        ax2.set_ylabel("Project Value (Million EGP)")
        ax2.legend(loc="lower right", frameon=True)
        style_chart(fig2, ax2)
        st.pyplot(fig2)
        st.caption("Each point is one candidate system size; higher is more financially valuable.")

# --- Tab 2: Financial Risk & Monte Carlo ---
with tab_fin:
    st.markdown("#### What Will This Actually Cost You, and What Do You Get Back?")

    scenario_copy = {
        "cash": ("💵", "Pay Cash Upfront", "What you'd need to pay today, in full."),
        "finance": ("🏦", "Pay with a Bank Loan", "Small upfront payment, then fixed monthly installments."),
    }
    fin_cols = st.columns(len(result.financial))
    for idx, s in enumerate(result.financial):
        icon, title, subtitle = scenario_copy.get(s.scenario, ("💰", s.scenario.title(), ""))
        lifetime = lifetime_savings_egp(s, run["assumptions"])
        accent_class = "accent-brand" if s.scenario == "cash" else "accent-ink"
        monthly_row = (
            f'<div class="gadded-scenario-row"><span>Monthly Loan Payment</span> '
            f'<span class="val">{s.monthlyLoanPaymentEgp:,.0f} EGP</span></div>'
            if s.monthlyLoanPaymentEgp else ""
        )
        with fin_cols[idx]:
            st.markdown(
                f"""
                <div class="gadded-glass-card {accent_class}">
                    <div class="font-extrabold text-slate-900 text-lg mb-0.5">{icon} {title}</div>
                    <div class="text-xs text-slate-500 font-medium mb-3.5">{subtitle}</div>
                    <div class="text-[11px] text-slate-500 font-bold uppercase tracking-wide mb-1">Upfront Cost</div>
                    <div class="text-2xl font-extrabold text-emerald-700 mb-3.5 tabnum">{s.capexEgp:,.0f} <span class="text-sm font-bold text-slate-400">EGP</span></div>
                    <div>
                        <div class="gadded-scenario-row"><span>You Save / Year</span> <span class="val">{s.yearOneSavingsEgp:,.0f} EGP</span></div>
                        <div class="gadded-scenario-row"><span>Pays for Itself In</span> <span class="val">{f'{s.simplePaybackYears:.1f} yrs' if s.simplePaybackYears else 'n/a'}</span></div>{monthly_row}
                        <div class="gadded-scenario-row"><span>Total Savings ({lifetime_years} yrs)</span> <span class="val">{lifetime:,.0f} EGP</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.caption(
                f"Equivalent annual return: **{s.irrPct:.0f}%** — like an interest rate, but paid to "
                "you by your own electricity bill instead of a bank."
                if s.irrPct is not None else ""
            )

    st.markdown("<div class='my-4'></div>", unsafe_allow_html=True)
    st.markdown("##### How Sure Are We? (Accounting for Uncertain Sun, Prices & Costs)")
    st.caption(
        f"We ran {result.risk.runCount:,} simulated versions of this project, each with slightly "
        "different weather, prices, and costs, to see how much the outcome could realistically vary."
    )
    fig3, ax3 = plt.subplots(figsize=(8, 3))
    ax3.bar(
        ["Worst Case\n(P10)", "Expected\n(P50)", "Best Case\n(P90)"],
        [result.risk.npvP10Egp / 1e6, result.risk.npvP50Egp / 1e6, result.risk.npvP90Egp / 1e6],
        color=[TOKENS["seq_light"], TOKENS["seq_mid"], TOKENS["seq_dark"]],
        width=0.5, zorder=3,
    )
    ax3.set_ylabel("Project Value (Million EGP)")
    style_chart(fig3, ax3)
    _round_bars(ax3, radius_frac=0.22)
    st.pyplot(fig3)
    if result.risk.probabilityTargetPaybackPct is not None:
        st.caption(
            f"Even in the worst case we tested, this is a positive investment. "
            f"Chance of paying itself back within your {ai.finance.targetPaybackYears:.0f}-year target: "
            f"**{result.risk.probabilityTargetPaybackPct:.0f}%**."
        )

    with st.expander("🔬 Advanced: What affects the outcome the most?"):
        drivers = result.risk.topSensitivityDrivers
        fig4, ax4 = plt.subplots(figsize=(8, 3))
        ax4.barh([d.variable for d in drivers][::-1], [d.influence * 100 for d in drivers][::-1], color=TOKENS["technical"], height=0.5, zorder=3)
        ax4.set_xlabel("Relative Influence on Project Value (%)")
        style_chart(fig4, ax4)
        ax4.grid(True, axis="x", linestyle="-", linewidth=1, alpha=0.6, color=TOKENS["border"])
        ax4.grid(False, axis="y")
        _round_bars(ax4, radius_frac=0.22, horizontal=True)
        st.pyplot(fig4)
        st.caption("One-at-a-time sensitivity ranking — which assumption moves the result most if it's wrong.")

    st.markdown("<div class='my-5'></div>", unsafe_allow_html=True)
    st.markdown("#### 🏦 Bank Financing Options")
    st.caption(
        "Groq `groq/compound` searches the web for real Egyptian bank solar-financing "
        "products, and Gemini extracts structured candidates from the results; pick one "
        "to re-price the finance scenario. Falls back to the static product in "
        "`assumptions.json` if search is unavailable or returns nothing."
    )

    financing_options = run["financing_options"]
    financing_warnings = run["financing_warnings"]
    fin_assumptions = run["assumptions"]
    fin_row = run["opt"].table.loc[rec.recommendedCapacityKw]
    fin_year1_savings = fin_row["year1_savings_egp"]

    default_label = "Default — assumptions.json bank product"
    option_labels = [default_label] + [
        f"{o.bankName} — {o.productName} ({o.financingRatePct:.1f}%/{o.termYears}y, {o.downPaymentPct:.0f}% down)"
        for o in financing_options
    ]
    chosen_label = st.selectbox(
        "Choose a bank financing option to price:", option_labels, key="financing_choice"
    )

    if chosen_label == default_label:
        chosen_option = None
        chosen_scenario = finance_scenario(rec.recommendedCapacityKw, fin_year1_savings, fin_assumptions)
    else:
        chosen_option = financing_options[option_labels.index(chosen_label) - 1]
        chosen_scenario = finance_scenario(
            rec.recommendedCapacityKw, fin_year1_savings, fin_assumptions,
            financing_rate_pct=chosen_option.financingRatePct,
            financing_term_years=chosen_option.termYears,
            down_payment_pct=chosen_option.downPaymentPct,
            financing_fees_pct=chosen_option.feesPct,
            financing_label=f"{chosen_option.bankName} — {chosen_option.productName}",
        )

    chosen_lifetime = lifetime_savings_egp(chosen_scenario, fin_assumptions)
    fin_pick_cols = st.columns(4)
    metric_card(
        fin_pick_cols[0], "Monthly Payment",
        f"{chosen_scenario.monthlyLoanPaymentEgp:,.0f} EGP" if chosen_scenario.monthlyLoanPaymentEgp else "n/a", "🧾", "slate",
    )
    metric_card(
        fin_pick_cols[1], "Pays for Itself In",
        f"{chosen_scenario.simplePaybackYears:.1f} yr" if chosen_scenario.simplePaybackYears else "n/a", "⏱️", "violet",
    )
    metric_card(fin_pick_cols[2], f"Total Savings ({lifetime_years} yrs)", f"{chosen_lifetime:,.0f} EGP", "📈", "brand")
    metric_card(fin_pick_cols[3], "Equivalent Annual Return", f"{chosen_scenario.irrPct:.0f}%" if chosen_scenario.irrPct is not None else "n/a", "💰", "solar")

    if chosen_option is not None:
        with st.expander(f"📎 Source evidence — {chosen_option.bankName} {chosen_option.productName}"):
            st.write(f"**Verification status:** {chosen_option.verificationStatus}")
            if chosen_option.notes:
                st.write(chosen_option.notes)
            for ev in chosen_option.evidence:
                st.markdown(f"- [{ev.title}]({ev.url})")
    elif not financing_options:
        if financing_warnings:
            st.caption("Financing search note: " + "; ".join(financing_warnings))
        else:
            st.caption("Live bank-financing search was not run for this session (enable AI features and rerun).")

# --- Tab 3: Site & GIS Spatial Screening ---
with tab_site:
    st.markdown("#### GIS Spatial & Environmental Screening")
    if not result.gisFindings:
        st.info("No spatial constraints recorded for this site.")
    for f in result.gisFindings:
        icon, icon_bg, badge_label, badge_class = {
            "info": ("✓", "var(--brand-soft)", "Clear", "bg-emerald-100 text-emerald-800 border-emerald-300"),
            "warning": ("⚠", "var(--solar-soft)", "Condition", "bg-amber-100 text-amber-800 border-amber-300"),
            "critical": ("✕", "var(--rose-soft)", "Blocker", "bg-rose-100 text-rose-800 border-rose-300"),
            "unknown": ("?", "#F1F5F9", "Unknown", "bg-slate-100 text-slate-700 border-slate-300"),
        }.get(f.severity, ("?", "#F1F5F9", f.severity, "bg-slate-100 text-slate-700 border-slate-300"))

        meta_html = f"Category: <strong>{f.category}</strong> &middot; Source: <strong>{f.sourceName}</strong>"
        body_html = (
            (f'<div class="text-xs font-bold text-slate-900 mb-1">Value: {f.value} {f.unit or ""}</div>' if f.value is not None else "")
            + ('<div class="text-[11px] text-slate-500 italic">Limitations: ' + " ".join(f.limitations) + "</div>" if f.limitations else "")
        )
        st.markdown(
            finding_card(icon, icon_bg, f.title, badge_label, badge_class, meta_html, body_html),
            unsafe_allow_html=True,
        )

# --- Tab 4: Regulatory Compliance & AI ---
with tab_reg:
    st.markdown("#### Egyptian Solar Legal Framework (Circular 3/2023 & EEAA)")
    if not result.regulatoryFindings:
        st.info("No regulatory findings evaluated.")
    for f in result.regulatoryFindings:
        icon, icon_bg, badge_class = {
            "info": ("✓", "var(--brand-soft)", "bg-emerald-100 text-emerald-800 border-emerald-300"),
            "warning": ("⚠", "var(--solar-soft)", "bg-amber-100 text-amber-800 border-amber-300"),
            "critical": ("✕", "var(--rose-soft)", "bg-rose-100 text-rose-800 border-rose-300"),
        }.get(f.severity, ("?", "#F1F5F9", "bg-slate-100 text-slate-700 border-slate-300"))
        meta_html = f"Confidence: <strong>{f.confidence}</strong> &middot; Verification Required: <strong>{'Yes' if f.verificationRequired else 'No'}</strong>"
        body_html = f'<p class="text-xs text-slate-700 font-medium">{f.explanation}</p>'
        st.markdown(
            finding_card(icon, icon_bg, f.title, f.conclusion.replace("_", " ").title(), badge_class, meta_html, body_html),
            unsafe_allow_html=True,
        )
        if f.citations:
            for c in f.citations:
                with st.expander(f"📜 Authority Citation: {c.documentTitle} ({c.authority})"):
                    st.write(f"**Effective Date:** {c.effectiveDate or 'n/a'}")
                    st.write(f"> *{c.excerpt}*")

    if run["reg_explanation"]:
        st.markdown("##### 🤖 Grounded Gemini AI Legal Analysis")
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
            meta_html = f'<a href="{v.websiteUrl}" target="_blank" class="font-bold text-emerald-700 hover:underline">Visit Website ↗</a>'
            body_html = (
                f'<p class="text-xs text-slate-700 mb-1.5 font-medium">{v.fitExplanation}</p>'
                f'<div class="text-[11px] text-slate-500">Verification Status: <strong>{v.verificationStatus}</strong></div>'
            )
            st.markdown(
                finding_card("🏢", "var(--violet-soft)", v.name, "Vendor", "bg-violet-100 text-violet-800 border-violet-300", meta_html, body_html),
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
st.markdown(
    f"""
    <div class="gadded-footer">
        <span>☀️ Gadded</span>
        <span>&middot;</span>
        <span>AI Empower Egypt 2026</span>
        <span>&middot;</span>
        <span>{DISCLAIMER}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
