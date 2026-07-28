# Architecture Context

Gadded is a **notebook-first Python proof of concept**. No web app, database, queue, or auth in Phase 1.
The analytical engine is the graded work; the notebook orchestrates it end to end on one golden case.

## Stack

| Layer | Technology | Role |
| --- | --- | --- |
| Language | Python 3.12+ | All logic |
| Orchestration | Jupyter notebook (`gadded.ipynb`) | Runs the full pipeline on the golden case, renders charts |
| Contracts | Pydantic | Canonical typed shapes shared across modules |
| Data / math | pandas, NumPy | Series, tables, units |
| PV physics | pvlib | Hourly PV generation |
| ML | scikit-learn | Load-profile clustering + archetype classifier |
| Finance | numpy-financial | NPV, IRR, amortization, payback |
| Risk | NumPy | Monte Carlo + sensitivity |
| Geospatial | Shapely | Point-in-polygon, distance on local GeoJSON |
| Retrieval | TF-IDF cosine (scikit-learn) | Regulatory RAG over ~10 local excerpt chunks (no vector DB, no embeddings API) |
| LLM | Groq (OpenAI-compatible chat completions API) | `openai/gpt-oss-120b` for cited regulatory explanation + RFQ wording (reasoning model — pass `reasoning_effort="low"`); `groq/compound` for the vendor web-search agent (built-in server-side search, evidence returned in `message.executed_tools`) |
| Charts | matplotlib | Notebook + report visuals |
| Report | Jinja2 HTML (optional PDF) | Combined assessment artifact |
| Tests | pytest | Formula, reconciliation, evidence checks |

## Repository shape

```text
gadded/
├── gadded.ipynb            # graded showcase: input -> full assessment
├── README.md               # exact install + run steps (reviewers run from source)
├── requirements.txt
├── docs/gadded.pdf         # graded documentation (one PDF)
├── data/
│   ├── golden_case.json            # the fixed demo assessment input
│   ├── weather_10ramadan_cached.csv  # NASA POWER fetched once, then offline
│   ├── load_archetypes/            # normalized profiles + manifest
│   ├── regulations/                # 2–3 short official excerpts + manifest
│   ├── zones.geojson               # 2 industrial-zone polys + 1 protected area
│   └── assumptions.json            # versioned, classified assumptions
├── src/gadded/
│   ├── contracts.py        # Pydantic models (data-contracts.md)
│   ├── weather.py          # NASA POWER adapter + cache
│   ├── pv.py               # pvlib generation
│   ├── load.py             # archetype baseline + ML clustering/classifier
│   ├── matching.py         # hourly self-consumption / import / export
│   ├── optimization.py     # constrained sizing
│   ├── finance.py          # cash + finance scenarios
│   ├── risk.py             # Monte Carlo + sensitivity
│   ├── gis.py              # shapely site screening
│   ├── regulatory.py       # RAG retrieval + cited LLM + deterministic rules
│   ├── vendors.py          # LLM web-search agent (evidence-gated)
│   ├── feasibility.py      # deterministic status resolver
│   └── report.py           # assemble AssessmentResult + HTML
└── tests/
    └── test_*.py
```

## Module boundaries

- Pure calculation modules (`pv`, `load` baseline, `matching`, `optimization`, `finance`, `risk`, `feasibility`) make **no network or file calls** — inputs in, typed outputs out. Testable in isolation.
- I/O lives at the edges: `weather` (cached fetch), `regulatory`/`vendors` (OpenAI), `report` (render).
- `contracts.py` is the single source of shapes. No module invents a competing shape for assessment input, hourly series, GIS finding, regulatory finding, financial scenario, vendor evidence, or final result.
- Do not mix regulatory reasoning, engineering calculation, and LLM prompting in one module.

## Pipeline (what the notebook runs)

```text
golden_case.json
  -> validate (contracts)
  -> weather (cached)
  -> load (ML profile, reconciled to monthly kWh)
  -> pv (pvlib, per candidate size)
  -> matching (hourly self/import/export)
  -> optimization (pick capacity by NPV, not largest)
  -> finance (cash + finance) -> risk (Monte Carlo)
  -> gis (site screening) 
  -> regulatory (retrieve -> rules -> cited explanation)
  -> feasibility (deterministic status)
  -> vendors (LLM web search, evidence-gated)
  -> report (AssessmentResult -> HTML)
```

## Hackathon swaps (deliberate, from the full-product spec)

- pgvector → TF-IDF cosine (scikit-learn) over a local excerpt corpus (only ~10 chunks).
- PostGIS → Shapely on local GeoJSON.
- Supabase / Next.js / Celery / Redis / auth → removed.
- OpenAI Responses API → Groq's OpenAI-compatible endpoint (`openai/gpt-oss-120b` for reasoning/explanation, `groq/compound` for web-search).
- Live NASA POWER call → one cached CSV committed to the repo.
- Model weights / large datasets → not committed; described in the doc (submission size limits).

## AI and analytics boundaries

- **Load profile (ML):** cluster normalized curves into archetypes, classify user inputs to an archetype/shape, then scale to reconcile to submitted monthly kWh. Preserve model version, features, archetype, confidence; low confidence falls back to the deterministic archetype with a warning.
- **PV (physics):** `pvlib`. Not machine learning. Preserve weather source, tilt, azimuth, loss, model version.
- **Optimization:** constrained; objective and constraints inspectable; recommendation reproducible from frozen inputs; must not simply pick the largest size.
- **Finance / risk:** deterministic formulas, tested; Monte Carlo seeded; show P10/P50/P90 and sensitivity.
- **Regulatory:** retrieve (TF-IDF) → apply deterministic versioned rules → LLM (`openai/gpt-oss-120b`) explains only retrieved evidence + applied rules. The LLM never invents a permit, threshold, authority, duration, or eligibility decision.
- **Vendors:** `groq/compound` web-search agent, strict structured output (extracted by a second `openai/gpt-oss-120b` pass constrained to the returned search evidence only), ≥1 accessible source per candidate, contact fields null when unsupported, no quality ranking.

## Invariants

1. LLM text never decides eligibility or overall status — rules and cited evidence do.
2. Engineering and financial calculations are deterministic and independently tested.
3. Every recommendation ties to frozen inputs, assumptions, and model/prompt versions.
4. GIS never implies authoritative completeness; missing coverage returns `unknown`.
5. A displayed vendor always has source evidence.
6. External data used by the demo is cached/versioned for reproducibility.
7. Predicted load totals reconcile with submitted monthly totals within documented tolerance.
8. The report is assembled from stored structured outputs, not recomputed.
9. The PoC supports only industrial rooftop solar in the selected geography.
