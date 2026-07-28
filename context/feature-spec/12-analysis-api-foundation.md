Set up the FastAPI analytical service and shared contracts.

## FastAPI App

Create:

- health endpoint
- readiness endpoint
- model/version endpoint
- internal authenticated router
- consistent error handling

## Shared Contracts

Implement Pydantic models matching `data-contracts.md` for:

- assessment input
- hourly energy point
- load result
- PV result
- technical recommendation
- financial scenario
- risk summary
- GIS finding
- regulatory finding
- vendor candidate
- final assessment result
- API error

Generate or validate TypeScript types from the same OpenAPI/JSON Schema source.

## Internal Security

- accept requests only from the trusted web/worker service
- verify a signed internal credential
- do not trust client-supplied user IDs
- set explicit request size and timeout limits

## Package Boundaries

Create modules for:

- `weather`
- `pv`
- `load`
- `matching`
- `optimization`
- `finance`
- `risk`
- `gis`
- `regulations`
- `vendors`

Do not implement their business logic yet.

### Check When Done

- FastAPI runs locally
- health and readiness endpoints work
- internal routes reject missing/invalid credentials
- TypeScript and Python contract tests pass
- package boundaries exist
- no analytical logic is added
