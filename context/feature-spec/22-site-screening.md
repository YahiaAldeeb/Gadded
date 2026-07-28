Add GIS-based preliminary site screening.

## Input

- assessment site point
- optional site polygon
- project type
- selected geography

## Checks

Implement:

- inside selected industrial zone
- protected-area intersection
- available land-use classification
- nearest road distance
- nearest mapped substation or grid feature distance
- layer coverage check

Use projected coordinates or PostGIS geography for valid distance calculations.

## Output

Return structured `GisFinding` records with:

- code
- severity
- value and unit
- layer/source
- check time
- methodology
- limitations

## User-Facing Rules

- no matching feature means `not found in selected dataset`, not `does not exist`
- missing layer coverage returns `unknown`
- protected-area intersection may be critical
- grid distance is a screening proxy, not grid-capacity confirmation

## UI

Add the result layers to the map and provide an equivalent findings list.

## Scope Limits

- no regulatory permit conclusions
- no approval-time estimate
- no final engineering conclusion

### Check When Done

- known test sites produce expected findings
- distance and intersection methods are recorded
- coverage gaps return unknown
- map and list show the same findings
- source dates and limitations are visible
