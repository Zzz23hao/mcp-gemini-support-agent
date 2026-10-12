import json
import tempfile
from pathlib import Path

from src.agent_api.schemas import ChatResponse
from src.agent_api.tracing import (
    build_agent_trace_record,
    estimate_tokens,
    infer_error_type,
    log_agent_trace,
)


def test_estimate_tokens_uses_rough_character_based_estimate():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 20) == 5


def test_build_agent_trace_record_includes_observability_fields():
    response = ChatResponse(
        answer="Use the SSO troubleshooting steps.",
        citations=[],
        confidence=0.4,
        next_actions=["Contact IT support"],
        ticket_draft={"created": False, "draft_id": None},
    )

    record = build_agent_trace_record(
        trace_id="trace-1",
        session_id="session-1",
        query="SSO login failed",
        status="success",
        latency_ms=123,
        tool_names=["search_kb"],
        response=response,
    )

    assert record["trace_id"] == "trace-1"
    assert record["session_id"] == "session-1"
    assert record["query"] == "SSO login failed"
    assert record["status"] == "success"
    assert record["event"] == "agent_chat_trace"
    assert record["tool_calls"] == ["search_kb"]
    assert record["tool_call_count"] == 1
    assert record["tool_names"] == ["search_kb"]
    assert record["latency_ms"] == 123
    assert record["estimated_input_tokens"] > 0
    assert record["estimated_output_tokens"] > 0
    assert record["error_type"] is None
    assert record["error"] is None
    assert "created_at" in record


def test_infer_error_type_uses_exception_prefix():
    assert infer_error_type("RuntimeError: Tool call failed") == "RuntimeError"
    assert infer_error_type(None) is None


def test_log_agent_trace_appends_jsonl_record_and_emits_stdout_json(capsys):
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "agent_traces.jsonl"

        log_agent_trace(
            trace_id="trace-1",
            session_id="session-1",
            query="SSO login failed",
            status="error",
            latency_ms=5000,
            tool_names=["search_kb"],
            error="RuntimeError: Tool call failed: search_kb",
            error_type="RuntimeError",
            path=trace_path,
        )

        lines = trace_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1

        record = json.loads(lines[0])
        assert record["trace_id"] == "trace-1"
        assert record["status"] == "error"
        assert record["tool_calls"] == ["search_kb"]
        assert record["error_type"] == "RuntimeError"
        assert record["error"] == "RuntimeError: Tool call failed: search_kb"

        stdout_record = json.loads(capsys.readouterr().out)
        assert stdout_record["trace_id"] == "trace-1"
        assert stdout_record["session_id"] == "session-1"
        assert stdout_record["latency_ms"] == 5000
        assert stdout_record["tool_calls"] == ["search_kb"]
        assert stdout_record["error_type"] == "RuntimeError"
