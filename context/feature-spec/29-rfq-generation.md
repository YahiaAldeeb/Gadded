Generate a standardized request for quotation from the completed assessment.

## RFQ Input

Use persisted structured data:

- owner/project details
- site coordinates/address
- project type
- recommended capacity
- available roof area
- expected annual generation
- target self-consumption
- connection model
- required technical/regulatory studies
- target date
- vendor response requirements

## RFQ Sections

Generate:

1. Project overview
2. Site information
3. Requested PV system
4. Required scope of services
5. Grid and regulatory responsibilities
6. Equipment and design information requested
7. Warranty and O&M questions
8. Commercial quote table
9. Delivery schedule
10. Required evidence and references

## Generation

The RFQ structure is deterministic.

An LLM may improve wording but must not change numeric values or introduce unsupported requirements.

## UI

Add:

- RFQ preview
- editable owner/company fields
- copy text
- download document
- vendor-specific duplicate option

## Scope Limits

- no email sending
- no quote comparison
- no vendor negotiation
- no legal contract terms

### Check When Done

- RFQ uses persisted recommendation values
- numeric fields match the assessment
- unsupported requirements are not invented
- RFQ can be regenerated
- download works
- vendor search is optional
