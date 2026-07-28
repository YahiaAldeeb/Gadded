Add the first deterministic industrial load-profile baseline.

## Archetypes

Create one normalized hourly archetype for each supported combination needed by the demo:

- food processing, day shift
- food processing, two shifts
- textiles, day shift
- textiles, two shifts
- continuous operation fallback

Profiles may be based on public data and synthetic transformations, but every profile requires a source/assumption manifest.

## Input

- sector
- shift pattern
- working days
- monthly electricity consumption
- optional shift hours

## Output

Generate an 8,760-hour load series.

Requirements:

- monthly totals reconcile with submitted values
- non-working days follow the documented rule
- no negative load
- explicit Africa/Cairo timestamps
- archetype ID and version
- confidence fixed to baseline status
- warnings describing synthetic/proxy limitations

## UI

Show the predicted profile preview in the assessment result only after the run completes.

## Scope Limits

- no clustering
- no XGBoost
- no smart-meter upload
- no optimization

### Check When Done

- each supported input maps to an archetype
- monthly reconciliation is within tolerance
- annual row count and timezone validate
- source and synthetic transformations are documented
- baseline tests pass
