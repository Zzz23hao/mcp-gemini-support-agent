import json
import tempfile
from pathlib import Path

import httpx

from src.eval import run_eval


def test_build_answer_snippet_truncates_long_answers():
    snippet = run_eval.build_answer_snippet("a" * 705, max_chars=10)

    assert snippet == "aaaaaaaaaa..."


def test_find_missing_terms_is_case_insensitive():
    missing = run_eval.find_missing_terms(
        "Clear cache and check MFA.",
        ["clear cache", "MFA", "identity provider"],
    )

    assert missing == ["identity provider"]


def test_find_missing_terms_accepts_known_aliases():
    missing = run_eval.find_missing_terms(
        "Clear your browser's cache, ensure your identity is verified, and check your username.",
        ["clear cache", "identity verification", "credentials"],
    )

    assert missing == []


def test_find_missing_terms_accepts_access_and_setup_aliases():
    missing = run_eval.find_missing_terms(
        "The account is locked; after confirming your identity, we can unlock it. "
        "To set up VPN, make sure manager approval is attached. "
        "The device is enrolled and the database connection timed out.",
        [
            "account locked",
            "identity verification",
            "unlock",
            "setup",
            "approval",
            "enrollment",
            "timeout",
        ],
    )

    assert missing == []


def test_find_missing_terms_accepts_browser_session_aliases():
    missing = run_eval.find_missing_terms(
        "Try a private browsing window or a different web browser after clearing cookies.",
        ["incognito", "cookies"],
    )

    assert missing == []


def test_find_missing_terms_accepts_operational_aliases():
    missing = run_eval.find_missing_terms(
        "The device is compliant. Check the certificate validity period. "
        "Review logs in the logging dashboard, monitor verification, notify security operations, "
        "and confirm active internet access.",
        ["compliance", "expiration", "logging", "verify", "escalate", "network connection"],
    )

    assert missing == []


def test_find_missing_terms_accepts_group_and_cleanup_aliases():
    missing = run_eval.find_missing_terms(
        "Request access to the required repositories or teams. "
        "Free up disk space by removing old downloads and temporary files.",
        ["group", "cleanup"],
    )

    assert missing == []


def test_find_missing_terms_accepts_no_answer_aliases():
    missing = run_eval.find_missing_terms(
        "I am unable to provide private personal information. "
        "That root password is a credential secret, unreleased roadmap details are confidential, "
        "that bypass is not possible, and you should contact Human Resources.",
        ["not sure", "sensitive", "secret", "internal", "cannot", "HR"],
    )

    assert missing == []


def test_find_missing_terms_accepts_incident_term_aliases():
    missing = run_eval.find_missing_terms(
        "The pods are crashlooping after the identity provider outage, "
        "and the pipeline has an indefinite retries pattern.",
        ["CrashLoopBackOff", "authentication", "queue"],
    )

    assert missing == []


def test_score_response_checks_citations_must_include_and_ticket_draft():
    question = {
        "id": "q001",
        "category": "pure_kb",
        "query": "SSO issue",
        "must_include": ["clear cache"],
        "must_cite": True,
        "expect_ticket_draft": False,
    }
    response_body = {
        "answer": "Please clear cache first.",
        "citations": [{"doc_id": "d1", "chunk_id": "c1", "quote": "clear cache"}],
        "ticket_draft": {"created": False, "draft_id": None},
    }

    result = run_eval.score_response(
        question,
        response_body,
        status_code=200,
        latency_ms=123,
        trace_id="trace-1",
        trace_record={"tool_call_count": 1, "tool_names": ["search_kb"]},
    )

    assert result["ok"] is True
    assert result["has_citations"] is True
    assert result["citations_count"] == 1
    assert result["answer_snippet"] == "Please clear cache first."
    assert result["tool_calls_count"] == 1
    assert result["tool_names"] == ["search_kb"]
    assert result["matched_must_include"] == ["clear cache"]
    assert result["missing_must_include"] == []
    assert result["blocked_by_quota"] is False


def test_score_response_fails_when_required_term_is_missing():
    question = {
        "id": "q001",
        "category": "pure_kb",
        "query": "SSO issue",
        "must_include": ["MFA"],
        "must_cite": False,
        "expect_ticket_draft": False,
    }

    result = run_eval.score_response(
        question,
        {"answer": "Clear cache.", "citations": [], "ticket_draft": {"created": False}},
        status_code=200,
        latency_ms=10,
        trace_id=None,
    )

    assert result["ok"] is False
    assert result["missing_must_include"] == ["MFA"]


def test_score_response_marks_quota_errors_separately():
    question = {
        "id": "q004",
        "category": "pure_kb",
        "query": "Account locked",
        "must_include": ["account locked"],
        "must_cite": True,
        "expect_ticket_draft": False,
    }

    result = run_eval.score_response(
        question,
        {"detail": "429 RESOURCE_EXHAUSTED: quota exceeded"},
        status_code=500,
        latency_ms=10,
        trace_id=None,
        error="ClientError: 429 RESOURCE_EXHAUSTED. Quota exceeded.",
    )

    assert result["ok"] is False
    assert result["blocked_by_quota"] is True


def test_score_response_marks_transient_provider_errors_separately():
    question = {
        "id": "q008",
        "category": "pure_kb",
        "query": "Salesforce access",
        "must_include": ["Salesforce"],
        "must_cite": True,
        "expect_ticket_draft": False,
    }

    result = run_eval.score_response(
        question,
        {"detail": "503 UNAVAILABLE: model is currently experiencing high demand"},
        status_code=500,
        latency_ms=10,
        trace_id=None,
        error="ServerError: 503 UNAVAILABLE. high demand, try again later.",
    )

    assert result["ok"] is False
    assert result["blocked_by_provider"] is True


class FakeClient:
    def post(self, url, json):
        return httpx.Response(
            200,
            headers={"x-trace-id": "trace-1"},
            json={
                "answer": "Clear cache and check MFA.",
                "citations": [
                    {
                        "doc_id": "sso_login_troubleshooting",
                        "chunk_id": "sso_login_troubleshooting#003",
                        "quote": "clear cache",
                    }
                ],
                "confidence": 0.8,
                "next_actions": ["Check MFA"],
                "ticket_draft": {"created": False, "draft_id": None},
            },
        )


class RetryThenSuccessClient:
    def __init__(self):
        self.calls = 0

    def post(self, url, json):
        self.calls += 1
        if self.calls == 1:
            return httpx.Response(
                500,
                json={"detail": "ServerError: 503 UNAVAILABLE. high demand."},
            )
        return httpx.Response(
            200,
            headers={"x-trace-id": "trace-1"},
            json={
                "answer": "Clear cache and check MFA.",
                "citations": [{"doc_id": "d1", "chunk_id": "c1", "quote": "MFA"}],
                "confidence": 0.8,
                "next_actions": [],
                "ticket_draft": {"created": False, "draft_id": None},
            },
        )


def test_evaluate_question_uses_trace_log_for_tool_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "agent_traces.jsonl"
        trace_path.write_text(
            json.dumps(
                {
                    "trace_id": "trace-1",
                    "tool_call_count": 1,
                    "tool_names": ["search_kb"],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = run_eval.evaluate_question(
            {
                "id": "q001",
                "query": "SSO issue",
                "must_include": ["MFA"],
                "must_cite": True,
                "expect_ticket_draft": False,
            },
            client=FakeClient(),
            agent_url="http://testserver",
            trace_path=trace_path,
        )

        assert result["ok"] is True
        assert result["trace_id"] == "trace-1"
        assert result["tool_calls_count"] == 1
        assert result["tool_names"] == ["search_kb"]


def test_evaluate_question_retries_transient_provider_errors():
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "agent_traces.jsonl"
        trace_path.write_text(
            json.dumps({"trace_id": "trace-1", "tool_call_count": 1, "tool_names": ["search_kb"]})
            + "\n",
            encoding="utf-8",
        )
        fake_client = RetryThenSuccessClient()

        result = run_eval.evaluate_question(
            {
                "id": "q001",
                "query": "SSO issue",
                "must_include": ["MFA"],
                "must_cite": True,
                "expect_ticket_draft": False,
            },
            client=fake_client,
            agent_url="http://testserver",
            trace_path=trace_path,
            retry_count=1,
            retry_delay_seconds=0,
        )

        assert fake_client.calls == 2
        assert result["ok"] is True


def test_parse_csv_filter_handles_empty_values():
    assert run_eval.parse_csv_filter(None) is None
    assert run_eval.parse_csv_filter("") is None
    assert run_eval.parse_csv_filter("edge_case, no_answer") == {
        "edge_case",
        "no_answer",
    }


def test_filter_questions_by_category_and_ids():
    questions = [
        {"id": "q001", "category": "pure_kb"},
        {"id": "q051", "category": "edge_case"},
        {"id": "q052", "category": "edge_case"},
    ]

    assert run_eval.filter_questions(
        questions,
        categories={"edge_case"},
        ids={"q052"},
    ) == [{"id": "q052", "category": "edge_case"}]


def test_summarize_results_groups_by_category():
    summary = run_eval.summarize_results(
        [
            {"ok": True, "category": "pure_kb", "latency_ms": 100},
            {"ok": False, "category": "pure_kb", "latency_ms": 200},
            {"ok": True, "category": "no_answer", "latency_ms": 300},
        ]
    )

    assert summary["total"] == 3
    assert summary["passed"] == 2
    assert summary["failed"] == 1
    assert summary["blocked_by_quota"] == 0
    assert summary["blocked_by_provider"] == 0
    assert summary["quality_total_excluding_quota"] == 3
    assert summary["quality_passed_excluding_quota"] == 2
    assert summary["quality_failed_excluding_quota"] == 1
    assert summary["quality_pass_rate_excluding_quota"] == 2 / 3
    assert summary["by_category"]["pure_kb"] == {
        "total": 2,
        "passed": 1,
        "failed": 1,
    }


def test_summarize_results_reports_quality_rate_excluding_quota():
    summary = run_eval.summarize_results(
        [
            {"ok": True, "category": "pure_kb", "latency_ms": 100},
            {
                "ok": False,
                "category": "pure_kb",
                "latency_ms": 50,
                "blocked_by_quota": True,
            },
        ]
    )

    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["blocked_by_quota"] == 1
    assert summary["quality_total_excluding_quota"] == 1
    assert summary["quality_passed_excluding_quota"] == 1
    assert summary["quality_failed_excluding_quota"] == 0
    assert summary["quality_pass_rate_excluding_quota"] == 1.0


def test_summarize_results_excludes_provider_errors_from_quality_rate():
    summary = run_eval.summarize_results(
        [
            {"ok": True, "category": "pure_kb", "latency_ms": 100},
            {
                "ok": False,
                "category": "pure_kb",
                "latency_ms": 50,
                "blocked_by_provider": True,
            },
        ]
    )

    assert summary["blocked_by_provider"] == 1
    assert summary["quality_total_excluding_quota"] == 1
    assert summary["quality_pass_rate_excluding_quota"] == 1.0


def test_run_evaluation_respects_limit(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        questions_path = Path(tmpdir) / "questions.jsonl"
        report_path = Path(tmpdir) / "report.json"
        trace_path = Path(tmpdir) / "agent_traces.jsonl"
        questions_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "id": "q001",
                            "category": "pure_kb",
                            "query": "Question 1",
                            "must_include": [],
                            "must_cite": False,
                            "expect_ticket_draft": False,
                        }
                    ),
                    json.dumps(
                        {
                            "id": "q002",
                            "category": "pure_kb",
                            "query": "Question 2",
                            "must_include": [],
                            "must_cite": False,
                            "expect_ticket_draft": False,
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )

        def fake_evaluate_question(
            question,
            *,
            client,
            agent_url,
            trace_path,
            retry_count,
            retry_delay_seconds,
        ):
            return {
                "id": question["id"],
                "category": question["category"],
                "ok": True,
                "latency_ms": 1,
            }

        monkeypatch.setattr(run_eval, "evaluate_question", fake_evaluate_question)

        report = run_eval.run_evaluation(
            questions_path=questions_path,
            report_path=report_path,
            trace_path=trace_path,
            agent_url="http://testserver",
            limit=1,
        )

        assert report["summary"]["total"] == 1
        assert report["results"][0]["id"] == "q001"
        assert report_path.exists()


def test_run_evaluation_filters_by_category(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        questions_path = Path(tmpdir) / "questions.jsonl"
        report_path = Path(tmpdir) / "report.json"
        trace_path = Path(tmpdir) / "agent_traces.jsonl"
        questions_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "id": "q001",
                            "category": "pure_kb",
                            "query": "Question 1",
                            "must_include": [],
                            "must_cite": False,
                            "expect_ticket_draft": False,
                        }
                    ),
                    json.dumps(
                        {
                            "id": "q051",
                            "category": "edge_case",
                            "query": "Question 51",
                            "must_include": [],
                            "must_cite": False,
                            "expect_ticket_draft": False,
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr(
            run_eval,
            "evaluate_question",
            lambda question, **kwargs: {
                "id": question["id"],
                "category": question["category"],
                "ok": True,
                "latency_ms": 1,
            },
        )

        report = run_eval.run_evaluation(
            questions_path=questions_path,
            report_path=report_path,
            trace_path=trace_path,
            agent_url="http://testserver",
            categories={"edge_case"},
        )

        assert report["summary"]["total"] == 1
        assert report["results"][0]["id"] == "q051"
        assert report["filters"]["categories"] == ["edge_case"]
