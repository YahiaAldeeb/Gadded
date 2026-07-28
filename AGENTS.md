# Gadded — Agent Build Context

Gadded is a **hackathon proof of concept** (AI Empower Egypt 2026, Renewable Energy Using AI).
The graded artifact is a **Python package + one showcase notebook**, not a web product.

## Deliverable shape

- Core PoC: clean, owned Python modules in `src/gadded/` driven end-to-end by `gadded.ipynb`.
- Documentation: one concise PDF in `docs/`.
- No web app, no database, no queue, no auth for Phase 1. (Optional thin Streamlit wrapper only for the live pitch, time permitting.)

## Read before implementing or making any architectural decision

1. `context/project-overview.md` — product definition, users, scope
2. `context/architecture-context.md` — notebook-first module structure, boundaries, invariants
3. `context/data-contracts.md` — canonical Pydantic shapes
4. `context/code-standards.md` — Python + notebook conventions
5. `context/ai-workflow-rules.md` — build workflow, scoping, ownership, source rules
6. `context/implementation-plan.md` — hackathon eval, 1–2 day plan, team split
7. `context/progress-tracker.md` — current phase, decisions, open items

Update `context/progress-tracker.md` after each meaningful change. If a change alters architecture, scope, or standards, update the relevant context file first.

## Non-negotiables (these drive the score)

- Real ML present and explained (load-profile clustering, regulatory RAG, LLM vendor agent).
- Every regulatory claim carries a citation; every vendor carries a source.
- Overall feasibility status is deterministic; the LLM never decides it.
- Financial output shows ranges (Monte Carlo), not a single payback.
- Do not call physics (`pvlib`) or deterministic finance "ML."
- Missing authoritative data returns `unknown`, never `clear`.
- Every team member can explain their own module live (Phase 2 ownership check).
