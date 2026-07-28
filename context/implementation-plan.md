# Implementation Plan

## Goal

Deliver a hackathon proof of concept for AI Empower Egypt 2026 (Renewable Energy Using AI):
a Python analytical engine + `gadded.ipynb` that takes one industrial rooftop-solar assessment
from input to a combined technical, financial, regulatory, GIS, and vendor-ready result.

Timebox: **1–2 days.** Primary artifact: **notebook-first PoC.**

## What the judges score (from the eval criteria)

- **Phase 1 (qualification):** documentation PDF + PoC → technical assessment → top 10 advance.
- **Phase 2 (final):** live presentation + business assessment + **live technical assessment of ownership** (you must explain and prove you built it).
- PoC need not be a full product; a notebook is explicitly accepted.
- Heavy weight on **originality/innovation**, technical soundness, implementation maturity, and clear concise docs. Undifferentiated or unexplained AI-generated work scores lower.

### Design decisions that follow

- Go deep on a novel, fully-working PoC instead of a broad half-built web app.
- Put real AI/ML front and center: load-profile clustering, regulatory RAG, LLM vendor agent, Monte Carlo.
- Keep the doc short. Keep the repo small (submission limits: <200MB total, <10MB/file, source only).
- Everyone owns and can defend a module live.

## Submission requirements (upload guide)

- Repo of **source files** (caches strip `node_modules`, `.venv`, etc.) + **one PDF**.
- No datasets/model weights/builds committed — link or describe in the doc.
- No `.exe/.dll/.vbs`-type files. **Submit is final — no edits after.**

## Resolve first (blocks multiple modules)

1. **OpenAI API key + confirm web-search tool access** — gates regulatory + vendor. Verify hour 1.
2. **`assumptions.json`** — capex/kW, opex, discount rate, degradation, tariff, export rate, financing terms, PV tilt/azimuth/loss. Each classified OFFICIAL / MARKET_RANGE / LITERATURE_PROXY / SYNTHETIC / DEMO.
3. **`golden_case.json`** — 12 monthly kWh, roof area, sector, shift, location (10th of Ramadan City).
4. **Cached weather CSV** — fetch NASA POWER once for the golden site, commit, go offline.
5. **Archetype profiles** — source (public C&I or synthetic) + manifest; decide archetype count and reconciliation tolerance.
6. **Regulatory excerpts + `zones.geojson`** — 2–3 short official excerpts with dates; 2 industrial-zone polygons + 1 protected area.

## Build order (dependency-driven)

Layer 0 (blocks all): `contracts.py`, `golden_case.json`, `assumptions.json`, repo skeleton, `requirements.txt`.

Then:
1. weather → pv → matching (energy spine)
2. load baseline → load ML (clustering + classifier + reconciliation)
3. optimization → finance → risk
4. gis (shapely site screening)
5. regulatory (retrieve → rules → cited explanation)
6. vendors (web-search agent)
7. feasibility (deterministic status) → report (HTML)
8. assemble `gadded.ipynb` end to end; write tests; finalize doc PDF

## Team split (6)

1. **Lead / integration** — Layer 0, contracts, feasibility, `gadded.ipynb` assembly.
2. **Energy spine** — weather, pv, matching.
3. **Load ML** — archetypes, clustering, classifier, reconciliation (largest AI story).
4. **Finance** — optimization, finance, risk (Monte Carlo).
5. **AI wow** — regulatory RAG (cited) + vendor agent (evidence).
6. **Docs / GIS / tests** — the graded PDF, gis.py, formula + evidence tests.

Every module needs a second team member who can also explain it.

## Day plan

- **Day 1:** Layer 0 → resolve #1–#4 in parallel → energy spine + load + finance working in isolation with passing tests. Doc-writer drafts problem, motivation, approach.
- **Day 2 AM:** RAG + vendor + gis + Monte Carlo.
- **Day 2 PM:** assemble `gadded.ipynb` on the golden case, finalize doc PDF, `README` run steps, clean repo, **submit early** (submit is final).
- If time remains: thin Streamlit wrapper for the live pitch.

## Acceptance criteria (PoC done)

- Golden case runs top-to-bottom in `gadded.ipynb` without manual code surgery.
- Monthly load reconciles to submitted totals within tolerance; energy balance holds hour by hour.
- Optimizer recommends a capacity from economics, not the largest size, and can explain why.
- Finance shows cash + finance; risk shows P10/P50/P90 and sensitivity from a fixed seed.
- Every regulatory finding is `insufficient_information` or carries a citation; the LLM invents nothing.
- Every vendor has ≥1 source; unsupported contact fields are absent; no quality ranking.
- Overall status is deterministic and reproducible from frozen inputs.
- Report renders from stored outputs with disclaimers, versions, and sources.
- Standard test run makes no live external call (cached weather, recorded fixtures).
- Each member can explain their module and the ML vs physics vs rules vs LLM split.

## Documentation PDF outline (concise)

1. Problem + Egyptian relevance (grid strain, import dependence, rooftop-solar gap).
2. Solution: end-to-end solar pre-development decision support.
3. AI/technical approach: load-profile ML, pvlib physics, constrained optimization, deterministic finance, Monte Carlo, GIS, regulatory RAG + rules, LLM vendor agent.
4. Data + sources (classified) and key assumptions.
5. Results on the golden case (with figures).
6. Limitations, disclaimers, and future scaling to the full platform.

## Official data sources

- NASA POWER Hourly — https://power.larc.nasa.gov
- PVGIS — https://re.jrc.ec.europa.eu/pvg_tools/en/tools.html
- pvlib ModelChain — https://pvlib-python.readthedocs.io
- OpenStreetMap — https://www.openstreetmap.org
- NREA (Egypt) — https://nrea.gov.eg/en/Home
- Regulatory: EgyptERA, Ministry of Electricity and Renewable Energy, NREA, EEAA, IDA
