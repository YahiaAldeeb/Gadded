Add Arabic localization and right-to-left support to Gadded.

## Localization Foundation

Add a translation framework that supports server and client components.

Requirements:

- English and Arabic locales
- locale-aware routes or stored user preference
- language switch in the header
- no concatenated translated fragments
- locale-aware dates, percentages, units, and EGP values

## RTL

When Arabic is active:

- set document direction to RTL
- use logical CSS properties
- mirror navigation and step layout appropriately
- keep charts numerically readable
- keep map controls usable
- preserve technical abbreviations such as kW, kWh, NPV, and IRR

## Content Scope

Translate:

- navigation
- assessment wizard
- validation
- progress stages
- result labels
- statuses
- warnings
- disclaimers
- vendor verification notices
- RFQ/report static labels

Regulatory source excerpts remain in their original language with optional translated explanation.

## Fonts

Use the bilingual font choice in `ui-context.md`.

## Scope Limits

- no automatic translation of source documents
- no Arabic speech interface
- no dialect-specific copy in the first version

### Check When Done

- all primary flows work in English and Arabic
- no major layout overflow in RTL
- units and numbers remain clear
- source citations preserve original document metadata
- PDFs support Arabic text correctly
- `npm run build` passes
