# Database Schema and Data Layer

## Goal

Create the initial PostgreSQL schema for Gadded using Supabase migrations.

Enable:

- PostGIS
- pgvector

## Core Models

Add tables for:

### Organization

- ID
- name
- timestamps

### Organization Member

- organization ID
- Supabase user ID
- role: `OWNER`, `MEMBER`
- unique organization/user constraint

### Project

- organization ID
- owner user ID
- name
- optional description
- status: `DRAFT`, `ACTIVE`, `ARCHIVED`
- timestamps
- indexes on organization, owner, status, and creation date

### Assessment

- project ID
- name
- project type
- connection model
- status: `DRAFT`, `READY`, `ANALYZING`, `COMPLETED`, `FAILED`
- location point using PostGIS geography
- timestamps

### Assessment Input Snapshot

- assessment ID
- immutable JSON input
- content hash
- created timestamp

### Analysis Run

- assessment ID
- status: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`
- current stage
- progress percentage
- error code/message
- input snapshot hash
- code version
- assumption-set version
- timestamps

### Generated Artifact

- assessment/run ID
- type: `REPORT`, `RFQ`, `HOURLY_SERIES`, `MODEL_OUTPUT`
- object-storage path
- content hash
- timestamp

Do not add regulatory, GIS, vendor, or financial detail tables yet.

## Row-Level Security

Add policies so:

- users can access only organizations they belong to
- project and assessment access follows organization membership
- users cannot alter frozen input snapshots
- browser clients cannot write completed analysis results directly

## Database Client

Create typed server and browser database helpers.

### Check When Done

- PostGIS and pgvector are enabled
- all listed tables exist
- relations and indexes are correct
- row-level security protects user-owned data
- input snapshots are immutable through normal client access
- migrations run from a clean database
- generated types compile
- `npm run build` passes
