Generate the combined Gadded preliminary assessment report.

## Report Source

Build the report exclusively from persisted structured results and artifact references.

Do not re-run calculations during report rendering.

## Sections

1. Executive summary
2. Input snapshot
3. Overall preliminary feasibility
4. Technical recommendation
5. Energy profiles
6. Financial analysis
7. Risk and sensitivity
8. Site screening
9. Regulatory roadmap
10. Vendor candidates
11. RFQ summary
12. Sources, assumptions, and versions
13. Limitations and disclaimer

## Artifacts

Generate:

- HTML report
- PDF report
- source/assumption appendix
- chart images when required

Store artifact paths and content hashes.

## Requirements

- citations must be visible
- charts need captions and units
- report date and source freshness must be visible
- unknown and incomplete information must remain visible
- report must not imply legal, engineering, bank, grid, or vendor approval
- report can be regenerated from stored results

## UI

Enable report preview and downloads from the Report tab.

### Check When Done

- golden-case PDF renders without layout overflow
- report values match dashboard values
- citations and versions are included
- content hash is stored
- report regeneration is deterministic
- disclaimers are present
