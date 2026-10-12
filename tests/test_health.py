import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from src.mcp_server.schemas import HealthResponse
from src.mcp_server.tools.health import (
    build_health_checks,
    can_read_json,
    directory_is_writable,
    get_health,
)


class HealthToolTests(TestCase):
    def test_can_read_json_returns_true_for_valid_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "valid.json"
            path.write_text("[]", encoding="utf-8")

            self.assertTrue(can_read_json(path))

    def test_can_read_json_returns_false_for_missing_or_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing.json"
            invalid_path = Path(tmpdir) / "invalid.json"
            invalid_path.write_text("{not-json", encoding="utf-8")

            self.assertFalse(can_read_json(missing_path))
            self.assertFalse(can_read_json(invalid_path))

    def test_directory_is_writable_checks_parent_without_creating_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / "nested" / "feedback.jsonl"

            self.assertFalse(directory_is_writable(target_path))
            self.assertFalse(target_path.exists())

            target_path.parent.mkdir()
            self.assertTrue(directory_is_writable(target_path))
            self.assertFalse(target_path.exists())

    def test_build_health_checks_reports_current_project_dependencies(self):
        checks = build_health_checks()

        self.assertTrue(checks["chunks_json_readable"])
        self.assertTrue(checks["chroma_index_exists"])
        self.assertTrue(checks["tickets_json_readable"])
        self.assertTrue(checks["ticket_drafts_parent_writable"])
        self.assertTrue(checks["feedback_parent_writable"])

    def test_get_health_returns_ok_when_all_checks_pass(self):
        response = get_health()

        self.assertIsInstance(response, HealthResponse)
        self.assertEqual(response.status, "ok")
        self.assertEqual(response.version, "0.1.0")
        self.assertTrue(all(response.checks.values()))

    def test_get_health_returns_degraded_when_any_check_fails(self):
        with patch(
            "src.mcp_server.tools.health.build_health_checks",
            return_value={"chunks_json_readable": True, "tickets_json_readable": False},
        ):
            response = get_health()

        self.assertEqual(response.status, "degraded")
