# Release 1 — Shared MCP and RAG

This guide covers the shared MCP and grounded-answer services used by all feature backends. MCP and RAG run as local Python processes; feature backends and databases run in Docker. Release 2 cloud deployment is not configured here.

## Prerequisites

- Docker Desktop and Ollama are running.
- Python 3.11 or newer is available.
- Ollama has the approved chat model and a local embedding model:

```bash
ollama pull qwen2.5:0.5b
ollama pull nomic-embed-text
```

The embedding model is selected with `OLLAMA_EMBED_MODEL`. The local RAG process reaches Ollama at `http://localhost:11434`.

## Start Student 2 Services

Install the shared service dependencies from the repository root:

```bash
python -m pip install -r ai-services/mcp-server/requirements.txt
python -m pip install -r ai-services/rag-server/requirements.txt
```

In separate terminals from the repository root, start the shared services:

```bash
cd ai-services/rag-server
python rag_http_server.py
```

```bash
cd ai-services/mcp-server
python server.py
```

Then start the Docker services from the repository root:

```bash
docker compose up --build -d
```

Open the Student 2 feature at `http://localhost:8082`. The shared team homepage remains at `http://localhost:8090`.

MCP is available at `http://localhost:8000/mcp`; Docker backends connect through `http://host.docker.internal:8000/mcp`. RAG is available at `http://localhost:5050/`; Docker backends connect through `http://host.docker.internal:5050`. RAG's `POST /answer` accepts `{"query": "...", "domain": "timetable"}` and returns the selected domain's answer, citations, and confidence category. Feature-specific MCP tools and RAG knowledge sources are registered from separate files, including Timetable's `timetable_tools.py` and policy document.

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

Install the backend dependencies into the project virtual environment:

```bash
python -m pip install -r student-2/backend-service/requirements.txt
```

Run the offline behavior tests:

```bash
python -m unittest discover -s ai-services/mcp-server -p "test_*.py" -v
python -m unittest discover -s ai-services/rag-server -p "test_*.py" -v
python -m unittest discover -s student-2/backend-service/tests -p "test_*.py" -v
```

After starting the local services and confirming Ollama has `nomic-embed-text`, run the evaluation from the RAG server directory:

```bash
cd ai-services/rag-server
python rag_eval.py
```

This refreshes the corpus, evaluates department, employment-type, and individual-record queries at $k=5$, and writes P@5/R@5 results to `ai-services/rag-server/retrieval-metrics.md`. The committed metrics file is a placeholder until this command is run against the team's local data and model.

## Release Evidence

Before submitting, capture actual results for:

- Local MCP/RAG startup and the Student 2 UI.
- Successful MCP tool calls and tool outputs.
- RAG corpus refresh, retrieved chunks, cited answer, and low-evidence abstention.
- `retrieval-metrics.md` P@5/R@5 values and the evaluation queries.
- MCP/RAG/backend unit-test and GitHub Actions results.
- Known limitations, including local Ollama/model prerequisites and the distance-based confidence heuristic.

Do not report expected outputs as completed evidence; record the actual run and environment.