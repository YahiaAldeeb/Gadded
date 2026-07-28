Add the assessment intake forms and draft persistence.

## Project Step

Fields:

- assessment name
- project type fixed to industrial rooftop solar for the PoC
- connection model:
  - self-consumption
  - net metering

## Factory Consumption Step

Fields:

- sector:
  - food processing
  - textiles
- twelve monthly consumption values in kWh
- working days per week
- shift pattern:
  - day shift
  - two shifts
  - continuous
- optional shift start/end
- optional hourly CSV upload placeholder

## Site and Ownership Step

Fields:

- available rooftop area in m²
- ownership status
- roof type
- target capacity in kW, optional
- connection voltage, optional
- existing studies or permits, optional metadata only

## Connection and Finance Step

Fields:

- budget ceiling, optional
- preference:
  - cash
  - finance
  - compare
- target payback, optional
- target commissioning date, optional

## Behavior

- validate with the shared assessment contract
- autosave draft values
- preserve incomplete drafts
- distinguish required and optional inputs
- show unit labels
- show field-specific errors
- prevent unsupported project types

Do not freeze the input or start analysis yet.

### Check When Done

- all supported inputs can be entered
- twelve monthly values validate correctly
- draft state survives refresh
- unsupported enum values are rejected server-side
- form values match the shared contract
- no analysis runs are created
- `npm run build` passes
