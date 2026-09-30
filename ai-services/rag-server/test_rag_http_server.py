import unittest
from unittest.mock import patch

from rag_http_server import app


class RagHttpServerTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_reports_service(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["service"], "student2-rag")

    def test_answer_requires_question(self):
        response = self.client.post("/answer", json={"query": " "})
        self.assertEqual(response.status_code, 400)

    @patch("rag_http_server.answer_question", return_value={"status": "success", "answer": "Grounded"})
    def test_answer_returns_pipeline_result(self, answer_question):
        response = self.client.post("/answer", json={"query": "Who works in Arts?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["answer"], "Grounded")
        answer_question.assert_called_once_with("Who works in Arts?", 5, caller="student")


if __name__ == "__main__":
    unittest.main()