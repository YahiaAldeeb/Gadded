Harden and evaluate the complete Gadded proof of concept.

## Golden Cases

Create at least:

1. feasible daytime-load factory case
2. oversized-system case where optimization selects a smaller capacity
3. insufficient ownership or regulatory-information case
4. site with a GIS warning
5. vendor-search failure case

## Automated Tests

Require:

- TypeScript/Python contract tests
- API authentication and authorization tests
- input snapshot immutability test
- hourly load reconciliation tests
- PV sanity tests
- energy-balance tests
- optimization objective tests
- finance formula tests
- Monte Carlo reproducibility tests
- GIS known-point tests
- regulatory retrieval/citation tests
- regulatory rule tests
- vendor evidence tests
- end-to-end browser test from assessment to report

## LLM Evaluations

Test:

- citation completeness
- refusal to invent missing regulatory facts
- prompt-injection resistance
- vendor evidence requirement
- no unsupported rankings
- structured-output validity

## Demo Reliability

Add:

- cached weather fallback
- recorded regulatory fixtures
- controlled vendor-search fallback message
- visible source dates
- run retry behavior
- seed demo data
- clean-environment setup instructions

## Team Readiness

Every team member must be able to explain:

- load-profile ML
- PV physics
- hourly matching
- optimization
- deterministic finance
- Monte Carlo
- GIS
- RAG
- regulatory rules
- vendor web-search agent

### Check When Done

- all golden cases complete
- standard CI makes no live external calls
- end-to-end demo succeeds from a clean environment
- implemented claims match the pitch
- open limitations are documented
- progress tracker reflects completion
