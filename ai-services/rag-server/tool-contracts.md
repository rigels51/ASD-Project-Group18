# RAG Tool Contracts

Documents the input/output contract for each RAG tool. To be completed once `rag_pipeline.py` is implemented.

## refresh_corpus
- Purpose: rebuild corpus and vector index
- Input: `caller` (optional)
- Output: `status`, `chunk_count`, `collection`, `corpus_path` or `error`

## retrieve_context
- Purpose: retrieve relevant chunks for a query
- Input: `query` (required), `k` (optional), `caller` (optional)
- Output: `status`, `results[]` with `chunk_id`, `source_id`, `authority_tier`, `distance`, `text`

## answer_question
- Purpose: answer strictly from retrieved context
- Input: `query` (required), `k` (optional), `caller` (optional)
- Output: `answer`, `citations[]`, `confidence_category`, `retrieval_summary` or `error`
