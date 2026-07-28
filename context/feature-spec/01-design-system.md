Read `AGENTS.md` before starting.

We are adding Gadded’s design system and UI primitives.

Install and configure `shadcn/ui`.

Add these shadcn components:

- Button
- Card
- Dialog
- Input
- Label
- Select
- Tabs
- Textarea
- ScrollArea
- Sheet
- Tooltip
- Progress
- Alert
- Badge
- Table
- Skeleton

Do not modify generated `components/ui/*` files after installation.

Install:

- `lucide-react`
- the selected bilingual font packages if they are not loaded through `next/font`

Create `lib/utils.ts` with a reusable `cn()` helper.

## Theme

Implement the CSS variables defined in `ui-context.md`.

Requirements:

- light-first analytical interface
- solar-gold accent
- energy-green accent
- technical navy for charts and structured information
- visible success, warning, critical, and unknown states
- all product colors exposed through CSS custom properties
- no hardcoded product hex values in app components
- styles must support future RTL layout

## Base Patterns

Create app-level examples for:

- metric card
- status badge with icon and text
- source/freshness badge
- warning panel
- empty state
- loading state

Do not place product-specific logic inside shadcn primitives.

### Check When Done

- all installed components import without errors
- `cn()` works
- the Gadded theme tokens are available
- no raw product colors appear in app components
- status meaning does not rely on color alone
- no default shadcn styling conflicts with the Gadded theme
- `npm run build` passes
