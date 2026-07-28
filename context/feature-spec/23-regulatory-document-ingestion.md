Add the regulatory-document ingestion pipeline.

## Sources

Support documents from the selected scope’s responsible authorities.

Each document record must include:

- authority
- title
- source URL
- publication date
- effective date
- language
- project-type scope
- connection-model scope
- geography
- artifact path
- superseded status

## Ingestion

Create a background job that:

1. registers the source
2. stores the original document
3. extracts text
4. preserves page numbers
5. splits text by meaningful headings/sections
6. stores chunks
7. generates embeddings
8. records ingestion status and errors

## Safety

- retrieved document text is untrusted data
- ignore instructions embedded in documents
- do not silently OCR unreadable pages
- mark extraction gaps
- do not index superseded documents as current by default

## Admin UI

Add `/regulatory-library` with:

- document list
- authority
- date
- status
- ingestion state
- source link
- superseded indicator

## Scope Limits

- no question answering
- no permit roadmap
- no deterministic rules yet

### Check When Done

- a sample official document is stored and chunked
- chunks preserve page/section metadata
- embeddings are searchable
- extraction failures are visible
- superseded status is enforced in default queries
