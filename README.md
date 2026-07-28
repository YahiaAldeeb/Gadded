# Gadded

AI-driven solar pre-development decision support for Egyptian factories.
Built for **AI Empower Egypt 2026 — Renewable Energy Using AI**.

Gadded turns a factory location + electricity consumption into a preliminary industrial
rooftop-solar assessment: recommended PV size, expected generation and self-consumption,
financial return with uncertainty, a cited regulatory roadmap, and evidence-backed EPC
vendor leads.

This proof of concept is a **Python package + a showcase notebook** (the graded
artifact), plus a thin optional Streamlit UI for the live demo/pitch.

## Setup

Requires Python 3.12+ (developed on 3.14).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt        # or requirements.lock.txt for pinned versions
```

Copy `.env.example` to `.env` and set your keys (needed only for the regulatory, vendor,
and financing stages — Gemini for reasoning/extraction, Groq for the vendor/financing
web search, since Gemini's own search grounding needs a billing-enabled project):

```
GEMINI_API_KEY=...
GROQ_API_KEY=gsk_...
```

## Run

```powershell
jupyter notebook gadded.ipynb          # runs the full pipeline on the golden case (graded artifact)
streamlit run app.py                    # optional thin demo UI for the live pitch
pytest                                  # formula, reconciliation, and evidence tests
```

## Layout

```
src/gadded/        analytical modules (contracts, weather, pv, load, load_ml,
                   matching, optimization, finance, risk, gis, regulatory,
                   vendors, feasibility, report)
data/              golden_case.json, assumptions.json, cached weather,
                   load archetypes, regulatory excerpts, zones.geojson
gadded.ipynb       graded showcase: input -> full assessment
app.py             optional thin Streamlit UI for the live pitch (not graded)
docs/gadded.pdf    documentation
tests/             pytest suite
```

## Data & assumptions

Every external value carries a source and classification (OFFICIAL / MARKET_RANGE /
LITERATURE_PROXY / SYNTHETIC / DEMO) in `data/assumptions.json`. Values labeled `DEMO`
are placeholders and must be replaced with sourced figures before any formal use.

## Disclaimer

This is a preliminary decision-support assessment. Verify regulatory, engineering, grid,
vendor, and financing information with the responsible authorities and qualified professionals.
