Build the project assessment workspace shell. No analysis logic yet.

## Route

Create:

- `/projects/[projectId]`
- `/projects/[projectId]/assessments/[assessmentId]`

Both routes must perform server-side access checks.

## Project Page

Show:

- project name and description
- assessment list
- assessment status
- last run date
- `New Assessment` action
- empty state

## Assessment Workspace

Build a desktop-first layout with:

- top project/assessment header
- left assessment-step navigation
- central content area
- optional right context panel
- save state indicator
- current assessment status

Initial steps:

1. Project
2. Location
3. Factory Consumption
4. Site and Ownership
5. Connection and Finance
6. Review

## Access Denied

Create a reusable access-denied component with:

- lock icon
- short explanation
- link to `/projects`

## Scope Limits

- no real form fields
- no map
- no analysis run
- no calculations

### Check When Done

- inaccessible projects/assessments are blocked
- project page lists real assessment records
- workspace shell renders all steps
- current step is represented in the URL or controlled state
- layout is responsive
- `npm run build` passes
