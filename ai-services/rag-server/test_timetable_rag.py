import unittest
from unittest import mock

import timetable_rag as rag_pipeline


def fake_embed(texts, kind):
    """Deterministic embeddings: questions about clashes/rooms align with section 4."""
    vectors = []
    for text in texts:
        lowered = text.lower()
        if "clash" in lowered:
            vectors.append([1.0, 0.0, 0.0])
        elif "semester" in lowered:
            vectors.append([0.7, 0.7, 0.0])
        else:
            vectors.append([0.0, 0.0, 1.0])
    return vectors


class RagPipelineTests(unittest.TestCase):
    def setUp(self):
        rag_pipeline._INDEX["chunks"], rag_pipeline._INDEX["vectors"] = [], []
        self.embed = mock.patch.object(rag_pipeline, "_embed", side_effect=fake_embed).start()
        self.audit = mock.patch.object(rag_pipeline, "_audit").start()
        self.generate = mock.patch.object(
            rag_pipeline, "_generate", return_value="Back-to-back sessions do not clash [policy-4]."
        ).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_policy_splits_into_twelve_sections(self):
        chunks = rag_pipeline.load_chunks()
        self.assertEqual(len(chunks), 12)
        self.assertEqual(chunks[3]["chunk_id"], "policy-4")
        self.assertIn("Room clash rule", chunks[3]["section"])

    def test_relevant_question_is_answered_with_citations(self):
        result = rag_pipeline.answer_question("When do two sessions clash?")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["confidence_category"], "high")
        self.assertIn("policy-4", [c["chunk_id"] for c in result["citations"]])
        self.generate.assert_called_once()

    def test_unrelated_question_abstains_without_calling_the_llm(self):
        with mock.patch.object(rag_pipeline, "_embed", side_effect=lambda texts, kind: [
            [0.0, 1.0, 0.0] if kind == "query" else [1.0, 0.0, 0.0] for _ in texts
        ]):
            result = rag_pipeline.answer_question("What is the capital of France?")
        self.assertEqual(result["confidence_category"], "low")
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["answer"], rag_pipeline.INSUFFICIENT)
        self.generate.assert_not_called()

    def test_empty_query_is_rejected(self):
        self.assertEqual(rag_pipeline.answer_question("   ")["status"], "error")


if __name__ == "__main__":
    unittest.main()
