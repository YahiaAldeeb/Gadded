Build the assessment results dashboard using structured completed-run data.

## Summary Header

Show:

- assessment/project name
- location
- analysis date
- preliminary feasibility status
- rerun action
- report placeholder action

## Metric Strip

Show:

- recommended capacity
- annual generation
- self-consumption ratio
- annual savings
- median payback
- preliminary approval-time range when available

## Tabs

Create:

- Technical
- Financial
- Site
- Regulations
- Vendors
- Report

The Vendors and Report tabs may show controlled placeholders until later specs.

## Technical Tab

- load versus PV chart
- monthly energy comparison
- candidate-size table
- binding constraints
- assumptions

## Financial Tab

- cash and finance cards
- NPV, IRR, payback
- cash-flow chart
- Monte Carlo distribution
- sensitivity chart

## Site Tab

- map findings
- list equivalent
- source coverage and freshness

## Regulations Tab

- summary
- permit roadmap
- authorities
- required documents
- citations
- confidence and verification labels

## Source Drawer

Add a reusable drawer listing all data, model, assumption, and prompt versions.

### Check When Done

- dashboard uses persisted structured results
- charts include units and text summaries
- unknown/warning states are explicit
- citations open the correct source metadata
- results remain usable without map interaction
- `npm run build` passes
