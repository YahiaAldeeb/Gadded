Add authentication and route protection to Gadded.

Use Supabase Auth as defined in `architecture-context.md`.

## Provider and Session

Configure the browser and server Supabase clients.

Requirements:

- secure cookie-based server sessions
- authenticated user available in server components
- no service-role key in browser code
- session refresh handled through the supported Next.js pattern

## Auth Pages

Create:

- `/sign-in`
- `/sign-up`
- `/forgot-password`

Design:

- large screens: compact two-panel layout
- left panel: Gadded identity, short value statement, text-only benefits
- right panel: centered auth form
- small screens: form only
- no oversized hero
- no gradients
- no scroll-heavy layout

## Route Behavior

- unauthenticated `/` users see the public landing page
- authenticated users can navigate to `/projects`
- protect project, assessment, result, source, and regulatory routes
- redirect unauthenticated protected requests to `/sign-in`

## Header

Replace the user-menu placeholder with:

- user email/name
- profile/account action
- sign-out action

Keep account management minimal.

### Check When Done

- server components can read the authenticated user
- protected routes redirect correctly
- service-role credentials never reach the client
- sign-in, sign-up, password reset, and sign-out work
- auth pages use Gadded design tokens
- `npm run build` passes
