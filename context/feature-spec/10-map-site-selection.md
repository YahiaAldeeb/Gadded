Add location selection and the base map to the assessment wizard.

## Map

Use MapLibre GL JS.

Requirements:

- address search field
- click map to place a site point
- draggable site marker
- latitude/longitude display
- optional governorate and industrial-zone fields
- map attribution
- muted basemap matching Gadded’s UI

## Persistence

Save:

- latitude
- longitude
- normalized address when available
- governorate
- industrial zone

Store the site as PostGIS geography on the assessment.

## Coverage Notice

Add a visible notice explaining:

- mapped data may be incomplete
- the point is used for preliminary screening
- authoritative site and grid confirmation is still required

## Accessibility

Provide a non-map coordinate input fallback.

Keyboard users must be able to enter coordinates directly.

## Scope Limits

- no protected-area layers
- no grid-distance calculations
- no GIS screening
- no vendor search

### Check When Done

- selecting or entering a location updates the draft
- saved coordinates reload correctly
- invalid coordinates are rejected
- map attribution is visible
- direct coordinate input works without the map
- `npm run build` passes
