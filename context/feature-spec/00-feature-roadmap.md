# Gadded Build Roadmap (Notebook-First PoC)

## Status

The numbered files `01`–`32` in this folder describe the **full-product** build
(Next.js + FastAPI + Supabase + Celery). They are **DEFERRED reference** for a
post-hackathon platform — not the current plan.

For the hackathon we build a **notebook-first Python PoC**. Use the plan below.

## Module build order

Layer 0 (blocks everything):
- `contracts.py` — Pydantic shapes from `data-contracts.md`
- `data/golden_case.json`, `data/assumptions.json`
- repo skeleton + `requirements.txt`

Then, dependency-ordered:

1. `weather.py` — NASA POWER adapter + cached CSV
2. `pv.py` — pvlib hourly generation
3. `matching.py` — hourly self-consumption / import / export
4. `load.py` — archetype baseline → clustering → classifier → reconciliation
5. `optimization.py` — constrained sizing (not largest)
6. `finance.py` — cash + finance scenarios
7. `risk.py` — Monte Carlo + sensitivity
8. `gis.py` — Shapely site screening on `zones.geojson`
9. `regulatory.py` — retrieve (cosine over embeddings) → rules → cited LLM
10. `vendors.py` — LLM web-search agent, evidence-gated
11. `feasibility.py` — deterministic status resolver
12. `report.py` — assemble AssessmentResult → HTML
13. `gadded.ipynb` — run the whole pipeline on the golden case
14. `tests/` — formula, reconciliation, evidence, reproducibility
15. `docs/gadded.pdf` — concise documentation

## Rule

Complete one module at a time. Do not combine unrelated calculation, GIS, regulatory,
or LLM work in one step. A module is done only when its scope works in the notebook,
its tests pass, and its owner can explain it live.

## Mapping to the deferred spec

The deferred `01`–`32` files still hold useful detail for individual modules
(e.g. `14` PV, `18` sizing, `24` regulatory retrieval, `28` vendor search).
Read them for module-level guidance, but ignore their web/DB/queue/auth scaffolding.
