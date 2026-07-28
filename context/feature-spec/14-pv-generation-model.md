Add deterministic hourly PV generation using `pvlib`.

## Input

- site coordinates
- weather dataset
- system capacity in kW
- tilt
- azimuth
- module/inverter or simplified system assumptions
- system-loss percentage
- model version

## Implementation

Use `pvlib` ModelChain or a documented equivalent.

Generate:

- hourly AC power in kW
- hourly energy in kWh
- annual generation
- monthly generation
- performance assumptions
- warnings

## Defaults

Resolve defaults from the active assumption set.

Do not hardcode:

- tilt
- azimuth
- system loss
- module efficiency
- temperature parameters

## Validation

Add:

- zero generation at night
- non-negative output
- capacity sanity check
- annual-yield range warning
- known reference-site fixture
- reproducible result from the same weather and assumptions

## Scope Limits

- do not call this machine learning
- no sizing optimization
- no load matching
- no financial calculations

### Check When Done

- hourly PV output is produced for the golden site
- output units and timestamps are correct
- model assumptions are attached
- annual/monthly totals reconcile
- validation tests pass
- model version is stored
