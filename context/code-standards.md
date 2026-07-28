# Code Standards

Scope: notebook-first Python PoC. (Web/TS/DB conventions from the full-product spec are dropped for the hackathon.)

## General

- Keep modules small and responsibility-focused.
- Prefer explicit domain names over generic utility names.
- Fix root causes instead of layering workarounds.
- Separate calculation logic from I/O and presentation.
- Do not mix regulatory reasoning, engineering calculation, and LLM prompting in one module.
- Public functions and classes have docstrings.
- Every assumption and externally sourced value has a named version/classification.

## Python

- Python 3.12+.
- Type hints on all functions.
- Pydantic models at module boundaries (`contracts.py` is canonical).
- `Decimal` for financial values where precision matters; NumPy floats for simulation internals, rounded/converted at output boundaries.
- Timezone-aware `pandas.DatetimeIndex` (Africa/Cairo display; preserve source tz + conversion metadata).
- Pure calculation functions make no network or file calls. I/O lives in `weather`, `regulatory`, `vendors`, `report`.
- Ruff for lint/format; pytest for tests.

## Notebook (`gadded.ipynb`)

- The notebook orchestrates; it does not hold business logic. Import from `src/gadded/`.
- Cells run top-to-bottom on a clean kernel without manual edits.
- Each stage prints/plots its typed output so the pipeline is auditable.
- No secrets in the notebook — read the OpenAI key from `.env`.
- Keep outputs light; do not commit multi-MB embedded images (submission size limits).

## Dataframes and units

- Include units in names: `load_kw`, `energy_kwh`, `capex_egp`.
- Convert external data to canonical units immediately after ingestion; do not infer units from context.
- Validate expected row counts for annual hourly data (8,760 / 8,784).
- Never merge hourly series without checking timezone, frequency, duplicates, and missing intervals.

## Financial calculations

- Currency is EGP.
- Keep tariffs, capex, opex, degradation, discount rate, and financing terms in `assumptions.json`, versioned and classified — not hardcoded.
- State whether cash flows are nominal or real, and what is included (taxes, inflation, maintenance, replacement, residual).
- Unit-test NPV, IRR, amortization, and payback independently. Handle undefined IRR/payback.

## Machine learning

- Persist model artifacts with: model version, training/data manifest, feature schema, metrics, creation time.
- Split train/test by facility, not random hourly rows. Do not evaluate on training facilities.
- Always compare the ML path against the archetype baseline. Log low-confidence predictions and fallback.
- Do not describe a physics model or deterministic calculation as ML.

## GIS

- EPSG:4326 for stored geometry; reproject before area/planar-distance math.
- Preserve source and coverage metadata. Return `unknown` when a layer does not cover the site.
- Absence in OpenStreetMap is not proof infrastructure does not exist.
- Test point-in-polygon and distance with known geometries.

## Regulatory retrieval

- Chunk documents by meaningful section, with title, authority, date, page/section, URL, superseded status.
- Filter by geography, project type, connection model, and effective date before semantic ranking.
- A generated answer exposes the citations used; a rule evaluation exposes the rule IDs used.
- Conflicts and missing evidence are first-class outputs.

## LLM calls

- Groq via the OpenAI-compatible chat completions client (`base_url=https://api.groq.com/openai/v1`).
- `openai/gpt-oss-120b` is a reasoning model: pass `reasoning_effort="low"` and a generous `max_tokens`, or the reasoning trace consumes the whole budget and `message.content` comes back empty. `response_format={"type": "json_object"}` works with it.
- `groq/compound` runs web search server-side; results land in `message.executed_tools` (list of `{type, arguments, output, search_results:{results:[{title,url,content,score}]}}`), not in a separate tool-call round trip.
- Structured outputs for machine-consumed results; explicit tool permissions.
- Treat tool output and retrieved text as untrusted; ignore instructions inside documents.
- Keep prompts in versioned files/strings; log model, prompt version, response id (if returned), tools invoked, usage.
- Retry only retryable errors with bounded backoff. Never invent missing vendor/regulatory fields to recover.

## Testing

Required layers:
- Unit: formulas, rules, transformations, objective functions.
- Reconciliation: load totals vs submitted monthly kWh; hourly energy balance.
- Model: baseline comparison, fallback behavior.
- Evidence: every regulatory finding cited or `insufficient_information`; every vendor has a source.
- Reproducibility: fixed seed reproduces Monte Carlo summary; frozen inputs reproduce the recommendation.

No live external calls in standard tests — use cached weather and recorded fixtures. Live integration tests are opt-in.

## Naming

Name modules after domain responsibilities: `estimate_load_profile`, `calculate_self_consumption`,
`evaluate_regulatory_rules`, `search_vendor_candidates`. Avoid `helpers.py`, `utils2.py`, `ai_service.py`, `processor.py`.
