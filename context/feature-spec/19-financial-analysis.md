Add deterministic cash and financing analysis.

## Assumptions

Resolve from the active assumption set:

- capex per kW or project-cost model
- annual O&M
- degradation
- discount rate
- tariff escalation treatment
- export compensation
- analysis period
- financing rate
- term
- down payment
- fees
- replacement costs when included

## Cash Scenario

Calculate:

- initial investment
- annual cash flows
- year-one savings
- NPV
- IRR when defined
- simple payback
- discounted payback

## Financing Scenario

Calculate:

- down payment
- monthly payment
- debt cash flows
- monthly savings versus payment
- NPV
- equity payback

## Output

Return separate scenarios for:

- cash
- finance

Clearly list inclusions, exclusions, and whether values are nominal or real.

## Scope Limits

- no random simulation
- no bank credit decision
- no live bank product scraping
- no vendor quote

### Check When Done

- NPV, IRR, amortization, and payback tests pass
- calculations use versioned assumptions
- money is persisted with appropriate precision
- undefined IRR/payback cases are handled
- result exposes assumptions and exclusions
