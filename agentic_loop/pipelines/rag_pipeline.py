"""RAG validation mode: Plan -> Act -> Observe -> Adapt against the shared RAG server."""

from agentic_loop.collectors import rag_collector
from agentic_loop.config.review_config import RAG_CASES, RAG_SERVER_URL
from agentic_loop.config.review_config import OLLAMA_MODEL
from agentic_loop.core.ai_runner import suggest_adaptation
from agentic_loop.core.reporter import Reporter


def _evaluate(case, observation):
    """Return (passed, detail). Grounded = cited + high/medium; abstain = no citations + low."""
    body = observation["body"]
    if observation["status_code"] != 200 or body.get("status") != "success":
        return False, f"request failed ({observation['status_code']}): {str(body.get('error', ''))[:100]}"

    confidence = body.get("confidence_category")
    citations = body.get("citations") or []
    cited = ", ".join(str(c.get("chunk_id")) for c in citations) or "none"

    if case["expect"] == "grounded":
        if citations and confidence in {"high", "medium"}:
            return True, f"grounded answer, confidence {confidence}, cites {cited}"
        return False, f"expected a grounded answer, got confidence {confidence} with citations: {cited}"

    if not citations and confidence == "low":
        return True, "insufficient-context response returned (no citations, confidence low)"
    return False, f"expected abstention, got confidence {confidence} with citations: {cited}"


def run(use_ai=True):
    report = Reporter("rag")
    domains = sorted({case["domain"] for case in RAG_CASES})

    # ---------- PLAN ----------
    report.stage("PLAN", f"Validate the shared RAG server at {RAG_SERVER_URL}.")
    report.line("1. Health check and list the knowledge domains the server hosts.")
    report.line("2. For each domain, ask an in-scope question: expect a grounded answer with citations "
                "and a high/medium confidence category.")
    report.line("3. For each domain, ask an out-of-scope question: expect an insufficient-context "
                "response (no citations, low confidence).")
    report.line(f"Domains under test: {', '.join(domains)}")

    # ---------- ACT ----------
    report.stage("ACT", "Checking health and sending grounded / out-of-scope questions.")
    health = rag_collector.health(RAG_SERVER_URL)
    if not health["ok"]:
        report.line(f"RAG server unreachable: {health['error']}")
        report.stage("OBSERVE", "0 checks run — server unreachable.")
        report.stage("ADAPT", "Start the shared RAG server (cd ai-services/rag-server && python rag_http_server.py) and rerun.")
        report.save()
        return False

    hosted = health.get("domains", [])
    report.line(f"Server healthy; hosted domains: {', '.join(hosted) or 'not reported'}")

    rows, results, examples = [], [], []
    for case in RAG_CASES:
        if hosted and case["domain"] not in hosted:
            rows.append((case["domain"], case["question"], case["expect"], "FAIL", "domain not hosted by the server"))
            results.append(("fail", case["domain"]))
            continue
        observation = rag_collector.ask(RAG_SERVER_URL, case["domain"], case["question"])
        passed, detail = _evaluate(case, observation)
        results.append(("pass" if passed else "fail", case["domain"]))
        rows.append((case["domain"], case["question"], case["expect"], "PASS" if passed else "FAIL",
                     f"{detail} ({observation['latency_ms']} ms)"))
        if observation["body"].get("status") == "success":
            examples.append((case, observation["body"]))

    for domain in sorted(set(hosted) - set(domains)):
        rows.append((domain, "—", "—", "NOT EXERCISED", "no case in agentic_loop/config/review_config.py"))

    # ---------- OBSERVE ----------
    passed = sum(1 for status, _ in results if status == "pass")
    failed = sorted({domain for status, domain in results if status == "fail"})
    report.stage("OBSERVE", f"{passed} passed, {len(results) - passed} failed.")
    report.table(["Domain", "Question", "Expect", "Result", "Detail"], rows)
    for case, body in examples:
        report.line(f"[{case['domain']}] Q: {case['question']}")
        report.block(f"A: {body.get('answer', '')}\n"
                     f"confidence: {body.get('confidence_category')} | citations: "
                     + (", ".join(f"{c.get('chunk_id')} ({c.get('source_id')})" for c in body.get("citations") or [])
                        or "none"))

    # ---------- ADAPT ----------
    report.stage("ADAPT")
    if failed:
        report.line("Fix before submission, domains: " + ", ".join(failed))
        report.line("Grounded case failing -> check the knowledge source is indexed and the similarity "
                    "threshold is not too strict. Abstain case failing -> threshold too loose.")
    else:
        report.line("All domains returned grounded answers and abstained correctly; no rule-based adaptation needed.")
    if use_ai:
        summary = "\n".join(f"{r[0]} | {r[1]} | expect {r[2]} -> {r[3]}: {r[4]}" for r in rows)
        advice, error = suggest_adaptation("rag", summary)
        report.line(f"Local AI suggestion ({OLLAMA_MODEL if advice else 'unavailable'}):")
        report.block(advice or error)

    report.save()
    return not failed
