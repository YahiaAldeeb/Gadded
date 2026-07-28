Add deterministic regulatory rules and permit-path outputs.

## Rule Model

Create versioned rules containing:

- rule ID
- title
- effective date
- project type
- connection model
- geography
- condition expression
- finding template
- severity
- required documents
- dependencies
- authority
- supporting source records
- status: `DRAFT`, `ACTIVE`, `RETIRED`

## Rule Engine

Evaluate rules against the frozen assessment input and GIS findings.

Support:

- equality and membership checks
- numeric thresholds
- missing-value checks
- boolean combinations
- GIS finding conditions

Do not execute arbitrary code stored in the database.

## Outputs

Produce structured regulatory findings with:

- conclusion
- severity
- explanation template data
- authority
- documents
- dependencies
- rule IDs
- citations
- confidence
- verification-required flag
- duration range only when sourced or explicitly rule-based

## Admin/Test Tools

Add a protected rule-test view or script using fixed scenarios.

## Scope Limits

- no natural-language rule authoring
- no LLM eligibility decision
- no automated permit submission

### Check When Done

- active rules evaluate deterministically
- unsupported/missing facts produce review or insufficient-information results
- each result exposes rule IDs and supporting sources
- rule expressions cannot execute code
- threshold and missing-data tests pass
