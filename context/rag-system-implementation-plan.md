# RAG System Swap (LLM-based Retrieval over Regulatory Excerpts)

Swap the placeholder TF-IDF retrieval in `src/gadded/regulatory.py` with an evidence-grounded LLM RAG retrieval system that uses the current LLM model (Groq client) to evaluate semantic relevance of context (`text` field in `data/regulations/excerpts.json`) for queries, while retaining TF-IDF as a zero-dependency offline fallback.

## User Review Required

> [!IMPORTANT]
> **Deterministic Feasibility Principle Maintained**: The LLM RAG system retrieves regulatory excerpt context based on semantic relevance to the query. The deterministic rule engine (`evaluate_rules`) continues to evaluate official feasibility rules and produce conclusions deterministically. The LLM never makes the final legal or technical status decision. We could rely on the LLM to make this decision, but we have chosen to keep the rule engine deterministic and leave the final decision to human reviewers.

> [!NOTE]
> **Fallback Mechanism**: When `GROQ_API_KEY` or `client` is unavailable (e.g., offline environments, standard unit test runs), `retrieve()` gracefully falls back to TF-IDF cosine similarity to ensure zero test breakages and offline usability. Very good approach for rapid prototyping.

## Proposed Changes

### Core Regulatory Module

#### [MODIFY] [regulatory.py](../src/gadded/regulatory.py)

- Update `retrieve(query: str, corpus: RegulatoryCorpus, top_k: int = 3, client: OpenAI | None = None, model: str | None = None) -> list[tuple[dict, float]]`:
  - When `client` is provided or `GROQ_API_KEY` is present in `os.environ`:
    - Format a prompt containing the user `query` and all excerpt items from `corpus.excerpts` (using the `text` field as the context).
    - Request the LLM (default `llama-3.3-70b-versatile` or `openai/gpt-oss-120b` with `response_format={"type": "json_object"}`) to score relevance between `0.0` and `1.0` for each excerpt ID.
    - Parse scores, rank `corpus.excerpts` descending by LLM relevance score, and return top `top_k` as `(excerpt, score)` tuples.
  - If LLM API call fails or `client` is not available: fall back to TF-IDF cosine similarity ranking.
- Update module docstring to reflect real LLM-driven RAG retrieval.

---

### Streamlit Showcase Application

#### [MODIFY] [app.py](../app.py)

- Line 269: Pass `client=client` to `retrieve(...)`:
  ```python
  retrieved = retrieve(question, corpus, top_k=2, client=client)
  ```

---

### Core PoC Notebook

#### [MODIFY] [gadded.ipynb](../gadded.ipynb)

- Update markdown cell 11 description to document LLM-driven RAG retrieval.
- Update code cell 15 to pass `client=client` into `retrieve(question, corpus, top_k=2, client=client)`.

---

### Unit Test Suite

#### [MODIFY] [test_regulatory.py](../tests/test_regulatory.py)

- Add `test_llm_retrieval_ranks_relevant_excerpts_live()` test marked with `@pytest.mark.skipif(not os.environ.get("GROQ_API_KEY"), ...)` to verify live LLM RAG retrieval rankings.
- Ensure existing offline TF-IDF fallback tests continue to pass cleanly.

## Verification Plan

### Automated Tests
- Run `.\.venv\Scripts\python.exe -m pytest tests/test_regulatory.py` to verify both offline fallback and live LLM RAG retrieval tests pass.
- Run full test suite `.\.venv\Scripts\python.exe -m pytest` to ensure no regressions.

### Manual Verification
- Test `retrieve()` with live `GROQ_API_KEY` using python to confirm LLM scores and ranks relevant excerpts (`exc-001`, `exc-002`, `exc-003`, etc.) correctly.
- Test `app.py` regulatory tab execution flow.
