# Research and Source Plan

## Purpose

The platform is only credible when every regulatory, geospatial, financial, weather, and vendor result exposes where it came from. This file defines how sources are found, evaluated, stored, and used.

## Source Classes

### A. Authoritative

Examples:

- Egyptian regulator or ministry
- Government authority
- Official utility/distribution company
- Official law, decree, regulation, or program document
- NASA, European Commission/JRC, or official technical documentation

May support:

- Regulatory requirements
- Official process
- Published tariff
- Program terms
- Weather/PV data definitions

### B. Reliable Secondary

Examples:

- Multilateral institution
- Reputable research institution
- Peer-reviewed paper
- Established industry report

May support:

- Context
- Method selection
- Proxy assumptions
- Cross-checking

Must not silently replace an available authoritative source.

### C. Public Operational Data

Examples:

- OpenStreetMap
- Public vendor websites
- Public project references
- Public directories

May support:

- Vendor lead discovery
- Infrastructure proxies
- Map context

Absence is not proof of nonexistence.

### D. Synthetic or Demo Assumption

Used when real data is unavailable.

Must include:

- Assumption ID
- Value/distribution
- Reason
- Owner
- effective date
- Limitations
- Where it affects outputs

## Source Register Fields

```text
source_id
title
publisher_or_authority
source_class
country
geographic_scope
project_type_scope
connection_model_scope
publication_date
effective_date
retrieved_at
source_url
artifact_id
license
language
supersedes_source_id
superseded_by_source_id
validation_status
reviewer
notes
```

## Regulatory Research Workflow

1. Define one concrete question.
2. Search the responsible authority first.
3. Record candidate documents in the source register.
4. Confirm publication/effective dates.
5. Identify whether the document is current, amended, or superseded.
6. Extract relevant pages and sections.
7. Have a second teammate review the interpretation.
8. Convert deterministic conditions into versioned rules.
9. Index source text for retrieval.
10. Create a test question and expected cited answer.

### Regulatory Question Template

```text
Project type:
Connection model:
Capacity:
Location:
Ownership:
Question:
Expected responsible authority:
Evidence found:
Conflicts:
Open issue:
```

## GIS Research Workflow

For each desired layer:

1. Define the user decision the layer supports.
2. Prefer authoritative data.
3. Check license and redistribution limits.
4. Check geometry type and CRS.
5. Check geographic and temporal coverage.
6. Identify gaps and known quality issues.
7. Import through a repeatable script.
8. Validate with known locations.
9. Record source metadata.
10. Write the exact user-facing limitation.

### Initial Layer Priorities

1. Selected industrial-zone boundary
2. Protected areas
3. Basic land use
4. Roads/access
5. Publicly available substations/grid proxies
6. Administrative boundaries

Do not add a layer just because it is visually interesting.

## Weather and PV Research Workflow

### Primary Options

- NASA POWER Hourly API
- PVGIS API
- `pvlib` ModelChain

### Required Checks

- Available variables
- Spatial resolution
- Timezone
- Missing data
- API limits
- Licensing/attribution
- Reproducible caching
- Agreement between NASA POWER/PVGIS for the golden site

## Load-Profile Research Workflow

### Search Terms

- industrial hourly load profile dataset
- commercial and industrial load curves
- factory load profile clustering
- load archetype electricity
- synthetic industrial load profile
- monthly consumption to hourly load shape
- food processing factory load profile
- textile factory electricity load profile

### Evaluation Questions

- Is reuse allowed?
- Are profiles hourly or sub-hourly?
- Are they facility-level?
- Is sector metadata available?
- Are shift patterns represented?
- Can profiles be separated by facility for evaluation?
- How different is the climate/operation context from Egypt?
- What transformations are required?

### Minimum Deliverable

- Source manifest
- Normalized profiles
- Synthetic generation method
- Baseline archetypes
- Train/test split
- Metrics and limitations

## Financial Research Workflow

Research and version:

- Industrial electricity tariffs
- Export/net-metering value
- Representative system capex
- O&M
- Panel degradation
- Discount rate
- Financing rate, term, down payment, fees
- Equipment replacement assumptions
- Inflation/escalation treatment

Every value must be classified as official, observed market range, literature proxy, or demo assumption.

## Vendor Search Workflow

### Search Input

- Location
- Project type
- Recommended capacity
- Connection model
- Required services

### Evidence Requirements

A candidate requires a source that supports at least one of:

- Commercial/industrial solar service
- Rooftop EPC capability
- Service in Egypt or the relevant region
- Relevant public project
- Public contact/website

### Forbidden Unsupported Claims

- Best
- Most reliable
- Licensed
- Certified
- Lowest cost
- Highest quality
- Guaranteed timeline

### Manual Review Checklist

- Company exists
- Website belongs to the company
- Project/service evidence supports the summary
- Contact detail is public and current-looking
- No duplicate/alternate brand
- Search date recorded

## Source Freshness

- Regulatory and tariff sources: check before every formal demo/submission
- Vendor evidence: live search at run time and display search date
- Weather historical datasets: version by retrieval and requested period
- GIS layers: show source date and import date
- Model datasets: immutable manifest per model version

## Source Failure Behavior

- Source unavailable: use cached source only when its date is shown
- No evidence: return unknown/no result
- Conflicting evidence: show conflict and require verification
- Incomplete coverage: show coverage limitation
- Stale source: warn and prevent high-confidence result where material
