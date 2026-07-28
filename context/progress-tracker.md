# Progress Tracker

Update whenever the phase, active module, scope, or implementation state changes.

## Context

- Competition: AI Empower Egypt 2026 — Renewable Energy Using AI.
- Deliverable: notebook-first Python PoC (`gadded.ipynb` + `src/gadded/`) + one documentation PDF.
- Timebox: 1–2 days. Phase 1 = docs + PoC → top 10 advance. Phase 2 = live pitch + ownership check.

## Pivot decision (current)

- Dropped the full-product build (Next.js, Supabase, PostGIS, pgvector, Celery, auth) as wrong-for-a-PoC scope.
- Kept the product concept: end-to-end solar pre-development decision support.
- Graded artifact is the analytical engine + showcase notebook, not a web app.
- Swaps: pgvector → NumPy cosine over OpenAI embeddings; PostGIS → Shapely; live weather → cached CSV.

## Current phase

- Phase 0 → Phase 1 build. Standing up Layer 0 and resolving shared blockers.

## Completed

- Product concept, scope, and hybrid AI approach defined.
- Context pack rewritten for the notebook-first PoC (this pivot).
- Data contracts frozen as canonical Pydantic shapes.
- Environment: venv (Python 3.14), all deps installed, `requirements.lock.txt` pinned.
- Layer 0 core: `contracts.py` (all shapes + invariants), `golden_case.json`, `assumptions.json` (22 classified values), `pyproject.toml`, `README`, `.env.example`. 4/4 contract tests pass.
- `weather.py`: NASA POWER adapter + cache. Golden-site 2023 hourly cached (`data/weather_10ramadan_cached.csv`, 460KB, 8760 rows, Africa/Cairo). Live fetch confirmed working.
- `pv.py`: pvlib PVWatts (Hay-Davies transposition, Faiman cell temp). Golden 500 kW → 874 MWh/yr, 1748 kWh/kWp. 10/10 tests pass.
- `load.py`: synthetic archetype baseline (`data/load_archetypes/archetypes.json`), exact per-month reconciliation to submitted kWh, index-aligned to weather. (ML clustering path still to come.)
- `matching.py`: canonical hourly self/import/export + tariff valuation, alignment guards. Golden @500kW: 92.5% self-consumption, 41.2% self-sufficiency, 1.86M EGP/yr saved, 7.5% spilled.
- `optimization.py`: NPV grid search, PV modeled once per-kW then scaled, roof + budget constraints, candidate table persisted. Golden picks **475 kW (economic optimum, not the 500 kW roof max)**, NPV 2.44M EGP. 27/27 tests pass.
- `finance.py`: cash + finance (amortizing loan) scenarios, NPV/IRR/simple+discounted payback, numpy-financial. Cash NPV cross-checks exactly against optimizer objective (2.438M EGP). Golden: cash IRR 13.8%, simple payback 8.18y (misses 6y target); finance IRR 12.4%, monthly loan 255,577 EGP. 38/38 tests pass.
- `risk.py`: Monte Carlo (seeded, reuses deterministic finance functions per draw) over PV yield, capex, opex, tariff-escalation uncertainty + one-at-a-time sensitivity ranking. Added `opex_variability_pct`, `tariff_escalation_variability_pct`, `financing_rate_variability_pct` to assumptions.json. Golden: NPV P10/P50/P90 = -1.72M / +2.33M / +7.66M EGP; payback P10/P50/P90 = 7.1/8.2/9.6y; P(payback≤6y target)=0.2%; top driver is tariff escalation (56.5%), not PV yield. 45/45 tests pass.
- `data/zones.geojson`: hand-drawn SYNTHETIC layer (2 industrial zones incl. golden site, 1 protected-area placeholder, substation + road proxy points), manifest labels it non-authoritative.
- `gis.py`: Shapely point-in-polygon / intersects / nearest-distance, local equirectangular projection for meter distances (documented approximation, no pyproj dependency). Missing layer → `unknown` severity, not `clear`; unmatched zone → "not found in dataset" wording, not "does not exist". Golden site: inside 10th-of-Ramadan zone, no protected-area hit, substation ~1km. 53/53 tests pass.
- **LLM provider decision: Groq (OpenAI-compatible endpoint), not OpenAI.** Live-verified: `openai/gpt-oss-120b` (reasoning model — needs `reasoning_effort="low"` + generous `max_tokens` or output comes back empty) for regulatory/RFQ text; `groq/compound` (real server-side web search, evidence in `message.executed_tools`) for vendor search. `.env`/`.env.example` updated to `GROQ_API_KEY` + model env vars. Updated architecture-context.md, code-standards.md, ai-workflow-rules.md to reflect this (was previously specced as OpenAI).
- `data/regulations/excerpts.json` + `rules.json`: 3 SYNTHETIC excerpts (fictional "DNERA" authority, clearly labeled non-authoritative) covering self-consumption ownership rule, net-metering 20MW threshold, protected-area environmental clearance. 5 deterministic rules over a safe dict-DSL (no eval of stored code).
- `regulatory.py`: TF-IDF cosine retrieval (scikit-learn, local, no embeddings API) + rule engine + LLM cited explanation (Groq). Golden case: RULE-001 fires (applicable, cited to exc-001), LLM explanation live-verified grounded (mentions only ownership/export facts from the excerpt, no invented "EgyptERA"/"NREA"). 63/63 tests pass (incl. one live LLM test, opt-in via GROQ_API_KEY presence).
- `vendors.py`: two-stage agent — `groq/compound` searches live (evidence in `message.executed_tools`, deduped by URL across queries), `openai/gpt-oss-120b` extracts strict `VendorCandidate` JSON constrained to only that evidence (JSON mode + `reasoning_effort="low"`). Enforces: ≥1 evidence per candidate (Pydantic-dropped otherwise), forbidden-claims filter (best/licensed/certified/guaranteed/etc.), name dedup, contact fields null unless present in source text, both stages fail-soft (warnings, never raise). Extraction prompt explicitly separates REQUIRED (must be real text or omit the candidate) vs OPTIONAL (null when unsupported) fields after an early pass showed the model nulling required fields too often. 70/70 offline tests pass (mocked-LLM, covers every drop/dedup rule). Live path exercised repeatedly this session — confirmed real search + real extraction on a clean run, and confirmed the fail-soft path (rate-limit/timeout → empty list + warnings, never a crash, never a fabricated vendor) on a rate-limited run. Note: this session hit Groq rate limits from repeated live testing — expected on a free/dev tier; run fresh (not back-to-back with many other calls) for the actual demo/pitch.

- `feasibility.py`: deterministic 5-branch waterfall (insufficient_information > potentially_ineligible > high_risk > feasible_with_conditions > likely_feasible), each branch records which finding/warning drove it. Financial performance deliberately does not change the status (reported separately as ranges). Golden case chained end-to-end through real `gis.py` + `regulatory.py` → **likely_feasible**. 80/80 offline tests pass.

- `report.py`: `assemble_result()` validates everything into the canonical `AssessmentResult`; `render_html()` is a pure/deterministic Jinja2 render (no recompute, no clock access — caller supplies `generated_at`). Confirmed end-to-end on the golden case: 475kW, likely_feasible, both financial scenarios, risk table, 4 GIS findings, 1 regulatory finding with citation, empty-vendor case handled gracefully, standing model-limitation warning shown without downgrading status. 84/84 offline tests pass (86 total incl. 2 live-only). **Design note:** `feasibility.py` module_warnings should be run-specific anomalies, not standing PoC-model disclosures (e.g. "synthetic baseline") — those still show in the report's Warnings section via `AssessmentResult.warnings`, they just don't downgrade status on every run. Caller (test/notebook) filters for this.
- **Full pipeline now runs end-to-end for the golden case**: weather → load → pv → optimization → finance → risk → gis → regulatory → feasibility → report. This is the core PoC engine.

- Refactored `load.py`: extracted shared, reusable helpers (`load_archetype_spec`, `daily_production_intensity`, `default_shift_hours`, `week_shape_from_params`, `tile_week_shape_to_index`) so the ML path reuses the exact same shape-building and reconciliation math as the baseline — no duplicated logic. All prior load/matching/optimization/report tests still pass unchanged after the refactor.
- `load_ml.py` — the actual ML the project's non-negotiables require: synthetic facility population (parametric jitter + noise around the 6 archetype combos, clearly labeled SYNTHETIC, not measured data) → KMeans clustering on normalized 168-hour weekly shapes with **k chosen by silhouette-score sweep, not intuition** → RandomForest classifier mapping user inputs to a cluster, evaluated on a facility-level held-out split against a majority-lookup baseline. Low classifier confidence (<0.40) falls back to the deterministic baseline, never a weak ML guess (verified with a fake low-confidence classifier). Golden-case run: **silhouette picked k=6, exactly matching the 6 known combos** (validates the technique); classifier test accuracy **95.7% vs. 91.3% baseline** (facility-level held-out); golden case predicted with **high confidence, 0.0% reconciliation error**. Joblib persistence (`save_bundle`/`load_bundle`) tested via roundtrip; no model artifact is committed to the repo (submission-size guidance — the notebook trains it fresh). 92/92 offline tests pass (94 total incl. 2 live-only elsewhere).

- **`gadded.ipynb` built and executed end-to-end for real (35 cells, 0 errors).** Added `notebook`/`nbconvert`/`ipykernel` to requirements.txt (not previously installed). Runs the full pipeline live: golden case → assumptions table → cached weather + chart → load ML (trains fresh, prints metrics, compares vs baseline, chart) → PV physics chart → optimization (NPV-vs-capacity chart) → matching chart → finance table → Monte Carlo risk (charts) → GIS table → regulatory rules + live-verified grounded LLM explanation → vendor discovery (live call attempted, gracefully degraded this run — see below) → deterministic feasibility → assembled report → HTML rendered inline + written to `docs/example_report.html` (7.6KB; notebook itself 392KB with embedded charts, both trivially within submission size limits).
- This run: recommended capacity **350 kW** (using the ML-predicted load shape, vs 475 kW seen earlier with the deterministic baseline in standalone tests) — expected, not a bug: the ML cluster's intra-day shape differs slightly from the hand-authored archetype, which shifts the self-consumption/NPV tradeoff. Both are legitimate outputs of different (correctly-functioning) load sources.
- Vendor discovery in this run hit the same Groq rate-limit from repeated live testing this session (0 candidates, 2 clear warnings, no crash) — the fail-soft design worked exactly as intended and did not block the rest of the pipeline or the feasibility status. A fresh run (not preceded by dozens of other live calls) should get real candidates, as already demonstrated earlier this session.
- Overall status this run: **likely_feasible**.

- **`docs/gadded.pdf` written and verified (5 pages, 84KB).** Source kept alongside as `docs/gadded.html`. Built with `xhtml2pdf` (pure-Python HTML→PDF, no system binaries needed — added to requirements.txt along with `pypdf` for verification). Covers all eval-required sections: problem statement, motivation, approach/methodology, AI/technical components (table classifying every module as ML / physics / optimization / simulation / retrieval / rules / grounded-LLM), key assumptions/constraints/design decisions, golden-case results (2 real charts: NPV-vs-capacity, Monte Carlo NPV range), expected value/impact, limitations. All numbers pulled live from the real modules (same seed as the notebook, matches exactly).
- **Encoding gotcha (fixed):** xhtml2pdf's default Helvetica font does not support em-dash, middle-dot, `&sup2;`, or `&times;` — they silently render as a replacement glyph. Verified via `pypdf` text extraction (scan for any char outside ASCII/`\x09`) and fixed by using plain ASCII (`-`, `/`, `m2`) throughout. Also: xhtml2pdf doesn't parse percentage image widths (`width: 46%`) — use a fixed px value instead.
- Requirements.txt now also includes `notebook`, `nbconvert`, `ipykernel` (added for the notebook milestone) and `xhtml2pdf`, `pypdf` (this doc milestone). `requirements.lock.txt` refreshed (140 lines).

- **`app.py`: thin Streamlit demo UI built for the live pitch (not the graded artifact — see AGENTS.md).** Reuses `src/gadded` directly, no duplicated logic. Applies the parts of `context/ui-context.md` explicitly marked as still-applicable: status system (icon+text+color, never color alone), 6-metric strip, the six result tabs (Technical/Financial/Site/Regulatory/Vendors/Report), chart labeling+caption rules, persistent disclaimer banner, source/assumptions drawer accessible from every result, and distinct empty/error states (e.g. Vendors tab shows "not run" vs "unavailable this run" vs real candidates). 4 scenario presets (golden case, unknown-ownership, protected-area site, oversized-roof) — verified via direct pipeline execution to hit their intended status exactly: `likely_feasible` / `insufficient_information` / `high_risk` / `likely_feasible` respectively.
- Verified live in a real browser (claude-in-chrome click-through): server starts clean, form submits, full pipeline runs and renders correctly across all 6 tabs with real numbers. **Bug caught and fixed:** metric-card values were wrapping mid-digit ("1,167,89" / "1 EGP") at narrow column widths — fixed with `word-break: keep-all` CSS plus a `fmt_egp_short`/`fmt_kwh_short` abbreviation helper (e.g. "1.17M EGP") so cards never break mid-number.
- Added `streamlit` to requirements.txt; refreshed requirements.lock.txt (159 lines). Updated README (GROQ_API_KEY, not the stale OPENAI_API_KEY; documented `streamlit run app.py`).

## Real-data integration pass (major update)

User supplied real research (official Egyptian tariff table, real EgyptERA circular
summaries, real bank solar-loan products) plus a real WDPA protected-areas download.
Replaced most of the previously-synthetic/DEMO regulatory, GIS, and financial data:

- **`data/assumptions.json`**: `tariff_retail_egp_per_kwh` → 2.55 EGP/kWh (official medium-voltage
  22-11kV bracket, matches golden case's 22kV connection). `capex_per_kw_egp` → 10,000 EGP/kW
  (real market range, down from a 32,000 guess — MARKET_RANGE, consumer/commercial sourced,
  not a verified industrial quote). `financing_rate_pct`/`financing_term_years` → 20%/7yr
  (Credit Agricole Egypt real solar-loan product). `financing_fees_pct` → 1% (CIB's real fee
  schedule). `down_payment_pct` → tried 0% (Credit Agricole's 100%-financing product) but
  that produces a degenerate near-zero-equity IRR (869%, mathematically correct but not
  presentable) — switched to 20% (QNB Egypt Green Loan's real 80%-financing product) on
  user's call, giving a sane finance IRR (79%) while staying a real cited product.
- **`data/regulations/excerpts.json` + `rules.json`**: replaced the fictional "DNERA"
  placeholder entirely with real citations — EgyptERA Circular No. 3/2023 (self-consumption
  core rules + permit/licence thresholds), Circular No. 6/2023 (site-control amendment),
  Circular No. 4/2026 (net-metering capacity/process), Renewable Energy Law No. 203/2014,
  Protected Areas Law No. 102/1983, Environmental Law No. 4/1994 + EEAA guidance. Excerpt text
  is explicitly labeled as a **paraphrased research summary**, not a verbatim legal quote (I
  did not read the primary circular PDFs directly). Rewrote from 5 fake rules to 8 real ones
  with real thresholds: 30MW self-consumption cap, 500kW permit-exemption tier, 20MW
  net-metering ceiling, 25-year site-control requirement, real published net-metering
  timeline (22-395 days), and a new always-on rule requiring EEAA environmental-impact
  assessment for any industrial project (this is genuinely always required per real research
  — residential exemption doesn't apply to industrial).
- **`data/zones.geojson`**: merged in all **47 real Egyptian protected areas** from the WDPA/WDOECM
  (UNEP-WCMC/IUCN) download the user provided (via `pyogrio`, installed temporarily — NOT
  added to requirements.txt, since it's a one-time author-side data-prep tool, not a runtime
  dependency, keeping the shipped project GDAL-free per the original architecture decision).
  Also pulled **real OpenStreetMap data via the Overpass API** for the 10th of Ramadan City
  area: unioned 40 real `landuse=industrial` sector polygons into the real industrial-zone
  boundary, picked the nearest real named road (طريق الإسماعيلية / Ismailia Road) and nearest
  2 real `power=substation` features. Kept exactly one clearly-labeled SYNTHETIC demo
  protected-area polygon (the real nearest WDPA site is ~45km from the golden site) solely so
  the interactive "protected area" scenario preset still has something to demonstrate against.
  6th of October zone remains a synthetic placeholder (out of scope for this pass).
- **`data/golden_case.json`**: nudged the site coordinates (30.3009,31.7411 → 30.3203,31.7466)
  to sit genuinely inside the real OSM-mapped industrial zone (verified via `.contains()`)
  instead of ~1.4km outside it — same conceptual location ("a factory in 10th of Ramadan
  City"), now grounded in real geometry. `industrialZone`/`address` updated to name the real
  sector ("Industrial Zone C6 / المنطقة الصناعية ج6").

**Real-data-driven behavior changes (expected, not bugs):**
- Golden case's recommended capacity is now **500 kW = the full roof** (binding constraint
  `roof_area`, not `economic_optimum`) — real capex is ~3x cheaper than the old guess, so for
  this factory's high consumption, maxing the roof is genuinely the NPV-optimal choice. The
  "doesn't just pick the largest size" mechanism is still proven correct by
  `test_optimization.py::test_not_largest_when_load_is_small` and by the Streamlit app's
  "oversized roof" preset (which settles at 775 kW, well under its ~3,333 kW physical max).
- Financials got dramatically better with real, cheaper capex: cash payback ~2.7y (was 8.2y),
  NPV P10-P90 all positive (10.7M-20.6M EGP), 100% probability of meeting the 6-year target.
- Golden case's overall status shifted from `likely_feasible` to **`feasible_with_conditions`**
  — because a real Egyptian industrial project always needs EEAA environmental sign-off
  (RULE-008), which the old fake rule set didn't capture. This is a real, honest condition,
  not a regression.
- Updated all affected tests (`test_gis.py`, `test_regulatory.py`, `test_feasibility.py`,
  `test_report.py`, `test_optimization.py`'s budget test which had capex hardcoded in a
  comment) to match the new real thresholds/behavior. **100/100 tests still pass** (98
  offline + 2 live).
- Re-executed `gadded.ipynb` end to end (0 errors) and rebuilt `docs/gadded.pdf` (now 6
  pages, 86KB) with all the new real numbers and an updated narrative explaining the
  roof-bound/feasible-with-conditions results honestly.

## Remaining (optional, time-permitting)

- `rfq.py` (RFQ generation, spec module 29) — `report.py` already covers the graded-deliverable surface; not required for submission.
- A fresh (non-rate-limited) run of the vendor-discovery cell in `gadded.ipynb` to capture real vendor candidates in the committed notebook output, if convenient before final submission.
- Final repo cleanup pass before zipping/submitting: confirm `.venv`, `__pycache__`, `.pytest_cache` are excluded (`.gitignore` already covers this); confirm total size well under the 200MB/10MB-per-file submission limits (currently trivial — largest files are the notebook at ~400KB and the PDF at ~84KB).

## Resolve first (blocks multiple modules)

1. OpenAI API key + confirm web-search tool access (regulatory + vendor).
2. `assumptions.json` values, each classified.
3. `golden_case.json` numbers (12 monthly kWh, roof area, sector, shift, location).
4. Cached NASA POWER weather CSV for the golden site.
5. Archetype profiles source + manifest; archetype count; reconciliation tolerance.
6. Regulatory excerpts + `zones.geojson`.

## Next up

- Energy spine (weather → pv → matching).
- Load ML (clustering + classifier + reconciliation).
- Finance + optimization + risk.
- GIS, regulatory RAG, vendor agent.
- Feasibility resolver, report, notebook assembly, tests, doc PDF.

## Open questions

- Which two industrial zones/governorates (default: 10th of Ramadan City + one more).
- Which official documents define the self-consumption / net-metering paths and thresholds.
- Which capex/opex/tariff/discount/financing values are sourced vs DEMO.
- Reconciliation tolerance and Monte Carlo run count for the demo.
- Public vs synthetic load-profile source and its license.

## Key decisions

- Notebook-first PoC; web app deferred.
- OpenAI Responses API for regulatory explanation and vendor web search.
- Regulatory eligibility and overall status decided by deterministic rules, never the LLM.
- Every vendor requires source evidence; results show ranges, not a single payback.
- Industrial rooftop solar only, golden case only.

## Risks / mitigations

- OpenAI web-search access unconfirmed → verify hour 1; vendor stage is non-critical if it fails.
- Weak load validation data → synthetic + labeled, compared to baseline.
- Stale/absent regulatory docs → cite dates, mark `insufficient_information` when unsupported.
- Live API flakiness in demo → cached weather, recorded fixtures.
- Submission is final → clean repo and submit early.

## Notes

- No application code implemented yet at the time of this pivot.
