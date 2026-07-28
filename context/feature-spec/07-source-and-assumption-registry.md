# Source and Assumption Registry

## Goal

Add the foundational data structures for versioned external sources and modeling assumptions.

## Database Models

Add:

### Source Record

- ID
- title
- publisher or authority
- source class
- source URL
- country
- geographic scope
- project-type scope
- publication date
- effective date
- retrieval date
- license
- language
- artifact path
- validation status
- superseded-by reference
- notes

### Assumption Set

- ID
- name
- version
- status: `DRAFT`, `ACTIVE`, `RETIRED`
- effective date
- created timestamp

### Assumption Value

- assumption-set ID
- key
- numeric/text/JSON value
- unit
- source-record ID when sourced
- classification:
  - `OFFICIAL`
  - `MARKET_RANGE`
  - `LITERATURE_PROXY`
  - `SYNTHETIC`
  - `DEMO`
- notes

## Admin Pages

Create simple protected pages:

- `/data-sources`
- `/assumptions`

Support:

- list records
- filter by class/status
- view details
- show freshness/effective dates

Do not add full editing workflows yet. Seed records may be loaded through migrations or scripts.

## Helpers

Create shared functions to:

- get the active assumption set
- resolve an assumption by key and version
- attach source/version metadata to a result

### Check When Done

- source and assumption models exist
- an active assumption set can be resolved
- source freshness and classification display correctly
- calculations are not yet added
- seeded demo assumptions are clearly labeled
- `npm run build` passes
