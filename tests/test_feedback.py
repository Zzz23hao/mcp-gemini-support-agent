import json
import tempfile
from pathlib import Path
from unittest import TestCase

from pydantic import ValidationError

from src.mcp_server.schemas import FeedbackRequest
from src.mcp_server.tools.feedback import build_feedback_record, log_feedback


class FeedbackToolTests(TestCase):
    def test_build_feedback_record_includes_payload_and_timestamp(self):
        record = build_feedback_record(
            FeedbackRequest(session_id="session-1", rating=4, comment="Helpful answer.")
        )

        self.assertEqual(record["session_id"], "session-1")
        self.assertEqual(record["rating"], 4)
        self.assertEqual(record["comment"], "Helpful answer.")
        self.assertIn("created_at", record)

    def test_log_feedback_appends_jsonl_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feedback_path = Path(tmpdir) / "feedback.jsonl"

            response = log_feedback(
                FeedbackRequest(session_id="session-1", rating=5, comment="Solved it."),
                path=feedback_path,
            )

            self.assertTrue(response.logged)
            lines = feedback_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)

            record = json.loads(lines[0])
            self.assertEqual(record["session_id"], "session-1")
            self.assertEqual(record["rating"], 5)
            self.assertEqual(record["comment"], "Solved it.")

    def test_log_feedback_appends_without_overwriting_existing_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feedback_path = Path(tmpdir) / "feedback.jsonl"

            log_feedback(FeedbackRequest(session_id="session-1", rating=5), path=feedback_path)
            log_feedback(FeedbackRequest(session_id="session-2", rating=3), path=feedback_path)

            lines = feedback_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["session_id"], "session-1")
            self.assertEqual(json.loads(lines[1])["session_id"], "session-2")

    def test_feedback_request_rejects_invalid_rating(self):
        with self.assertRaises(ValidationError):
            FeedbackRequest(session_id="session-1", rating=6)
