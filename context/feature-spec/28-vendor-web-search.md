Add evidence-grounded solar EPC vendor discovery.

## Trigger

Run vendor search only after a technical recommendation exists.

Vendor-search input:

- location
- project type
- recommended capacity
- connection model
- required studies/services
- target timeline
- optional budget range

## LLM Tooling

Use the OpenAI Responses API with web-search capability and strict structured output.

Search for companies with evidence of:

- Egyptian commercial or industrial solar services
- rooftop EPC capability
- relevant service geography
- relevant public project or service description

## Output Rules

Each vendor requires:

- company name
- website URL
- fit explanation
- services
- at least one supporting source
- retrieval date
- verification status

Optional contact details are included only when supported.

Forbidden unsupported claims:

- best
- highest quality
- licensed
- certified
- cheapest
- guaranteed
- ranked score

## Persistence and Failure

- store source evidence
- deduplicate companies
- preserve search date
- vendor-search failure must not invalidate core assessment results
- show leads as candidates to verify independently

## UI

Populate the Vendors tab with:

- project specification summary
- vendor cards
- evidence links
- search date
- verification warning

### Check When Done

- no candidate appears without evidence
- unsupported fields remain absent
- duplicate companies are merged or removed
- search output validates against the contract
- failure leaves core results available
- vendor UI avoids quality rankings
