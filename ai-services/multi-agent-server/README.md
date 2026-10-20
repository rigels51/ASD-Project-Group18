# Shared Multi-Agent Server (Release 2)

One local, **non-containerised** server shared by all five features. It runs
**Planner → Worker → Reviewer → Human Review** on live data from a feature's own API,
and records every step in two append-only evidence files.

| Agent | Model | Job |
|---|---|---|
| Planner | `qwen2.5:0.5b` | Picks the feature domain + evidence sources (rule-based, reproducible) and writes the plan |
| Worker | `qwen2.5:0.5b` | Fetches only the evidence the plan named, answers from it; any ID not in the evidence is caught and the answer is replaced |
| Reviewer | `llama3.1:8b` | 6 automatic checks + model review → risk `low/medium/high` and a recommended decision. The model can raise the risk, never lower it |
| Human | — | `Accept`, `Partially Accept`, `Correct` (with corrected output), or `Reject`. Nothing is final until this step |

If Ollama is down, every agent falls back to a deterministic answer and says so, so the
workflow, audit log and human step still complete.

## Run

```bash
pip install -r requirements.txt
ollama pull qwen2.5:0.5b && ollama pull llama3.1:8b
python app.py                               # http://localhost:5004
```

Terminal (no UI needed):

```bash
python workflow_runner.py --domain assessment "Summarise the assessments for ASD101"   # then decide 1-4
python workflow_runner.py --status
python workflow_runner.py --decide <workflow_id>     # decide on a run started from a UI
```

## API

| Method | Path | Body / notes |
|---|---|---|
| GET | `/health` | agents, models, domains |
| GET | `/domains` | owner + sources per domain |
| POST | `/workflow` | `{"user_request", "domain"?, "caller"?}` → 200 `pending_human_review` / 422 planner rejected / 400 bad input |
| POST | `/workflow/<id>/decision` | `{"decision", "reviewer", "comment", "corrected_output"}` — comment required unless Accept; one decision per workflow |
| GET | `/workflow/<id>` | latest state incl. decision |
| GET | `/workflows?domain=&limit=` | summaries, newest first |
| GET | `/workflow/status` | counts, decisions, audit size |

Domains (edit `evidence.py` → `DOMAINS`): `students` :5002, `staff` :5012, `timetable` :5003,
`course` :5032, `assessment` :5022. All read over each feature's REST API — never its DB file.

## Evidence files

* `workflow_history.jsonl` — full workflow records + human decision events
* `coordination_audit.jsonl` — one line per handoff: `workflow_started → planner_completed → worker_completed → reviewer_completed → awaiting_human_review → human_decision_recorded`

Set `MULTI_AGENT_LOG_DIR` to write them elsewhere (tests do this).

## Tests (offline — no Ollama, no services)

```bash
python -m unittest discover -s tests -v
```

## Env

`OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_REVIEW_MODEL`, `OLLAMA_TIMEOUT_SECONDS` (60),
`MULTI_AGENT_LLM_ENABLED` (true), `MULTI_AGENT_LOG_DIR`, `PORT` (5004), and the per-domain
`*_DATABASE_URL` / `TIMETABLE_API_URL` overrides.

Feature integration: see `docs/release-2/multi-agent-integration-guide.md` and `integration/`.
