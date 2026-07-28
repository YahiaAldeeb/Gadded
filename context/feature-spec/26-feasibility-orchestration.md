Connect the completed analytical modules into one assessment pipeline.

## Worker Sequence

For a queued run:

1. validate frozen input
2. resolve source and assumption versions
3. fetch/cached weather
4. predict hourly factory load
5. run GIS site screening
6. retrieve applicable regulatory evidence
7. evaluate regulatory rules
8. generate PV profiles for candidate sizes
9. match load and generation
10. optimize capacity
11. calculate cash and finance scenarios
12. run Monte Carlo simulation
13. generate regulatory explanation
14. calculate overall preliminary status
15. persist structured outputs

Vendor search and report generation remain separate later stages.

## Overall Status

Implement a deterministic status resolver:

- likely feasible
- feasible with conditions
- high risk
- potentially ineligible
- insufficient information

The LLM must not select the overall status.

## Persistence

Store:

- module outputs
- versions
- warnings
- source references
- artifact references
- stage durations
- failure details

A failure in a critical core module fails the run.

A noncritical optional module should produce a warning.

## Scope Limits

- no vendor search
- no RFQ
- no PDF report
- no Arabic output

### Check When Done

- golden case completes through all core modules
- overall status is deterministic
- rerunning frozen inputs is reproducible
- module failures produce clear run states
- versions and sources are persisted
