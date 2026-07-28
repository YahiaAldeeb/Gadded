Add grounded regulatory retrieval and cited explanation.

## Retrieval Input

- project type
- connection model
- capacity
- location/geography
- ownership status
- user question or predefined regulatory topic

## Retrieval

Filter by metadata before semantic ranking:

- effective/current status
- geography
- project type
- connection model
- language when relevant

Return passages with:

- authority
- document title
- page/section
- effective/publication date
- source URL
- excerpt
- relevance score

## LLM Explanation

Use the OpenAI Responses API with structured output.

The model may:

- summarize retrieved evidence
- explain uncertainty
- identify missing information
- produce plain-language English text

The model may not:

- invent permit names
- invent thresholds
- invent authorities
- invent durations
- make an eligibility decision

Every factual regulatory statement needs a citation.

## Evaluation

Create test questions with expected relevant documents and citation completeness checks.

## Scope Limits

- no deterministic rules
- no final feasibility status
- no Arabic generation yet

### Check When Done

- retrieval filters exclude irrelevant/superseded documents
- explanations contain source citations
- unsupported questions return insufficient information
- prompt-injection content is ignored
- evaluation fixtures pass
