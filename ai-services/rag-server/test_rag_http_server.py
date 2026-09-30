import unittest
from unittest.mock import patch

from rag_http_server import app


class RagHttpServerTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_reports_service(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["service"], "shared-rag")
        self.assertIn("timetable", response.json["domains"])

    def test_answer_requires_question(self):
        response = self.client.post("/answer", json={"query": " "})
        self.assertEqual(response.status_code, 400)

    @patch("rag_http_server.answer_question", return_value={"status": "success", "answer": "Grounded"})
    def test_answer_returns_pipeline_result(self, answer_question):
        response = self.client.post("/answer", json={"query": "Who works in Arts?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["answer"], "Grounded")
        answer_question.assert_called_once_with("Who works in Arts?", 5, caller="student")

    @patch("timetable_rag.answer_question", return_value={"status": "success", "answer": "Policy", "domain": "timetable"})
    def test_timetable_domain_is_dispatched(self, timetable_answer):
        response = self.client.post("/answer", json={"query": "When do sessions clash?", "domain": "timetable"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["domain"], "timetable")
        timetable_answer.assert_called_once_with("When do sessions clash?", 5, caller="student")

    def test_unknown_domain_is_rejected(self):
        response = self.client.post("/answer", json={"query": "anything", "domain": "weather"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("timetable", response.json["domains"])


if __name__ == "__main__":
    unittest.main()