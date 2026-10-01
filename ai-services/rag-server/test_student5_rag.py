import unittest
from unittest import mock

import requests

import student5_rag as rag


ASSESSMENTS = [
    {"assessment_id": 1, "course_id": "ASD101", "assessment_name": "Assignment 1 - Design Doc",
     "assessment_type": "Assignment", "description": "Software design document", "due_date": "2026-09-05",
     "max_mark": 100, "weight": 20},
    {"assessment_id": 2, "course_id": "ASD101", "assessment_name": "Mid-Semester Test", "assessment_type": "Test",
     "description": "Closed book, 1 hour", "due_date": "2026-09-19", "max_mark": 50, "weight": 15},
    {"assessment_id": 3, "course_id": "ASD101", "assessment_name": "Final Project", "assessment_type": "Project",
     "description": "Team microservices project", "due_date": "2026-10-24", "max_mark": 100, "weight": 40},
    {"assessment_id": 7, "course_id": "DBS101", "assessment_name": "Final Exam", "assessment_type": "Exam",
     "description": "Closed book, 2 hours", "due_date": "2026-11-05", "max_mark": 100, "weight": 45},
]
GRADES = [
    {"grade_id": 1, "assessment_id": 1, "student_id": "STU-1001", "mark": 88, "grade": "HD",
     "course_id": "ASD101", "max_mark": 100},
    {"grade_id": 3, "assessment_id": 2, "student_id": "STU-1001", "mark": 42, "grade": "D",
     "course_id": "ASD101", "max_mark": 50},
    {"grade_id": 12, "assessment_id": 3, "student_id": "STU-1001", "mark": None, "grade": None,
     "course_id": "ASD101", "max_mark": 100},
]


def fake_get_list(path):
    return {"/assessments": ASSESSMENTS, "/grades": GRADES}[path]


class AssessmentRagTests(unittest.TestCase):
    def setUp(self):
        rag._INDEX.update(chunks=[], loaded_at=0.0, warnings=[])
        mock.patch.object(rag, "_audit").start()
        self.get_list = mock.patch.object(rag, "_get_list", side_effect=fake_get_list).start()
        self.generate = mock.patch.object(
            rag, "_generate",
            return_value="ASD101 has Assignment 1 - Design Doc, Mid-Semester Test and Final Project [course-ASD101].",
        ).start()

    def tearDown(self):
        mock.patch.stopall()

    # ---------- corpus ----------
    def test_policy_splits_into_twelve_sections(self):
        chunks = rag.load_policy_chunks()
        self.assertEqual(len(chunks), 12)
        self.assertIn("Grade bands", chunks[4]["section"])

    def test_refresh_indexes_records_and_policy_without_student_ids(self):
        result = rag.refresh_corpus()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["policy_chunk_count"], 12)
        ids = {c["chunk_id"] for c in rag._INDEX["chunks"]}
        self.assertTrue({"assessment-1", "course-ASD101", "course-DBS101", "grades-ASD101"} <= ids)
        all_text = " ".join(c["text"] for c in rag._INDEX["chunks"])
        self.assertNotIn("STU-1001", all_text)  # privacy boundary: no individual results indexed

    def test_refresh_survives_database_outage(self):
        self.get_list.side_effect = requests.ConnectionError("down")
        result = rag.refresh_corpus()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data_chunk_count"], 0)
        self.assertTrue(result["warnings"])

    # ---------- grounded answers ----------
    def test_course_assessment_question_is_grounded_with_citations(self):
        result = rag.answer_question("What assessments do I have for ASD101?", k=6)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["confidence_category"], "high")
        cited = [c["chunk_id"] for c in result["citations"]]
        self.assertIn("course-ASD101", cited)
        self.assertNotIn("course-DBS101", cited[:3])
        self.assertFalse(result["insufficient_evidence"])
        self.generate.assert_called_once()

    def test_policy_question_is_grounded(self):
        result = rag.answer_question("What is the penalty for late submission?")
        self.assertIn(result["confidence_category"], {"high", "medium"})
        self.assertIn("policy-6", [c["chunk_id"] for c in result["citations"]])

    # ---------- abstention ----------
    def test_unrelated_question_abstains_without_calling_the_llm(self):
        result = rag.answer_question("Who won the 2022 football World Cup?")
        self.assertEqual(result["answer"], rag.INSUFFICIENT)
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["confidence_category"], "low")
        self.assertTrue(result["insufficient_evidence"])
        self.generate.assert_not_called()

    def test_unknown_course_code_abstains_instead_of_guessing(self):
        result = rag.answer_question("What assessments are in XYZ999?")
        self.assertTrue(result["insufficient_evidence"])
        self.assertIn("XYZ999", result["agentic_workflow"]["adapt"])
        self.generate.assert_not_called()

    # ---------- grounding guard / fallbacks ----------
    def test_hallucinated_course_code_falls_back_to_extractive_answer(self):
        self.generate.return_value = "You also have an exam in MAT999 [course-ASD101]."
        result = rag.answer_question("What assessments do I have for ASD101?")
        self.assertTrue(result["generator"].startswith("extractive fallback"))
        self.assertIn("[course-ASD101]", result["answer"])
        self.assertNotIn("MAT999", result["answer"])

    def test_ollama_outage_still_returns_grounded_answer(self):
        self.generate.side_effect = requests.ConnectionError("ollama down")
        result = rag.answer_question("What assessments do I have for ASD101?")
        self.assertEqual(result["status"], "success")
        self.assertIn("Ollama unavailable", result["generator"])
        self.assertTrue(result["citations"])


if __name__ == "__main__":
    unittest.main()
