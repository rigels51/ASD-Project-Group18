# Release 1 — Student 2 MCP and RAG

This guide covers the Student 2 staff registry's Release 1 MCP and grounded-answer path. MCP and RAG are local-only and join the root Docker Compose network. Release 2 cloud deployment is not configured here.

## Prerequisites

- Docker Desktop and Ollama are running.
- Ollama has the approved chat model and a local embedding model:

```bash
ollama pull qwen2.5:0.5b
ollama pull nomic-embed-text
```

The embedding model is selected with `OLLAMA_EMBED_MODEL`. The RAG service must reach Ollama at `http://host.docker.internal:11434`.

## Start Student 2 Services

From the repository root:

```bash
docker compose up --build -d student2-database student2-mcp student2-rag student2-backend student2-frontend
docker compose ps
```

Open the Student 2 feature at `http://localhost:8082`. The shared team homepage remains at `http://localhost:8090`.

The backend talks to MCP at `http://student2-mcp:8000/mcp` and RAG at `http://student2-rag:5003` over `enrolment-network`. The MCP service is published to the host at port `8052`. The RAG service is intentionally not published to host port `5003`, which is already used by Student 3; it is reachable internally by the backend and at `/health` from the Compose network.

## Exercise the Feature

In the Student 2 UI:

- Open **MCP Tools** and run a staff count, directory, member lookup, or employment summary. Directory and member results omit email addresses.
- Open **RAG Answers**, refresh the staff index, and ask a question supported by the staff records. The response includes retrieved source IDs and a confidence category.
- Ask a question that cannot be supported by the registry; the RAG pipeline should abstain when retrieval confidence is low.

Backend routes for automated checks:

- `GET /mcp/tools`
- `POST /mcp/call` with JSON `{ "tool": "get_staff_count", "arguments": {} }`
- `POST /rag/refresh`
- `POST /rag/answer` with JSON `{ "question": "Which staff members work in Arts?" }`

## Tests and Retrieval Evaluation

Install the feature dependencies into the project virtual environment:

```bash
python -m pip install -r student-2/backend-service/requirements.txt
python -m pip install -r ai-services/mcp-server/requirements.txt
```

Run the offline behavior tests:

```bash
python -m unittest discover -s ai-services/mcp-server -p "test_*.py" -v
python -m unittest discover -s ai-services/rag-server -p "test_*.py" -v
python -m unittest discover -s student-2/backend-service/tests -p "test_*.py" -v
```

After starting the services and confirming Ollama has `nomic-embed-text`, run the evaluation inside the RAG container:

```bash
docker compose exec student2-rag python rag_eval.py
```

This refreshes the corpus, evaluates department, employment-type, and individual-record queries at $k=5$, and writes P@5/R@5 results to `ai-services/rag-server/retrieval-metrics.md`. The committed metrics file is a placeholder until this command is run against the team's local data and model.

## Release Evidence

Before submitting, capture actual results for:

- Docker Compose service startup and the Student 2 UI.
- Successful MCP tool calls and tool outputs.
- RAG corpus refresh, retrieved chunks, cited answer, and low-evidence abstention.
- `retrieval-metrics.md` P@5/R@5 values and the evaluation queries.
- MCP/RAG/backend unit-test and GitHub Actions results.
- Known limitations, including local Ollama/model prerequisites and the distance-based confidence heuristic.

Do not report expected outputs as completed evidence; record the actual run and environment.