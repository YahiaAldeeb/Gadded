Build the reusable application shell for Gadded.

## Header

Create `components/layout/app-header.tsx`.

Requirements:

- Gadded logo/name on the left
- navigation links:
  - Projects
  - New Assessment
  - Regulatory Library
  - Data Sources
- language switch placeholder
- user-menu placeholder
- responsive menu for smaller screens
- surface background with subtle bottom border

## Main Layout

Create `components/layout/app-shell.tsx`.

Requirements:

- full viewport minimum height
- fixed or sticky header
- centered content container
- page-title slot
- page-actions slot
- main content slot
- optional right context panel slot

## Landing Page

Create a minimal public landing page with:

- headline centered on whether a solar project can be built, financed, and approved
- three value areas:
  - Can I build?
  - Should I invest?
  - What happens next?
- primary action to start an assessment
- preliminary-assessment disclaimer

Do not add authentication behavior yet.

## Scope Limits

- no project data
- no analysis workflow
- no maps
- no charts
- no final marketing animation

### Check When Done

- header and shell are reusable
- landing page uses the shell correctly
- layout is responsive
- UI uses design tokens only
- no auth or API behavior is added
- `npm run build` passes
