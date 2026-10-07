import unittest
from unittest.mock import patch

import rag_pipeline


class RagPipelineTests(unittest.TestCase):
    def test_staff_records_become_citable_chunks(self):
        chunks = rag_pipeline._staff_chunks(
            [
                {
                    "staff_id": 7,
                    "given_name": "Tess",
                    "family_name": "Ng",
                    "department": "Arts",
                    "employment_type": "Part-time",
                }
            ]
        )

        self.assertEqual(chunks[0]["chunk_id"], "staff-7")
        self.assertEqual(chunks[0]["source_id"], "student2-database:/staff/7")
        self.assertIn("Tess Ng", chunks[0]["text"])
        self.assertEqual(chunks[0]["metadata"]["department"], "Arts")

    def test_retrieval_validates_query_and_bounds_result_count(self):
        self.assertEqual(rag_pipeline.retrieve_context(" ")["error"], "query is required")
        self.assertEqual(rag_pipeline.retrieve_context("staff", k=0)["error"], "k must be a positive integer")

    def test_retrieval_returns_provenance_for_matches(self):
        class Collection:
            def count(self):
                return 1

            def get(self, include):
                self.metadata_fields = include
                return {"metadatas": [{"department": "Arts"}]}

            def query(self, **kwargs):
                self.n_results = kwargs["n_results"]
                self.where = kwargs.get("where")
                return {
                    "ids": [["staff-7"]],
                    "documents": [["Tess Ng works in Arts."]],
                    "metadatas": [[{"source_id": "student2-database:/staff/7"}]],
                    "distances": [[0.2]],
                }

        collection = Collection()
        with patch.object(rag_pipeline, "_embed_texts", return_value=[[0.1, 0.2]]):
            result = rag_pipeline.retrieve_context("Arts staff", k=99, collection=collection)

        self.assertEqual(result["status"], "success")
        self.assertEqual(collection.n_results, rag_pipeline.MAX_RESULTS)
        self.assertEqual(collection.where, {"department": "Arts"})
        self.assertEqual(result["results"][0]["source_id"], "student2-database:/staff/7")

    def test_low_confidence_answer_abstains(self):
        retrieval = {
            "status": "success",
            "results": [{"chunk_id": "staff-7", "source_id": "source", "distance": 0.8, "text": "irrelevant"}],
        }
        with patch.object(rag_pipeline, "retrieve_context", return_value=retrieval):
            result = rag_pipeline.answer_question("unsupported question")

        self.assertEqual(result["confidence_category"], "low")
        self.assertIn("Insufficient evidence", result["answer"])
        self.assertEqual(result["citations"], [])
        self.assertIn("Abstained", result["agentic_workflow"]["adapt"])

    @patch.object(rag_pipeline.requests, "post")
    @patch.object(rag_pipeline.requests, "get")
    def test_staff_count_uses_live_records_and_cites_every_match(self, get_staff, ollama_request):
        staff_records = [
            {"staff_id": 2, "given_name": "Nero", "family_name": "Garcia", "department": "Arts"},
            {"staff_id": 8, "given_name": "Tiffany", "family_name": "Day", "department": "Arts"},
            {"staff_id": 9, "given_name": "Jane", "family_name": "Remover", "department": "Arts"},
            {"staff_id": 10, "given_name": "Dave", "family_name": "Banks", "department": "Finance"},
        ]
        get_staff.return_value.json.return_value = staff_records

        result = rag_pipeline.answer_question("how many staff are in arts?")

        self.assertEqual(result["status"], "success")
        self.assertIn("There are 3 staff members in the Arts department.", result["answer"])
        self.assertEqual(
            [citation["chunk_id"] for citation in result["citations"]],
            ["staff-2", "staff-8", "staff-9"],
        )
        self.assertEqual(result["confidence_category"], "high")
        ollama_request.assert_not_called()

    @patch.object(rag_pipeline.requests, "post")
    @patch.object(rag_pipeline.requests, "get")
    def test_staff_employment_filter_returns_all_six_full_time_members(self, get_staff, ollama_request):
        staff_records = [
            {"staff_id": 1, "given_name": "Jet", "family_name": "Smith", "employment_type": "Full-time"},
            {"staff_id": 2, "given_name": "Nero", "family_name": "Garcia", "employment_type": "Full-time"},
            {"staff_id": 3, "given_name": "Denver", "family_name": "Mesa", "employment_type": "Part-time"},
            {"staff_id": 4, "given_name": "Leona", "family_name": "Pilapil", "employment_type": "Part-time"},
            {"staff_id": 5, "given_name": "Jerome", "family_name": "Wilson", "employment_type": "Full-time"},
            {"staff_id": 6, "given_name": "Angelina", "family_name": "Kim", "employment_type": "Full-time"},
            {"staff_id": 7, "given_name": "Joey", "family_name": "Wu", "employment_type": "Part-time"},
            {"staff_id": 8, "given_name": "Tiffany", "family_name": "Day", "employment_type": "Part-time"},
            {"staff_id": 9, "given_name": "Jane", "family_name": "Remover", "employment_type": "Full-time"},
            {"staff_id": 10, "given_name": "Dave", "family_name": "Banks", "employment_type": "Full-time"},
        ]
        get_staff.return_value.json.return_value = staff_records

        result = rag_pipeline.answer_question("which staff members have full time contracts?")

        self.assertEqual(result["status"], "success")
        self.assertIn("Jet Smith, Nero Garcia, Jerome Wilson, Angelina Kim, Jane Remover, Dave Banks", result["answer"])
        self.assertEqual(
            [citation["chunk_id"] for citation in result["citations"]],
            ["staff-1", "staff-2", "staff-5", "staff-6", "staff-9", "staff-10"],
        )
        self.assertEqual(result["retrieval_summary"]["retrieved_count"], 6)
        ollama_request.assert_not_called()

    def test_weak_nearest_match_abstains_without_calling_model(self):
        retrieval = {
            "status": "success",
            "results": [
                {
                    "chunk_id": "staff-2",
                    "source_id": "source",
                    "distance": 0.517,
                    "text": "Staff member works in Arts.",
                }
            ],
        }
        with patch.object(rag_pipeline, "retrieve_context", return_value=retrieval):
            with patch.object(rag_pipeline.requests, "post") as ollama_request:
                result = rag_pipeline.answer_question("What is the rector salary?")

        self.assertEqual(result["confidence_category"], "low")
        self.assertEqual(result["citations"], [])
        ollama_request.assert_not_called()

    def test_precision_and_recall_at_five(self):
        from rag_eval import precision_recall_at_k

        precision, recall = precision_recall_at_k(
            ["staff-1", "staff-2", "staff-3", "staff-4", "staff-5"],
            {"staff-2", "staff-5", "staff-8"},
        )

        self.assertEqual(precision, 0.4)
        self.assertAlmostEqual(recall, 2 / 3)


if __name__ == "__main__":
    unittest.main()