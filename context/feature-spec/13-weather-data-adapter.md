Add the hourly weather and irradiance data adapter.

## Sources

Implement adapters for:

- NASA POWER Hourly API
- one cached fixture for the golden demo site

PVGIS may be added as a secondary adapter only if the first adapter is complete.

## Input

- latitude
- longitude
- start/end year or representative period
- required weather variables
- desired output timezone

## Output

Return a canonical hourly weather series with explicit units.

Include:

- timestamp
- GHI
- DNI when available
- DHI when available
- ambient temperature
- wind speed when used
- source metadata
- retrieval date
- missing-data warnings

## Behavior

- validate response units
- normalize timestamps
- convert to Africa/Cairo display timezone
- cache raw and normalized responses
- retry bounded transient failures
- use recorded fixtures in standard tests
- fail visibly when required variables are unavailable

## Scope Limits

- no PV generation
- no weather ML forecasting
- no user-facing charts

### Check When Done

- golden-site fixture loads
- live adapter can be run through an opt-in integration test
- units and timezone are validated
- cache metadata is preserved
- missing data produces warnings/errors
- standard CI makes no live external call
