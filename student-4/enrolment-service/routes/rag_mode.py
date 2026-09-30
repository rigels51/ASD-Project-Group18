import json

from flask import Blueprint, request

from services.rag_api import (
    refresh_course_rag,
    retrieve_course_context,
    answer_course_question,
)


rag_bp = Blueprint(
    "rag_mode",
    __name__
)


def render_json(title: str, payload):
    return f"""
    <h3>{title}</h3>
    <pre>{json.dumps(payload, indent=2)}</pre>
    """


@rag_bp.post("/rag/refresh")
def rag_refresh():
    try:
        result = refresh_course_rag()

        return render_json(
            "RAG Refresh",
            result
        ), 200

    except Exception as exc:
        return render_json(
            "RAG Error",
            {
                "error": str(exc)
            }
        ), 503


@rag_bp.post("/rag/retrieve")
def rag_retrieve():
    query = request.form.get(
        "query",
        ""
    ).strip()

    if not query:
        return render_json(
            "RAG Error",
            {
                "error": "query is required"
            }
        ), 400

    try:
        result = retrieve_course_context(
            query,
            5
        )

        return render_json(
            "RAG Retrieve",
            result
        ), 200

    except Exception as exc:
        return render_json(
            "RAG Error",
            {
                "error": str(exc)
            }
        ), 503


@rag_bp.post("/rag/answer")
def rag_answer():
    query = request.form.get(
        "query",
        ""
    ).strip()

    if not query:
        return render_json(
            "RAG Error",
            {
                "error": "query is required"
            }
        ), 400

    try:
        result = answer_course_question(
            query,
            5
        )

        return render_json(
            "RAG Answer",
            result
        ), 200

    except Exception as exc:
        return render_json(
            "RAG Error",
            {
                "error": str(exc)
            }
        ), 503