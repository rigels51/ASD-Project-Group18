from flask import Flask, jsonify, request

from rag_pipeline import answer_question, refresh_corpus, retrieve_context


app = Flask(__name__)


def _payload():
	payload = request.get_json(silent=True)
	return payload if isinstance(payload, dict) else {}


@app.get("/health")
def health():
	return jsonify({"status": "ok", "service": "student2-rag"})


@app.post("/refresh")
def refresh():
	payload = _payload()
	result = refresh_corpus(caller=str(payload.get("caller", "student"))[:64])
	return jsonify(result), 200 if result.get("status") == "success" else 503


@app.post("/retrieve")
def retrieve():
	payload = _payload()
	query = payload.get("query")
	if not isinstance(query, str) or not query.strip() or len(query) > 1000:
		return jsonify({"status": "error", "error": "query must contain 1 to 1000 characters"}), 400
	k = payload.get("k", 5)
	if not isinstance(k, int) or isinstance(k, bool) or k < 1:
		return jsonify({"status": "error", "error": "k must be a positive integer"}), 400
	result = retrieve_context(query, k, caller=str(payload.get("caller", "student"))[:64])
	return jsonify(result), 200 if result.get("status") == "success" else 503


@app.post("/answer")
def answer():
	payload = _payload()
	query = payload.get("query")
	if not isinstance(query, str) or not query.strip() or len(query) > 1000:
		return jsonify({"status": "error", "error": "query must contain 1 to 1000 characters"}), 400
	k = payload.get("k", 5)
	if not isinstance(k, int) or isinstance(k, bool) or k < 1:
		return jsonify({"status": "error", "error": "k must be a positive integer"}), 400
	result = answer_question(query, k, caller=str(payload.get("caller", "student"))[:64])
	return jsonify(result), 200 if result.get("status") == "success" else 503


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5003)
# HTTP wrapper exposing /refresh, /retrieve, /answer so 
# containerised backends can 
# call the RAG pipeline via host.docker.internal. 

