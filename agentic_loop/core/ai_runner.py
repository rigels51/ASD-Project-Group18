"""ADAPT helper: ask the local Ollama model for one improvement based on observed results."""

from agentic_loop.config.review_config import OLLAMA_BASE_URL, OLLAMA_MODEL


def suggest_adaptation(mode, observe_summary):
    """Return (suggestion, error). Never raises: the loop still completes without Ollama."""
    prompt = (
        f"You are reviewing the {mode.upper()} validation results of a university management "
        "system's shared AI services.\n"
        f"Observed results:\n{observe_summary}\n\n"
        "Rules:\n"
        "- Only discuss checks that appear in the observed results.\n"
        "- If a check failed, name it and give one likely cause and one concrete fix.\n"
        "- If every check passed, recommend one additional validation case.\n"
        "- Do not invent tools, endpoints, or data that are not in the results.\n"
        "- Return exactly two bullet points."
    )
    try:
        from openai import OpenAI

        client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You are a concise software validation reviewer."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=220,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as exc:  # noqa: BLE001
        return None, f"Local AI agent unavailable ({type(exc).__name__}: {exc})"
