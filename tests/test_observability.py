from contextlib import contextmanager

from fastapi.testclient import TestClient
import httpx
from google.genai import types

from src.agent_api import main
from src.agent_api import observability


class FakeSpan:
    def __init__(self):
        self.attributes = {}
        self.exceptions = []

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def record_exception(self, error):
        self.exceptions.append(error)

    def set_status(self, status):
        self.status = status


def test_mark_span_error_records_exception_type():
    span = FakeSpan()
    error = RuntimeError("tool failed")

    observability.mark_span_error(span, error)

    assert span.exceptions == [error]
    assert span.attributes["error.type"] == "RuntimeError"


def test_execute_mcp_tool_creates_tool_call_span(monkeypatch):
    span_records = []

    @contextmanager
    def fake_tool_call_span(function_call, *, url, attempt):
        span_records.append(
            {
                "tool_name": function_call.name,
                "url": url,
                "attempt": attempt,
            }
        )
        yield FakeSpan()

    class FakeHttpClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def post(self, url, json):
            return httpx.Response(
                200,
                json={"results": []},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(main, "tool_call_span", fake_tool_call_span)
    monkeypatch.setattr(main.httpx, "Client", FakeHttpClient)

    result = main.execute_mcp_tool(
        types.FunctionCall(name="search_kb", args={"query": "SSO", "top_k": 3}),
        mcp_server_url="http://testserver",
    )

    assert result == {"results": []}
    assert span_records == [
        {
            "tool_name": "search_kb",
            "url": "http://testserver/tool/search_kb",
            "attempt": 1,
        }
    ]


def test_chat_endpoint_creates_agent_span(monkeypatch):
    span = FakeSpan()
    span_inputs = []

    @contextmanager
    def fake_agent_chat_span(*, trace_id, session_id, query):
        span_inputs.append(
            {
                "trace_id": trace_id,
                "session_id": session_id,
                "query": query,
            }
        )
        yield span

    def fake_run_agent_chat(payload, *, trace_id=None):
        return main.ChatResponse(
            answer="Use SSO troubleshooting steps.",
            citations=[],
            confidence=0.4,
            next_actions=[],
            ticket_draft={"created": False, "draft_id": None},
        )

    monkeypatch.setattr(main, "agent_chat_span", fake_agent_chat_span)
    monkeypatch.setattr(main, "create_trace_id", lambda: "trace-test")
    monkeypatch.setattr(main, "run_agent_chat", fake_run_agent_chat)

    client = TestClient(main.app)
    result = client.post(
        "/chat",
        json={"query": "I cannot log in with SSO", "session_id": "demo1"},
    )

    assert result.status_code == 200
    assert span_inputs == [
        {
            "trace_id": "trace-test",
            "session_id": "demo1",
            "query": "I cannot log in with SSO",
        }
    ]
    assert span.attributes["agent.status"] == "success"
    assert span.attributes["agent.citations_count"] == 0
    assert span.attributes["agent.ticket_draft_created"] is False
