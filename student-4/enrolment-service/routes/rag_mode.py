import html
import json

from flask import Blueprint, request

from services.rag_api import (
    refresh_course_rag,
    retrieve_course_context,
    answer_course_question,
)


rag_bp = Blueprint("rag_mode", __name__)


# =========================================================
# Helpers
# =========================================================

def escape(value):
    return html.escape(str(value))


def raw_json(payload):
    return f"""
    <details style="margin-top: 18px;">
        <summary style="
            cursor: pointer;
            color: #17213c;
            font-size: 13px;
        ">
            Raw RAG result (JSON)
        </summary>

        <pre style="
            margin-top: 12px;
            padding: 16px;
            border: 1px solid #dfdcd4;
            border-radius: 7px;
            background: #f8f7f3;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-word;
            font-size: 12px;
            line-height: 1.55;
        ">{escape(json.dumps(payload, indent=2))}</pre>
    </details>
    """


def error_result(message):
    payload = {
        "status": "error",
        "error": str(message),
    }

    return f"""
    <div style="
        padding: 14px 16px;
        border: 1px solid #ead4d0;
        border-radius: 7px;
        background: #fff8f7;
        color: #8f3b34;
    ">
        <strong>RAG Error</strong>
        <p>{escape(message)}</p>
    </div>

    {raw_json(payload)}
    """


# =========================================================
# Refresh Result
# =========================================================

def render_refresh(result):

    chunk_count = ""
    status = "success"
    domain = "course"

    if isinstance(result, dict):
        chunk_count = result.get("chunk_count", "")
        status = result.get("status", "success")
        domain = result.get("domain", "course")

    return f"""
    <div style="margin-bottom: 14px;">
        <strong style="
            font-size: 16px;
            color: #17213c;
        ">
            RAG Corpus Refreshed
        </strong>
    </div>

    <table>
        <thead>
            <tr>
                <th>Domain</th>
                <th>Chunks</th>
                <th>Status</th>
            </tr>
        </thead>

        <tbody>
            <tr>
                <td>{escape(domain)}</td>
                <td>{escape(chunk_count)}</td>
                <td>
                    <strong>{escape(status)}</strong>
                </td>
            </tr>
        </tbody>
    </table>

    {raw_json(result)}
    """


# =========================================================
# Retrieve Result
# =========================================================

def get_retrieved_items(result):

    if not isinstance(result, dict):
        return []

    possible_keys = [
        "results",
        "chunks",
        "retrieved",
        "evidence",
        "contexts",
    ]

    for key in possible_keys:
        value = result.get(key)

        if isinstance(value, list):
            return value

    nested = result.get("result")

    if isinstance(nested, list):
        return nested

    if isinstance(nested, dict):

        for key in possible_keys:
            value = nested.get(key)

            if isinstance(value, list):
                return value

    return []


def render_retrieve(result):

    items = get_retrieved_items(result)

    query = ""

    if isinstance(result, dict):
        query = result.get("query", "")

    rows = []

    for index, item in enumerate(items, start=1):

        if not isinstance(item, dict):
            continue

        source_id = item.get(
            "source_id",
            item.get(
                "chunk_id",
                item.get("id", f"Source {index}")
            )
        )

        section = item.get(
            "section",
            item.get("title", source_id)
        )

        text = item.get(
            "text",
            item.get(
                "content",
                item.get("chunk", "")
            )
        )

        similarity = item.get(
            "similarity",
            item.get("score", "")
        )

        rows.append(
            f"""
            <tr>
                <td>
                    <strong>{escape(section)}</strong>
                </td>

                <td>{escape(source_id)}</td>

                <td>{escape(text)}</td>

                <td>{escape(similarity)}</td>
            </tr>
            """
        )

    if rows:

        result_html = f"""
        <table>
            <thead>
                <tr>
                    <th>Section</th>
                    <th>Source</th>
                    <th>Retrieved Evidence</th>
                    <th>Similarity</th>
                </tr>
            </thead>

            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """

    else:

        result_html = """
        <p class="muted">
            No retrieved evidence could be displayed.
        </p>
        """

    return f"""
    <div style="margin-bottom: 16px;">

        <strong style="
            font-size: 16px;
            color: #17213c;
        ">
            Retrieved Evidence
        </strong>

        <span style="
            margin-left: 8px;
            color: #777d88;
            font-size: 13px;
        ">
            {len(items)} result(s)
        </span>

    </div>

    {
        f'''
        <p style="
            margin-bottom: 16px;
            color: #636a79;
        ">
            <strong>Query:</strong>
            {escape(query)}
        </p>
        '''
        if query
        else ""
    }

    {result_html}

    {raw_json(result)}
    """


# =========================================================
# RAG Answer
# =========================================================

def render_answer(result):

    if not isinstance(result, dict):

        return f"""
        <p class="muted">
            RAG answer could not be displayed.
        </p>

        {raw_json(result)}
        """

    answer = result.get("answer", "")

    query = result.get("query", "")

    confidence = result.get(
        "confidence_category",
        result.get("confidence", "unknown")
    )

    citations = result.get("citations", [])

    if not isinstance(citations, list):
        citations = []


    # -----------------------------------------------------
    # Build Sources
    # -----------------------------------------------------

    source_html = []

    for index, citation in enumerate(
        citations,
        start=1
    ):

        if isinstance(citation, str):

            source_html.append(
                f"""
                <div style="
                    padding: 12px 14px;
                    margin-bottom: 10px;
                    border-left: 3px solid #b6872f;
                    background: #faf9f6;
                ">
                    <strong>
                        Source {index}
                    </strong>

                    <div style="
                        margin-top: 5px;
                        color: #636a79;
                        font-size: 13px;
                    ">
                        {escape(citation)}
                    </div>
                </div>
                """
            )

            continue


        if not isinstance(citation, dict):
            continue


        source_id = citation.get(
            "source_id",
            citation.get(
                "chunk_id",
                citation.get(
                    "id",
                    f"Source {index}"
                )
            )
        )

        section = citation.get(
            "section",
            citation.get(
                "title",
                source_id
            )
        )

        similarity = citation.get(
            "similarity",
            citation.get("score", "")
        )


        source_html.append(
            f"""
            <div style="
                padding: 12px 14px;
                margin-bottom: 10px;
                border-left: 3px solid #b6872f;
                border-radius: 0 6px 6px 0;
                background: #faf9f6;
            ">

                <strong style="
                    display: block;
                    margin-bottom: 6px;
                    color: #17213c;
                ">
                    {escape(section)}
                </strong>

                <div style="
                    color: #636a79;
                    font-size: 13px;
                    line-height: 1.6;
                ">
                    Source: {escape(source_id)}
                </div>

                <div style="
                    color: #636a79;
                    font-size: 13px;
                    line-height: 1.6;
                ">
                    Similarity: {escape(similarity)}
                </div>

            </div>
            """
        )


    if source_html:

        sources = "".join(source_html)

    else:

        sources = """
        <p class="muted">
            No citations were returned.
        </p>
        """


    # -----------------------------------------------------
    # Final result
    # -----------------------------------------------------

    return f"""
    <div style="
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
    ">

        <strong style="
            font-size: 16px;
            color: #17213c;
        ">
            RAG Answer
        </strong>

    </div>


    {
        f'''
        <p style="
            margin: 0 0 16px;
            color: #636a79;
            font-size: 13px;
        ">
            <strong>Question:</strong>
            {escape(query)}
        </p>
        '''
        if query
        else ""
    }


    <!-- Answer -->

    <div style="
        padding: 17px;
        border: 1px solid #dfdcd4;
        border-radius: 7px;
        background: #fbfaf7;
        margin-bottom: 16px;
    ">

        <div style="
            margin-bottom: 8px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.7px;
            color: #a67c2d;
        ">
            ANSWER
        </div>

        <div style="
            color: #17213c;
            font-size: 14px;
            line-height: 1.7;
        ">
            {escape(answer)}
        </div>

    </div>


    <!-- Confidence -->

    <div style="
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 22px;
    ">

        <strong>
            Confidence
        </strong>

        <span style="
            display: inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            background: #e6efe8;
            color: #3f7350;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        ">
            {escape(confidence)}
        </span>

    </div>


    <!-- Sources -->

    <div style="margin-top: 8px;">

        <div style="
            margin-bottom: 12px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.7px;
            color: #a67c2d;
        ">
            SOURCES
        </div>

        {sources}

    </div>


    {raw_json(result)}
    """


# =========================================================
# Routes
# =========================================================

@rag_bp.post("/rag/refresh")
def rag_refresh():

    try:

        result = refresh_course_rag()

        return render_refresh(result), 200

    except Exception as exc:

        return error_result(str(exc)), 503


@rag_bp.post("/rag/retrieve")
def rag_retrieve():

    query = request.form.get(
        "query",
        ""
    ).strip()

    if not query:

        return error_result(
            "query is required"
        ), 400

    try:

        result = retrieve_course_context(
            query,
            5
        )

        return render_retrieve(
            result
        ), 200

    except Exception as exc:

        return error_result(
            str(exc)
        ), 503


@rag_bp.post("/rag/answer")
def rag_answer():

    query = request.form.get(
        "query",
        ""
    ).strip()

    if not query:

        return error_result(
            "query is required"
        ), 400

    try:

        result = answer_course_question(
            query,
            5
        )

        return render_answer(
            result
        ), 200

    except Exception as exc:

        return error_result(
            str(exc)
        ), 503