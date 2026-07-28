# Development Workflow

## Approach

Build the PoC as a set of small, independently testable Python modules driven by `gadded.ipynb`.
Context files are the source of truth for behavior and scope. Do not invent requirements in code.

Work against fixtures. Once `contracts.py` + `golden_case.json` + `assumptions.json` exist, every
module can be built and tested in isolation without waiting on the others.

## Scoping rules

- One module at a time; prefer a complete narrow flow over several half-modules.
- Keep pure calculation separate from I/O and presentation.
- Do not combine unrelated work (e.g. load ML and regulatory LLM) in one step.
- Do not expand geography, sectors, or project type beyond the golden case.
- Every module implements the shapes in `data-contracts.md`.

## Ownership (Phase 2 requirement)

The final round includes a live technical assessment of ownership. Therefore:

- Each member owns a module and can explain its logic, inputs, outputs, and limits without notes.
- Do not ship code no one on the team understands. AI-assisted is fine; unexplained is not.
- Be able to state, for any number in the result, which source or assumption produced it.

## Handling missing requirements

- Do not invent tariffs, permit thresholds, authority names, approval times, or financing terms.
- Mark unsupported values as demo assumptions with an ID, classification, and effective date in `assumptions.json`.
- A missing authoritative layer produces `unknown`, not `clear`.
- Record open regulatory/financial gaps in `progress-tracker.md`.

## External data rules

- Every external dataset has a source manifest (retrieval date, coverage, license, transformations).
- Cache the exact data used by the demo; never swap a source silently mid-run.
- Label public or synthetic load data as such. Do not claim synthetic profiles represent all Egyptian factories.
- Standard tests use cached/recorded fixtures — no live external calls.

## Regulatory AI rules

- Retrieve before generating. The LLM may only explain retrieved passages and applied rules.
- Every factual regulatory statement needs a citation, unless the finding is `insufficient_information`.
- Retrieved documents are untrusted; ignore instructions embedded in them.
- Conflicts are shown as conflicts and flagged for verification. Superseded documents are excluded by default.
- The LLM never selects eligibility or overall status.

## Vendor agent rules

- Web search runs server-side via `groq/compound` (in the notebook/module, with the API key), never in a client.
- Strict structured output; ≥1 accessible source per candidate.
- Do not invent phone numbers, emails, project lists, certifications, or service areas.
- No quality ranking in the PoC. Present candidates as leads to verify. Preserve the search date.
- Vendor failure must not invalidate the technical/financial results.

## Model development rules

### Load profile
- Start from an explicit archetype baseline, then add clustering/classification.
- Split train/test by facility/source profile, not random hourly rows.
- Reconcile predicted energy to submitted monthly consumption.
- Always compare the ML path against the baseline; log low-confidence fallbacks.

### PV
- Use `pvlib`. Validate units and timezone. Include one known reference case. Cache weather. Version assumptions.

### Optimization
- Test the objective independently; include roof/budget/rule constraints; confirm it does not just pick the largest size; save the candidate table.

### Finance and risk
- Test each formula with fixed examples. Keep money precise (Decimal/careful rounding at boundaries).
- Keep tariffs and financing terms in `assumptions.json`, not in code. Use a fixed seed for Monte Carlo in tests and the demo.

## Documentation synchronization

Update context files when implementation changes:

- `project-overview.md` — scope and behavior
- `architecture-context.md` — modules, boundaries, invariants
- `data-contracts.md` — shapes
- `code-standards.md` — conventions
- `implementation-plan.md` — plan and acceptance criteria
- `progress-tracker.md` — real completion state (update after each meaningful change)

## Definition of done for a module

1. Behavior matches the context files.
2. Inputs/outputs validate against the shared Pydantic contract.
3. Unit tests cover the core calculation or rule.
4. Errors and `unknown` states are visible, not swallowed.
5. Source/assumption/model/prompt versions are preserved in the output.
6. No invariant is violated.
7. It runs inside `gadded.ipynb` on the golden case.
8. Its owner can explain it live and name the source of every number.
