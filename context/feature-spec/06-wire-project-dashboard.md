Wire the project dashboard to the real project APIs.

## Project Dashboard

Create `/projects` as a server-rendered page.

Show:

- project name
- description
- status
- assessment count placeholder
- last updated date
- open action
- rename action
- archive/delete action

Add:

- empty state
- loading skeleton
- `New Project` action

## Project Dialogs

Create dialogs for:

### Create Project

- name
- optional description
- submit to project API
- navigate to project after success

### Rename Project

- prefilled project name
- Enter submits
- refresh after success

### Archive or Delete

- destructive confirmation
- show project name
- prevent accidental double submission

## Data Fetching

- initial project list is fetched server-side
- mutations use client actions/hooks
- do not fetch the initial project list again on mount
- refresh server data after successful mutation

## Scope Limits

- no assessment creation yet
- no charts
- no collaboration
- no model or AI calls

### Check When Done

- projects load from the real database
- create navigates to the new project
- rename updates the dashboard
- archive/delete updates the dashboard
- empty and error states work
- `npm run build` passes
