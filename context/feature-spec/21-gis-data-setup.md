Set up the geospatial data layer for the selected proof-of-concept locations.

## Scope

Only import layers required for the selected industrial zones/governorates.

Initial layer types:

- administrative boundaries
- industrial-zone boundaries
- protected areas
- land use when available
- roads/access
- public grid/substation proxies when available

## Source Manifest

For every layer store:

- source name
- source URL
- license
- source date
- retrieval/import date
- geographic coverage
- geometry type
- CRS
- known limitations

## Import Pipeline

Create repeatable scripts to:

- download or read source data
- validate geometry
- transform CRS
- load into PostGIS
- create spatial indexes
- record import metadata

## Test Fixtures

Add known points and expected spatial relationships.

## Scope Limits

- no user-facing findings
- no claim of authoritative grid completeness
- no nationwide import
- no automatic source updates

### Check When Done

- selected layers import from a clean database
- invalid geometries are handled
- source metadata is stored
- spatial indexes exist
- known-point fixtures pass
- incomplete coverage is documented
