The initial database schema is ready. Build project API routes only.

## Routes

Create endpoints for:

- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/[projectId]`
- `PATCH /api/projects/[projectId]`
- `DELETE /api/projects/[projectId]`

## Rules

Use the authenticated Supabase user.

When creating:

- require organization membership
- default a missing or blank name to `Untitled Project`
- set the current user as owner
- use the database’s existing ID strategy

When updating or deleting:

- verify access server-side
- only the project owner or organization owner may mutate
- return `403` for authenticated users without permission
- return `404` when the project is not visible to the user

## Response Shapes

Use consistent success and error contracts.

Validation errors must identify fields.

Keep this backend-only. Do not wire the project UI yet.

### Check When Done

- list/create/read/update/delete routes exist
- organization access is enforced
- owner mutation rules are enforced
- unauthenticated requests return `401`
- forbidden requests return `403`
- hidden/nonexistent resources return the agreed response
- route tests pass
- `npm run build` passes
