Add hour-by-hour matching between factory consumption and PV generation.

## Input

- canonical hourly load series
- canonical hourly PV series
- retail tariff assumptions
- export compensation assumptions
- connection model

## Calculation

For every interval compute:

- self-consumed energy
- imported energy
- exported energy
- retail value avoided
- export value earned

Use the canonical equations in `data-contracts.md`.

## Summary Metrics

Return:

- annual load
- annual PV generation
- annual self-consumed energy
- annual import
- annual export
- self-consumption ratio
- self-sufficiency ratio
- monthly summaries

## Validation

Before matching:

- check identical timezone
- check identical frequency
- detect missing timestamps
- detect duplicates
- verify units
- reject incompatible series

## Scope Limits

- one candidate PV size at a time
- no search over sizes
- no NPV or loan calculations
- no Monte Carlo

### Check When Done

- interval equations pass unit tests
- annual energy balances reconcile
- invalid/misaligned series are rejected
- summary metrics match hourly values
- output uses the shared contract
