Add constrained PV system sizing.

## Candidate Generation

Generate candidate capacities using:

- available roof area
- area-per-kW assumption
- optional target capacity
- supported capacity step
- optional budget ceiling
- regulatory capacity constraints when available

## Objective

For the first version, maximize project NPV or discounted economic value using the active assumption set.

The objective must account for:

- self-consumed electricity value
- exported electricity value
- project cost
- operating cost

## Output

Return:

- recommended capacity
- physical maximum
- evaluated capacities
- objective value for each candidate
- self-consumption for each candidate
- roof area required
- binding constraints
- reason the selected capacity won

Save the candidate comparison table as an artifact.

## Behavior

- recommendation must not automatically select the largest size
- deterministic result for frozen input/assumptions
- allow a manual target capacity comparison
- return insufficient-information when critical assumptions are missing

## Scope Limits

- no Monte Carlo
- no GIS analysis
- no regulatory LLM
- no financing scenario yet

### Check When Done

- candidate sizes respect roof constraints
- objective function has independent tests
- golden case produces an explainable recommendation
- candidate comparison is persisted
- identical inputs produce identical output
