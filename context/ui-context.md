# UI Context

> **DEFERRED for the hackathon PoC.** There is no web app in Phase 1. This file is the
> full-product UI spec, kept as reference. What still applies now: the notebook and HTML
> report should follow the chart rules (labels, units, text summary under each chart),
> the status system (icon + text, never color alone), and the persistent preliminary-assessment
> disclaimer. Ignore the navigation, screens, auth, and theming sections until the web build.

## Product Character

The interface should feel:

- Trustworthy
- Analytical
- Clear
- Solar and sustainability-oriented
- Appropriate for factory owners, engineers, developers, and officials
- Modern without looking like a consumer lifestyle application

The product is desktop-first because the main tasks involve maps, multi-step forms, charts, evidence, and reports. It remains responsive for tablets and mobile review.

## Language and Direction

- English and Arabic are first-class product languages.
- The initial implementation may ship English content first.
- Components must support RTL from the start.
- Do not concatenate translated fragments.
- Dates, numbers, units, and currencies must be locale-aware.
- Technical abbreviations such as kW, kWh, NPV, and IRR remain recognizable in both languages.

## Theme

Light-first with optional dark mode later.

All product colors must be CSS custom properties mapped to Tailwind tokens.

| Role | Token | Suggested value |
| --- | --- | --- |
| Page background | `--bg-base` | `#F6F7F2` |
| Surface | `--bg-surface` | `#FFFFFF` |
| Elevated surface | `--bg-elevated` | `#FFFFFF` |
| Muted surface | `--bg-muted` | `#EEF1E8` |
| Primary text | `--text-primary` | `#17211B` |
| Secondary text | `--text-secondary` | `#526159` |
| Muted text | `--text-muted` | `#7A877F` |
| Default border | `--border-default` | `#DCE2D9` |
| Solar accent | `--accent-solar` | `#E7A927` |
| Solar soft | `--accent-solar-soft` | `#FFF4D5` |
| Energy green | `--accent-energy` | `#1E7A52` |
| Energy soft | `--accent-energy-soft` | `#E3F4EA` |
| Technical navy | `--accent-technical` | `#183B56` |
| AI accent | `--accent-ai` | `#6255D9` |
| Success | `--state-success` | `#237A4B` |
| Warning | `--state-warning` | `#B76A00` |
| Critical | `--state-critical` | `#B93A3A` |
| Unknown | `--state-unknown` | `#667085` |

Final colors should be checked for accessible contrast before implementation.

## Typography

Use a bilingual family with strong Arabic and Latin support.

Recommended:

- UI: IBM Plex Sans Arabic with Latin fallback, or Noto Sans Arabic/Noto Sans
- Numbers and code: Geist Mono or IBM Plex Mono

Hierarchy:

- Display: product landing only
- H1: page title
- H2: section title
- H3: card/report subsection
- Body: explanations
- Label: forms and metrics
- Mono/tabular: hourly values, coordinates, model/run IDs

Use tabular numbers for financial and energy metrics.

## Radius and Elevation

| Context | Class |
| --- | --- |
| Inputs and small controls | `rounded-xl` |
| Cards and result panels | `rounded-2xl` |
| Wizards, modals, and major report panels | `rounded-3xl` |

Use borders before shadows. Result dashboards should feel precise, not overly floating.

## Main Application Layout

### Navigation

- Logo and working product name
- Projects
- New assessment
- Regulatory library
- Data sources
- User/organization menu
- Language switch

### Assessment Workspace

Desktop layout:

- Left: assessment step navigation
- Center: active form or result
- Right: contextual help, missing information, assumptions, or source summary

Result layout:

- Summary header
- Overall feasibility status
- Metric strip
- Tabs:
  - Technical
  - Financial
  - Site
  - Regulations
  - Vendors
  - Report

## Core Screens

### 1. Landing

- Main question: "Can this solar project be built, financed, and approved?"
- Product explanation
- Three value pillars:
  - Can I build?
  - Should I invest?
  - What happens next?
- Start assessment CTA
- Disclaimer

### 2. Project Dashboard

- Assessments by status
- Recent runs
- Saved reports
- Warnings for outdated assumptions or source data

### 3. New Assessment Wizard

Steps:

1. Project
2. Location
3. Factory consumption
4. Site and ownership
5. Connection and finance
6. Review

Requirements:

- Autosave
- Visible required/optional labels
- Inline validation
- Ability to upload interval CSV
- Clear example values
- Summary before analysis starts

### 4. Map and Site Screen

- Search/address control
- Map pin selection
- Coordinate display
- Optional site polygon
- Available GIS layers
- Site findings list
- Source coverage notice
- Legend for clear, warning, critical, and unknown

Absence of mapped infrastructure must never display as "none exists." Show "not found in the selected dataset."

### 5. Analysis Progress

Stages:

- Validating inputs
- Loading weather
- Estimating factory load
- Screening site
- Retrieving regulations
- Optimizing PV size
- Simulating financial risk
- Searching vendors
- Generating report

Show progress without inventing time estimates.

### 6. Results Summary

Header:

- Project and location
- Analysis date
- Result status
- Report download
- Rerun with changed assumptions

Metric cards:

- Recommended capacity
- Annual generation
- Self-consumption
- Estimated annual savings
- Median payback
- Approval-time range

Main issues:

- Top three blockers or uncertainties
- Missing information
- Source freshness warnings

### 7. Technical Tab

- Load vs PV chart
- Monthly production and consumption
- Candidate-size comparison
- Self-consumption and self-sufficiency
- Roof-area use
- Binding constraints
- Assumption drawer

### 8. Financial Tab

- Cash and financed scenario cards
- Annual cash-flow chart
- NPV/IRR/payback
- Monte Carlo payback distribution
- Sensitivity ranking
- Assumptions and exclusions

Never hide assumptions behind an info icon only.

### 9. Regulatory Tab

- Plain-language summary
- Permit roadmap
- Authority cards
- Required-document checklist
- Approval dependencies
- Estimated duration basis
- Citations expandable by finding
- Confidence and verification-required labels
- Ask-the-copilot input restricted to the current project context

### 10. Vendor Tab

- Search date
- Project specification summary
- Vendor candidates
- Evidence/source links
- Service and location fit
- Contact details when verified
- Manual verification warning
- Generate/download RFQ

Do not display stars, rankings, or "best vendor" claims in the proof of concept.

### 11. RFQ Preview

- Owner/project details
- Site details
- Requested capacity
- Expected generation
- Required services
- Regulatory/technical studies
- Vendor response table
- Commercial quote fields
- Delivery timeline
- Warranty and maintenance questions

### 12. Source and Assumptions Drawer

Accessible from every result.

Contains:

- Tariff version
- Weather source and retrieval date
- PV assumptions
- Load-model version
- GIS layers
- Regulatory document dates
- Finance assumptions
- LLM/prompt version
- Known limitations

## Status System

### Likely Feasible

Use success icon, label, and text explanation.

### Feasible With Conditions

Use warning icon and list conditions.

### High Risk

Use critical icon and name the blockers.

### Potentially Ineligible

Use critical treatment but state "preliminary."

### Insufficient Information

Use neutral/unknown style and show required next inputs.

Color is supportive; icons and text are mandatory.

## Charts

- Every axis has a label and unit.
- Tooltips include timestamp/month and values.
- Provide a textual summary under every important chart.
- Avoid 3D charts.
- Use line/area for hourly profiles.
- Use bars for monthly comparisons.
- Use histogram or cumulative curve for payback uncertainty.
- Use horizontal bars for sensitivity drivers.

## Maps

- Use MapLibre.
- Keep basemap muted so analytical layers remain readable.
- Provide layer toggles and source metadata.
- Do not render sensitive/restricted data that is not legitimately public.
- Provide non-map list equivalents for accessibility and auditability.

## Empty and Error States

- Explain what is missing.
- Provide a specific recovery action.
- Preserve submitted inputs after failure.
- Distinguish:
  - external source unavailable
  - no evidence found
  - source does not cover site
  - model low confidence
  - invalid user input

## Disclaimers

Display a persistent but non-obstructive notice:

"This is a preliminary decision-support assessment. Verify regulatory, engineering, grid, vendor, and financing information with the responsible authorities and qualified professionals."
