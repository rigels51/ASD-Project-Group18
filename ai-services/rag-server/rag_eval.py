import os
from pathlib import Path
from typing import Any, Callable

import requests

from rag_pipeline import refresh_corpus, retrieve_context


BASE_DIR = Path(__file__).resolve().parent
METRICS_PATH = BASE_DIR / "retrieval-metrics.md"
DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://localhost:5012").rstrip("/")
K = 5


def precision_recall_at_k(
	retrieved_ids: list[str],
	relevant_ids: set[str],
	k: int = K,
) -> tuple[float, float]:
	if k < 1:
		raise ValueError("k must be positive")
	hits = len(set(retrieved_ids[:k]) & relevant_ids)
	precision = hits / k
	recall = hits / len(relevant_ids) if relevant_ids else 0.0
	return precision, recall


def _benchmark_cases(staff_records: list[dict[str, Any]]):
	cases = []
	departments = sorted({str(record.get("department", "")) for record in staff_records})
	employment_types = sorted(
		{str(record.get("employment_type", "")) for record in staff_records}
	)
	if departments:
		department = departments[0]
		relevant = {
			f"staff-{record['staff_id']}"
			for record in staff_records
			if str(record.get("department", "")).casefold() == department.casefold()
		}
		cases.append((f"Staff in the {department} department", relevant))
	if employment_types:
		employment_type = employment_types[0]
		relevant = {
			f"staff-{record['staff_id']}"
			for record in staff_records
			if str(record.get("employment_type", "")).casefold() == employment_type.casefold()
		}
		cases.append((f"Staff with {employment_type} employment", relevant))
	if staff_records:
		record = staff_records[0]
		name = " ".join((record.get("given_name", ""), record.get("family_name", ""))).strip()
		cases.append((f"Staff record for {name}", {f"staff-{record['staff_id']}"}))
	return cases


def evaluate_queries(
	staff_records: list[dict[str, Any]],
	retriever: Callable[..., dict[str, Any]] = retrieve_context,
) -> list[dict[str, Any]]:
	metrics = []
	for query, relevant_ids in _benchmark_cases(staff_records):
		response = retriever(query, k=K, caller="rag_eval")
		results = response.get("results", []) if response.get("status") == "success" else []
		retrieved_ids = [result.get("chunk_id", "") for result in results]
		precision, recall = precision_recall_at_k(retrieved_ids, relevant_ids)
		metrics.append(
			{
				"query": query,
				"retrieved_chunk_ids": retrieved_ids,
				"relevant_chunk_ids": sorted(relevant_ids),
				"p_at_5": precision,
				"r_at_5": recall,
			}
		)
	return metrics


def write_metrics_report(metrics: list[dict[str, Any]]) -> None:
	lines = ["# RAG Retrieval Metrics", "", f"Evaluation cutoff: k={K}", ""]
	for result in metrics:
		lines.extend(
			[
				f"## {result['query']}",
				f"- Retrieved: {result['retrieved_chunk_ids']}",
				f"- Relevant: {result['relevant_chunk_ids']}",
				f"- P@5: {result['p_at_5']:.3f}",
				f"- R@5: {result['r_at_5']:.3f}",
				"",
			]
		)
	METRICS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
	response = requests.get(f"{DATABASE_SERVICE_URL}/staff", timeout=10)
	response.raise_for_status()
	staff_records = response.json()
	refresh_result = refresh_corpus(caller="rag_eval", staff_records=staff_records)
	if refresh_result.get("status") != "success":
		raise RuntimeError(f"Corpus refresh failed: {refresh_result.get('error')}")
	metrics = evaluate_queries(staff_records)
	write_metrics_report(metrics)
	for result in metrics:
		print(
			f"{result['query']}: P@5={result['p_at_5']:.3f}, "
			f"R@5={result['r_at_5']:.3f}"
		)


if __name__ == "__main__":
	main()
