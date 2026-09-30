import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parent
CORPUS_PATH = BASE_DIR / "corpus" / "corpus.jsonl"
CHROMA_PATH = BASE_DIR / "chroma"
AUDIT_PATH = CHROMA_PATH / "rag-audit.jsonl"
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://student2-database:5002")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = "student2_staff_context"
MAX_RESULTS = 10
MAX_EVIDENCE_DISTANCE = 0.45


def _now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _staff_chunks(staff_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
	chunks = []
	for staff in staff_records:
		staff_id = staff.get("staff_id")
		if staff_id is None:
			continue
		name = " ".join(
			part for part in (staff.get("given_name"), staff.get("family_name")) if part
		)
		department = str(staff.get("department") or "Unknown")
		employment_type = str(staff.get("employment_type") or "Unknown")
		chunks.append(
			{
				"chunk_id": f"staff-{staff_id}",
				"source_id": f"student2-database:/staff/{staff_id}",
				"text": (
					f"Staff member {name} (staff ID {staff_id}) works in the "
					f"{department} department and has {employment_type} employment."
				),
				"metadata": {
					"staff_id": int(staff_id),
					"department": department,
					"employment_type": employment_type,
				},
				"indexed_at": _now(),
			}
		)
	return chunks


def _embed_texts(texts: list[str]) -> list[list[float]]:
	if not texts:
		return []
	response = requests.post(
		f"{OLLAMA_HOST}/api/embed",
		json={"model": OLLAMA_EMBED_MODEL, "input": texts},
		timeout=120,
	)
	response.raise_for_status()
	embeddings = response.json().get("embeddings")
	if not isinstance(embeddings, list) or len(embeddings) != len(texts):
		raise ValueError("Ollama returned an invalid embedding response")
	return embeddings


def _get_collection():
	import chromadb

	client = chromadb.PersistentClient(path=str(CHROMA_PATH))
	return client.get_or_create_collection(
		name=COLLECTION_NAME,
		metadata={"hnsw:space": "cosine"},
	)


def _write_corpus(chunks: list[dict[str, Any]]) -> None:
	CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
	with CORPUS_PATH.open("w", encoding="utf-8") as corpus_file:
		for chunk in chunks:
			corpus_file.write(json.dumps(chunk) + "\n")


def _audit(
	tool_name: str,
	tool_input: dict[str, Any],
	outcome: str,
	started: float,
	details: dict[str, Any] | None = None,
) -> None:
	AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
	entry = {
		"request_id": str(uuid.uuid4()),
		"tool_name": tool_name,
		"tool_input": tool_input,
		"timestamp": _now(),
		"duration_ms": round((time.monotonic() - started) * 1000),
		"outcome": outcome,
		"details": details or {},
	}
	with AUDIT_PATH.open("a", encoding="utf-8") as audit_file:
		audit_file.write(json.dumps(entry) + "\n")


def refresh_corpus(
	caller: str = "student",
	staff_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
	started = time.monotonic()
	try:
		if staff_records is None:
			response = requests.get(f"{DATABASE_SERVICE_URL}/staff", timeout=10)
			response.raise_for_status()
			staff_records = response.json()
		if not isinstance(staff_records, list):
			raise ValueError("Database service returned an invalid staff list")
		chunks = _staff_chunks(staff_records)
		embeddings = _embed_texts([chunk["text"] for chunk in chunks])
		collection = _get_collection()
		existing = collection.get(include=[])
		existing_ids = existing.get("ids", [])
		if existing_ids:
			collection.delete(ids=existing_ids)
		if chunks:
			collection.add(
				ids=[chunk["chunk_id"] for chunk in chunks],
				documents=[chunk["text"] for chunk in chunks],
				metadatas=[
					{
						**chunk["metadata"],
						"source_id": chunk["source_id"],
						"indexed_at": chunk["indexed_at"],
					}
					for chunk in chunks
				],
				embeddings=embeddings,
			)
		_write_corpus(chunks)
		result = {
			"status": "success",
			"caller": caller,
			"chunk_count": len(chunks),
			"collection": COLLECTION_NAME,
		}
		_audit(
			"refresh_corpus",
			{"caller": caller},
			"success",
			started,
			{"chunk_count": len(chunks)},
		)
		return result
	except Exception as exc:
		_audit("refresh_corpus", {"caller": caller}, "error", started)
		return {"status": "error", "error": str(exc)}


def retrieve_context(
	query: str,
	k: int = 5,
	caller: str = "student",
	collection=None,
) -> dict[str, Any]:
	query = (query or "").strip()
	if not query:
		return {"status": "error", "error": "query is required"}
	if not isinstance(k, int) or isinstance(k, bool) or k < 1:
		return {"status": "error", "error": "k must be a positive integer"}

	started = time.monotonic()
	try:
		collection = collection or _get_collection()
		if collection.count() == 0:
			refreshed = refresh_corpus(caller="auto_refresh")
			if refreshed.get("status") != "success":
				raise RuntimeError(refreshed.get("error", "corpus refresh failed"))
		query_options = {
			"query_embeddings": _embed_texts([query]),
			"n_results": min(k, MAX_RESULTS),
		}
		where = _department_filter(query, collection)
		if where:
			query_options["where"] = where
		result = collection.query(**query_options)
		ids = (result.get("ids") or [[]])[0]
		documents = (result.get("documents") or [[]])[0]
		metadatas = (result.get("metadatas") or [[]])[0]
		distances = (result.get("distances") or [[]])[0]
		matches = []
		for index, chunk_id in enumerate(ids):
			metadata = metadatas[index] if index < len(metadatas) else {}
			matches.append(
				{
					"rank": index + 1,
					"chunk_id": chunk_id,
					"source_id": metadata.get("source_id"),
					"distance": distances[index] if index < len(distances) else None,
					"text": documents[index] if index < len(documents) else "",
					"metadata": {
						key: metadata[key]
						for key in ("staff_id", "department", "employment_type")
						if key in metadata
					},
				}
			)
		response = {"status": "success", "query": query, "caller": caller, "results": matches}
		_audit(
			"retrieve_context",
			{"query": query, "k": min(k, MAX_RESULTS), "caller": caller},
			"success",
			started,
			{"result_count": len(matches), "chunk_ids": [row["chunk_id"] for row in matches]},
		)
		return response
	except Exception as exc:
		_audit("retrieve_context", {"query": query, "caller": caller}, "error", started)
		return {"status": "error", "query": query, "error": str(exc)}


def _confidence_category(results: list[dict[str, Any]]) -> str:
	distances = [
		result["distance"]
		for result in results
		if isinstance(result.get("distance"), (float, int))
	]
	reliable_distances = [distance for distance in distances if distance <= MAX_EVIDENCE_DISTANCE]
	if not reliable_distances:
		return "low"
	if len(reliable_distances) >= 2 and max(reliable_distances) <= 0.30:
		return "high"
	return "medium"



def _department_filter(query: str, collection) -> dict[str, str] | None:
	get_results = getattr(collection, "get", None)
	if get_results is None:
		return None
	corpus = get_results(include=["metadatas"])
	departments = {
		str(metadata["department"])
		for metadata in corpus.get("metadatas", [])
		if isinstance(metadata, dict) and metadata.get("department")
	}
	query_folded = query.casefold()
	matches = [department for department in departments if department.casefold() in query_folded]
	if not matches:
		return None
	return {"department": max(matches, key=len)}

def answer_question(query: str, k: int = 5, caller: str = "student") -> dict[str, Any]:
	started = time.monotonic()
	retrieval = retrieve_context(query=query, k=k, caller=caller)
	if retrieval.get("status") != "success":
		_audit("answer_question", {"query": query, "caller": caller}, "error", started)
		return retrieval

	results = [
		result
		for result in retrieval["results"]
		if isinstance(result.get("distance"), (float, int))
		and result["distance"] <= MAX_EVIDENCE_DISTANCE
	]
	confidence = _confidence_category(results)
	citations = [
		{"chunk_id": result["chunk_id"], "source_id": result["source_id"]}
		for result in results
	] if confidence != "low" else []
	if not results or confidence == "low":
		answer = "Insufficient evidence in the staff registry to answer this question."
	else:
		context = "\n\n".join(
			f"[{result['chunk_id']}] {result['text']}"
			for result in results
		)
		try:
			response = requests.post(
				f"{OLLAMA_HOST}/api/generate",
				json={
					"model": OLLAMA_MODEL,
					"prompt": (
						"Answer using only the supplied staff evidence. Cite each factual "
						"claim with its exact [staff-ID] chunk label. If the evidence does "
						"not answer the question, reply exactly: Insufficient evidence.\n\n"
						f"Question: {query}\n\nEvidence:\n{context}"
					),
					"stream": False,
				},
				timeout=120,
			)
			response.raise_for_status()
			answer = response.json().get("response", "").strip()
			if not answer:
				answer = "Insufficient evidence in the staff registry to answer this question."
		except requests.RequestException as exc:
			_audit(
				"answer_question",
				{"query": query, "k": k, "caller": caller},
				"error",
				started,
				{"error_type": type(exc).__name__},
			)
			return {"status": "error", "query": query, "error": f"Ollama request failed: {exc}"}

	adaptation = "Abstained because retrieval confidence was low." if confidence == "low" else "Answered from retrieved staff evidence."
	result = {
		"status": "success",
		"query": query,
		"answer": answer,
		"citations": citations,
		"confidence_category": confidence,
		"retrieval_summary": {"retrieved_count": len(results), "top_chunk": results[0]["chunk_id"] if results else None},
		"agentic_workflow": {
			"plan": "Retrieve staff records relevant to the question.",
			"act": "Search the Chroma index using local Ollama embeddings.",
			"observe": {
				"retrieved_count": len(results),
				"confidence_category": confidence,
				"citation_chunk_ids": [citation["chunk_id"] for citation in citations],
			},
			"adapt": adaptation,
		},
	}
	_audit(
		"answer_question",
		{"query": query, "k": k, "caller": caller},
		"success",
		started,
		{
			"confidence_category": confidence,
			"citation_chunk_ids": [citation["chunk_id"] for citation in citations],
		},
	)
	return result
