# Gadded

## Product Name

**Gadded**

## Hackathon framing

Built for AI Empower Egypt 2026 (Renewable Energy Using AI). The Phase 1 deliverable is a
**notebook-first Python proof of concept** (`gadded.ipynb` + `src/gadded/`) plus one documentation
PDF — not a shipped web platform. The sections below describe the full product vision; the PoC
implements one end-to-end vertical slice of it on a single golden case (10th of Ramadan food-processing
factory). See `architecture-context.md` and `implementation-plan.md` for the actual build scope.

## Overview

Gadded is a bilingual decision-support platform for Egyptian factories, SMEs, and renewable-energy developers. It turns basic project information, a location, and electricity-consumption data into a preliminary solar-project assessment covering:

- Site and regulatory feasibility
- Recommended PV system size
- Expected generation and self-consumption
- Financial return and uncertainty
- Required permits, authorities, and likely blockers
- Suggested solar EPC vendors found through grounded web search
- A standardized request for quotation (RFQ)

The platform answers three connected questions:

1. **Can I legally and practically build the project here?**
2. **Should I invest, and what system size makes sense?**
3. **What actions, permits, and vendors should I pursue next?**

## Primary Users

### Factory and SME Owner

Needs an independent assessment before requesting quotations from installers.

### Renewable-Energy Developer

Needs a fast preliminary screening of location, grid proximity, restrictions, approvals, and expected economics.

### Government or Program Officer

Needs a consistent way to screen candidate projects and identify common deployment blockers.

## Initial Proof-of-Concept Scope

The first version must remain narrow enough to validate end to end.

- Project type: industrial rooftop solar
- User type: Egyptian factory or SME owner
- Locations: two selected industrial zones or governorates
- Connection models: self-consumption and net metering
- Industrial sectors: food processing and textiles
- Language: English first, Arabic-ready and RTL-compatible
- Vendor coverage: Egypt-wide search, filtered by evidence of commercial or industrial solar work
- Report type: preliminary assessment, not legal, engineering, or financial advice

Ground-mounted solar farms, detailed structural analysis, authoritative grid-capacity confirmation, and automated permit submission are future phases.

## Core User Flow

1. User signs in or starts a temporary assessment.
2. User creates a solar assessment.
3. User selects the site on a map or enters coordinates/address.
4. User provides factory, consumption, shifts, roof area, ownership, project, budget, and financing information.
5. The platform validates required inputs and lists missing information.
6. GIS pre-screening checks the selected location against available spatial layers.
7. The regulatory engine retrieves relevant official material and applies deterministic eligibility rules.
8. The load engine estimates an hourly factory-consumption profile.
9. The solar engine creates hourly PV-generation profiles for candidate system sizes.
10. The optimizer selects the size that maximizes financial value within roof and regulatory constraints.
11. The financial engine calculates savings, cash flow, NPV, IRR, payback, loan comparison, and uncertainty.
12. The system generates a cited regulatory roadmap and preliminary approval-time range.
13. The vendor agent searches the live web for relevant EPC companies and preserves source evidence.
14. The platform generates a standardized RFQ using the selected system specification.
15. The user reviews and downloads the combined assessment report.

## Product Modules

### Assessment Intake

- Project type and connection model
- Map-based location selection
- Factory sector and operating pattern
- Monthly or annual electricity consumption
- Roof or land area
- Ownership and existing documents
- Budget, financing preference, and target timeline

### Site and GIS Screening

- Point-in-polygon restriction checks
- Industrial-zone and land-use classification
- Protected-area intersection
- Distance to available grid, road, and substation datasets
- Approximate usable area and site warnings
- Source and freshness metadata for every layer

### Regulatory Copilot

- Official-document ingestion and versioning
- Retrieval-augmented question answering
- Deterministic rules for eligibility and thresholds
- Required permits, documents, sequence, authorities, and dependencies
- Confidence, source date, citation, and verification warnings
- Plain-language Arabic/English explanation

### Load-Profile Estimation

- Industrial load archetypes
- Predicted hourly consumption from sector, shifts, and monthly kWh
- Confidence score and selected archetype
- Manual correction option for users with interval data

### Solar Generation

- Hourly weather and irradiance retrieval
- PV generation modeled with `pvlib`
- Candidate system sizes constrained by available area
- Loss, orientation, temperature, and degradation assumptions
- Cached weather profiles for repeatable demos

### Sizing Optimization

- Hour-by-hour matching of consumption and generation
- Self-consumed, imported, and exported energy
- Search across system sizes
- Objective based on NPV or total economic value
- Constraints from area, budget, connection model, and regulations

### Finance and Risk

- Capital and operating cost assumptions
- Annual bill savings
- Cash versus financed scenarios
- NPV, IRR, and simple/discounted payback
- Monte Carlo distribution
- Sensitivity and primary risk drivers
- Clearly labeled assumptions and effective dates

### Vendor Discovery and RFQ

- LLM with live web-search capability
- Evidence-grounded EPC shortlist
- No unsupported or invented vendors
- Search date and source links preserved
- Vendor-fit explanation, not unverified quality ranking
- Standardized RFQ generated from the recommended design

## Main Inputs

### User-Provided

- Project name
- Project type
- Latitude/longitude or address
- Governorate or industrial zone
- Factory sector
- Working days and shift schedule
- Monthly electricity consumption in kWh
- Optional monthly bill value
- Optional hourly smart-meter CSV
- Available rooftop area in square meters
- Roof ownership or authorization status
- Existing connection voltage, when known
- Connection model
- Target capacity, when known
- Budget ceiling
- Cash or finance preference
- Target commissioning date
- Existing permits or technical studies

### Automatically Retrieved or Maintained

- Hourly solar and meteorological data
- PV technology assumptions
- Electricity tariff schedules
- Export/net-metering compensation rules
- Regulatory documents and effective dates
- GIS restriction and infrastructure layers
- Financing assumptions
- Vendor web-search results
- Model versions and calculation assumptions

## Main Outputs

### Feasibility

- Likely feasible
- Feasible with conditions
- High regulatory risk
- Potentially ineligible
- Insufficient information

### Technical

- Recommended PV capacity
- Roof area required
- Annual PV production
- Self-consumption ratio
- Self-sufficiency ratio
- Imported and exported energy
- Approximate grid/infrastructure distances
- Key technical assumptions

### Financial

- Estimated project cost
- Annual savings
- Monthly cash-flow comparison
- NPV
- IRR
- Payback distribution
- Probability of meeting a target payback
- Sensitivity drivers

### Regulatory

- Applicable regulatory path
- Permits and approvals
- Authorities involved
- Required documents
- Approval sequence and dependencies
- Preliminary approval-time range
- Major issues and missing information
- Source citations and verification notices

### Execution Support

- Vendor shortlist with evidence
- Vendor contact and service details when publicly available
- Questions to ask vendors
- Vendor-ready project specification
- Downloadable RFQ
- Downloadable combined assessment report

## Non-Goals for the Proof of Concept

- Legal approval or guarantee
- Structural roof certification
- Authoritative grid-capacity reservation
- Installer certification or quality guarantee
- Automatic permit submission
- Final engineering design
- Bank credit decision
- Nationwide authoritative GIS coverage
- Training a model on confidential Egyptian factory data

## Success Criteria

1. A user can complete an assessment for the selected industrial zones.
2. The system produces a valid hourly load profile from simple factory inputs.
3. The system produces a valid hourly PV profile from location and system size.
4. The optimizer recommends a capacity based on self-consumption and project economics.
5. The report includes financial ranges rather than only a single deterministic payback.
6. Regulatory answers cite retrieved source material and separate rules from LLM explanation.
7. GIS outputs expose source, coverage, and freshness limitations.
8. Every displayed vendor is supported by a retrieved web source.
9. The full demo runs from inputs to downloadable report without manual code execution.
10. The team can explain which components are ML, physics, optimization, simulation, rules, and LLM orchestration.
