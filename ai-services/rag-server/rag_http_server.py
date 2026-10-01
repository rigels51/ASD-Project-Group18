import os

from flask import Flask, jsonify, request

import timetable_rag
import student4_rag
import student5_rag
from rag_pipeline import answer_question, refresh_corpus, retrieve_context


app = Flask(__name__)

# Shared RAG server: each student feature registers its domain here as
# (refresh, retrieve, answer). Requests pick one with {"domain": "..."};
# requests without a domain keep the original staff behaviour.
DOMAINS = {
    "staff": (
        lambda *args, **kwargs: refresh_corpus(*args, **kwargs),
        lambda *args, **kwargs: retrieve_context(*args, **kwargs),
        lambda *args, **kwargs: answer_question(*args, **kwargs),
    ),

    "timetable": (
        lambda *args, **kwargs: timetable_rag.refresh_corpus(*args, **kwargs),
        lambda *args, **kwargs: timetable_rag.retrieve_context(*args, **kwargs),
        lambda *args, **kwargs: timetable_rag.answer_question(*args, **kwargs),
    ),

    "course": (
        lambda *args, **kwargs: student4_rag.refresh_corpus(*args, **kwargs),
        lambda *args, **kwargs: student4_rag.retrieve_context(*args, **kwargs),
        lambda *args, **kwargs: student4_rag.answer_question(*args, **kwargs),
    ),
        #Assessment & Grades Management
    "assessment": (
        lambda *args, **kwargs: student5_rag.refresh_corpus(*args, **kwargs),
        lambda *args, **kwargs: student5_rag.retrieve_context(*args, **kwargs),
        lambda *args, **kwargs: student5_rag.answer_question(*args, **kwargs),
    ),
}


def _domain(payload):
    name = str(payload.get("domain", "staff")).strip().lower()
    return name if name in DOMAINS else None


def _unknown_domain():
    return jsonify({
        "status": "error",
        "error": "unknown domain",
        "domains": sorted(DOMAINS)
    }), 400


def _payload():
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "shared-rag",
        "domains": sorted(DOMAINS)
    })


@app.post("/refresh")
def refresh():
    payload = _payload()

    domain = _domain(payload)

    if domain is None:
        return _unknown_domain()

    result = DOMAINS[domain][0](
        caller=str(payload.get("caller", "student"))[:64]
    )

    return jsonify(result), 200 if result.get("status") == "success" else 503


@app.post("/retrieve")
def retrieve():
    payload = _payload()

    query = payload.get("query")

    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        return jsonify({
            "status": "error",
            "error": "query must contain 1 to 1000 characters"
        }), 400

    k = payload.get("k", 5)

    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        return jsonify({
            "status": "error",
            "error": "k must be a positive integer"
        }), 400

    domain = _domain(payload)

    if domain is None:
        return _unknown_domain()

    result = DOMAINS[domain][1](
        query,
        k,
        caller=str(payload.get("caller", "student"))[:64]
    )

    return jsonify(result), 200 if result.get("status") == "success" else 503


@app.post("/answer")
def answer():
    payload = _payload()

    query = payload.get("query")

    if not isinstance(query, str) or not query.strip() or len(query) > 1000:
        return jsonify({
            "status": "error",
            "error": "query must contain 1 to 1000 characters"
        }), 400

    k = payload.get("k", 5)

    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        return jsonify({
            "status": "error",
            "error": "k must be a positive integer"
        }), 400

    domain = _domain(payload)

    if domain is None:
        return _unknown_domain()

    result = DOMAINS[domain][2](
        query,
        k,
        caller=str(payload.get("caller", "student"))[:64]
    )

    return jsonify(result), 200 if result.get("status") == "success" else 503


if __name__ == "__main__":
    # Runs on the host (not in Docker).
    # 5050 avoids the Timetable backend's host port 5003.
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5050"))
    )