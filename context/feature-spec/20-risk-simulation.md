Add Monte Carlo risk analysis for the recommended solar investment.

## Variables

Support versioned distributions for:

- annual irradiance or PV-yield variability
- capex variation
- tariff escalation
- export-value change
- panel degradation
- O&M variation
- financing rate when finance is selected

Do not add variables without a documented assumption source.

## Simulation

- run a configurable number of scenarios
- accept a random seed
- reuse deterministic finance functions
- store summary results, not every run unless needed for the report
- fail safely when a distribution is invalid

## Output

Return:

- payback P10, P50, P90
- NPV P10, P50, P90
- probability of meeting the user’s target payback
- top sensitivity drivers
- simulation count
- seed
- assumption-set version

## UI Preparation

Expose a result suitable for:

- payback distribution chart
- sensitivity bar chart
- plain-language summary

## Scope Limits

- no approval-time simulation
- no black-box risk score
- no LLM calculations

### Check When Done

- fixed seed reproduces the same summary
- invalid distributions are rejected
- deterministic scenario remains available
- percentiles and probability tests pass
- sensitivity method is documented
