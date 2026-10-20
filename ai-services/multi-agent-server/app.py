"""Shared Multi-Agent Server (Release 2). Runs on the host, NOT in Docker.

    cd ai-services/multi-agent-server && python app.py      # http://localhost:5004
"""

import os

from flask import Flask, jsonify, request
from flask_cors import CORS

import coordinator
import evidence
import llm

app = Flask(__name__)
CORS(app)
MAX_REQUEST_CHARS = 500


def _error(message: str, status: int):
    return jsonify({"status": "error", "error": message}), status


@app.get("/")
@app.get("/health")
def health():
    return jsonify({
        "service": "multi-agent-server", "status": "running",
        "agents": ["planner_agent", "worker_agent", "reviewer_agent", "human_reviewer"],
        "models": {"planner": llm.OLLAMA_MODEL, "worker": llm.OLLAMA_MODEL, "reviewer": llm.OLLAMA_REVIEW_MODEL},
        "domains": sorted(evidence.DOMAINS),
    })


@app.get("/domains")
def domains():
    return jsonify({name: {"owner": cfg["owner"], "sources": [s[0] for s in cfg["sources"]]}
                    for name, cfg in evidence.DOMAINS.items()})


@app.post("/workflow")
def start_workflow():
    data = request.get_json(silent=True) or {}
    user_request = str(data.get("user_request", "")).strip()
    domain = str(data.get("domain", "")).strip().lower() or None
    caller = str(data.get("caller", "api")).strip()[:64] or "api"
    if not user_request:
        return _error("user_request is required", 400)
    if len(user_request) > MAX_REQUEST_CHARS:
        return _error(f"user_request must be {MAX_REQUEST_CHARS} characters or fewer", 400)
    if domain and domain not in evidence.DOMAINS:
        return _error(f"unknown domain '{domain}'. Use one of: {', '.join(sorted(evidence.DOMAINS))}", 400)
    result = coordinator.run_workflow(user_request, domain, caller)
    return jsonify(result), 200 if result["status"] == "pending_human_review" else 422


@app.post("/workflow/<workflow_id>/decision")
def decide(workflow_id):
    data = request.get_json(silent=True) or {}
    try:
        result = coordinator.record_decision(
            workflow_id,
            decision=str(data.get("decision", "")).strip(),
            reviewer=str(data.get("reviewer", "")),
            comment=str(data.get("comment", "")),
            corrected_output=str(data.get("corrected_output", "")),
        )
    except KeyError:
        return _error("workflow not found", 404)
    except ValueError as exc:
        return _error(str(exc), 400)
    return jsonify(result), 200


@app.get("/workflow/<workflow_id>")
def get_one(workflow_id):
    wf = coordinator.get_workflow(workflow_id)
    return (jsonify(wf), 200) if wf else _error("workflow not found", 404)


@app.get("/workflows")
def list_all():
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 100))
    except ValueError:
        return _error("limit must be an integer", 400)
    domain = request.args.get("domain") or None
    return jsonify({"status": "success", "workflows": coordinator.list_workflows(limit, domain)})


@app.get("/workflow/status")
def status():
    return jsonify(coordinator.workflow_status())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5004")),
            debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
