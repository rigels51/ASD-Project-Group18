# RAG Tool Contracts

RAG service operations are available to the Student 2 backend over the private Compose network.

## refresh_corpus
- Purpose: rebuild corpus and vector index
- Input: `caller` (optional)
- Output: `status`, `chunk_count`, `collection` or structured `error`

## retrieve_context
- Purpose: retrieve relevant chunks for a query
- Input: `query` (required), `k` (optional), `caller` (optional)
- Output: `status`, `results[]` with `chunk_id`, `source_id`, `distance`, `text`, and staff metadata

## answer_question
- Purpose: answer strictly from retrieved context
- Input: `query` (required), `k` (optional), `caller` (optional)
- Output: `answer`, `citations[]` with chunk/source IDs, `confidence_category`, `retrieval_summary` or structured `error`

The corpus includes only staff ID, name, department, and employment type from the Student 2 database API. Email addresses are excluded. Embeddings are generated locally through Ollama using `OLLAMA_EMBED_MODEL`.
