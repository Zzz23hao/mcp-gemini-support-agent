from fastapi.testclient import TestClient
from google.genai import types
import pytest

from src.agent_api import main
from src.agent_api.schemas import ChatResponse


client = TestClient(main.app)


def parsed_response(answer: str = "Use the SSO troubleshooting steps."):
    return types.GenerateContentResponse(
        parsed=ChatResponse(
            answer=answer,
            citations=[
                {
                    "doc_id": "sso_login_troubleshooting",
                    "chunk_id": "sso_login_troubleshooting#001",
                    "quote": "Verify that the user is assigned to the application.",
                }
            ],
            confidence=0.8,
            next_actions=["Verify application assignment"],
            ticket_draft={"created": False, "draft_id": None},
        )
    )


def parsed_response_with_confidence(confidence: float):
    return types.GenerateContentResponse(
        parsed=ChatResponse(
            answer="Use the SSO troubleshooting steps.",
            citations=[
                {
                    "doc_id": "sso_login_troubleshooting",
                    "chunk_id": "sso_login_troubleshooting#001",
                    "quote": "Verify that the user is assigned to the application.",
                }
            ],
            confidence=confidence,
            next_actions=["Verify application assignment"],
            ticket_draft={"created": False, "draft_id": None},
        )
    )


def parsed_uncited_response_with_confidence(confidence: float):
    return types.GenerateContentResponse(
        parsed=ChatResponse(
            answer="Evidence is limited, so contact IT support.",
            citations=[],
            confidence=confidence,
            next_actions=["Contact IT support"],
            ticket_draft={"created": False, "draft_id": None},
        )
    )


def function_call_response():
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name="search_kb",
                                args={"query": "SSO login failed", "top_k": 5},
                            )
                        )
                    ],
                )
            )
        ]
    )


def single_function_call_response(name: str, args: dict):
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                name=name,
                                args=args,
                            )
                        )
                    ],
                )
            )
        ]
    )


def test_tool_call_generate_config_does_not_request_json_response():
    config = main.build_generate_config(enable_tools=True)

    assert config.tools is not None
    assert config.response_mime_type is None
    assert config.response_schema is None


def test_final_answer_generate_config_does_not_include_tools():
    config = main.build_generate_config(enable_tools=False)

    assert config.tools is None
    assert config.response_mime_type == "application/json"
    assert config.response_schema == ChatResponse


def test_chat_endpoint_returns_trace_id_header(monkeypatch):
    generated_trace_ids = []

    def fake_run_agent_chat(payload, *, trace_id=None):
        generated_trace_ids.append(trace_id)
        return parsed_response().parsed

    monkeypatch.setattr(main, "create_trace_id", lambda: "trace-test-001")
    monkeypatch.setattr(main, "run_agent_chat", fake_run_agent_chat)

    response = client.post(
        "/chat",
        json={"query": "Can you approve my vacation request?", "session_id": "demo1"},
    )

    assert response.status_code == 200
    assert response.headers["x-trace-id"] == "trace-test-001"
    assert generated_trace_ids == ["trace-test-001"]


def test_chat_endpoint_returns_direct_gemini_json(monkeypatch):
    generated_calls = []
    generated_contents = []
    trace_records = []
    appended_turns = []

    def fake_generate_content(client, contents, enable_tools):
        generated_calls.append(enable_tools)
        generated_contents.append(contents)
        if enable_tools:
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="No tool call needed.")],
                        )
                    )
                ]
            )
        return parsed_response()

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(
        main,
        "log_agent_trace",
        lambda **kwargs: trace_records.append(kwargs),
    )
    monkeypatch.setattr(
        main,
        "get_session_history",
        lambda session_id: [
            {
                "user": "I cannot log in",
                "assistant": "Try SSO troubleshooting.",
                "citations": [],
                "ticket_draft": {"created": False, "draft_id": None},
            }
        ],
    )
    monkeypatch.setattr(
        main,
        "append_session_turn",
        lambda session_id, query, response: appended_turns.append(
            {
                "session_id": session_id,
                "query": query,
                "answer": response.answer,
            }
        ),
    )

    response = client.post(
        "/chat",
        json={"query": "Can you approve my vacation request?", "session_id": "demo1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Use the SSO troubleshooting steps."
    assert body["citations"][0]["doc_id"] == "sso_login_troubleshooting"
    assert body["ticket_draft"] == {"created": False, "draft_id": None}
    assert generated_calls == [True, False]
    assert "conversation_history" in generated_contents[0]
    assert "Try SSO troubleshooting." in generated_contents[0]
    assert "original_user_query: Can you approve my vacation request?" in generated_contents[1]
    assert "Try SSO troubleshooting." in generated_contents[1]
    assert "Tool results already collected" in generated_contents[1]
    assert trace_records[0]["status"] == "success"
    assert trace_records[0]["session_id"] == "demo1"
    assert trace_records[0]["tool_names"] == []
    assert trace_records[0]["response"].answer == "Use the SSO troubleshooting steps."
    assert appended_turns == [
        {
            "session_id": "demo1",
            "query": "Can you approve my vacation request?",
            "answer": "Use the SSO troubleshooting steps.",
        }
    ]


def test_chat_endpoint_caps_supported_confidence(monkeypatch):
    def fake_generate_content(client, contents, enable_tools):
        if enable_tools:
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="No tool call needed.")],
                        )
                    )
                ]
            )
        return parsed_response_with_confidence(1.0)

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)

    response = client.post(
        "/chat",
        json={"query": "Can you approve my vacation request?", "session_id": "demo1"},
    )

    assert response.status_code == 200
    assert response.json()["confidence"] == 0.9


def test_chat_endpoint_adds_kb_when_support_query_has_no_model_tool_call(monkeypatch):
    generated_contents = []
    trace_records = []

    def fake_generate_content(client, contents, enable_tools):
        generated_contents.append(contents)
        if enable_tools:
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="No tool call needed.")],
                        )
                    )
                ]
            )
        return parsed_response("I found software approval evidence.")

    def fake_execute_mcp_tool(function_call):
        assert function_call.name == "search_kb"
        return {
            "results": [
                {
                    "doc_id": "software_install_request",
                    "chunk_id": "software_install_request#003",
                    "heading": "Troubleshooting Steps",
                    "text": "Confirm approval before installing software.",
                    "score": 4.0,
                }
            ]
        }

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(main, "execute_mcp_tool", fake_execute_mcp_tool)
    monkeypatch.setattr(
        main,
        "log_agent_trace",
        lambda **kwargs: trace_records.append(kwargs),
    )

    response = client.post(
        "/chat",
        json={"query": "I need a software installation approved.", "session_id": "demo1"},
    )

    assert response.status_code == 200
    assert '"tool_name": "search_kb"' in generated_contents[1]
    assert trace_records[0]["tool_names"] == ["search_kb"]


def test_chat_endpoint_caps_uncited_confidence(monkeypatch):
    def fake_generate_content(client, contents, enable_tools):
        if enable_tools:
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="No tool call needed.")],
                        )
                    )
                ]
            )
        return parsed_uncited_response_with_confidence(0.95)

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)

    response = client.post(
        "/chat",
        json={"query": "Unknown internal issue", "session_id": "demo1"},
    )

    assert response.status_code == 200
    assert response.json()["confidence"] == 0.4


def test_chat_endpoint_executes_function_call_then_returns_final_json(monkeypatch):
    generated_contents = []
    trace_records = []

    def fake_generate_content(client, contents, enable_tools):
        generated_contents.append(contents)
        if len(generated_contents) == 1:
            assert enable_tools is True
            return function_call_response()
        assert enable_tools is False
        return parsed_response("I found KB evidence for the SSO issue.")

    def fake_execute_mcp_tool(function_call):
        assert function_call.name == "search_kb"
        assert function_call.args == {"query": "SSO login failed", "top_k": 5}
        return {
            "results": [
                {
                    "doc_id": "sso_login_troubleshooting",
                    "chunk_id": "sso_login_troubleshooting#001",
                    "heading": "Troubleshooting Steps",
                    "text": "Verify that the user is assigned to the application.",
                    "score": 4.0,
                }
            ]
        }

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(main, "execute_mcp_tool", fake_execute_mcp_tool)
    monkeypatch.setattr(
        main,
        "log_agent_trace",
        lambda **kwargs: trace_records.append(kwargs),
    )

    response = client.post(
        "/chat",
        json={"query": "SSO login failed", "session_id": "demo1"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "I found KB evidence for the SSO issue."
    assert len(generated_contents) == 2
    assert "original_user_query: SSO login failed" in generated_contents[1]
    assert '"tool_name": "search_kb"' in generated_contents[1]
    assert "Verify that the user is assigned to the application." in generated_contents[1]
    assert trace_records[0]["status"] == "success"
    assert trace_records[0]["tool_names"] == ["search_kb"]
    assert trace_records[0]["response"].answer == "I found KB evidence for the SSO issue."


def test_chat_endpoint_adds_ticket_history_for_similar_case_queries(monkeypatch):
    generated_contents = []
    executed_tools = []

    def fake_generate_content(client, contents, enable_tools):
        generated_contents.append(contents)
        if len(generated_contents) == 1:
            return function_call_response()
        return parsed_response("I found KB and similar ticket evidence.")

    def fake_execute_mcp_tool(function_call):
        executed_tools.append(function_call.name)
        if function_call.name == "search_kb":
            return {"results": []}
        if function_call.name == "search_tickets":
            return {"results": [{"id": "TCK-1", "title": "Similar SSO case"}]}
        raise AssertionError(f"Unexpected tool: {function_call.name}")

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(main, "execute_mcp_tool", fake_execute_mcp_tool)

    response = client.post(
        "/chat",
        json={
            "query": "SSO is still failing. Have we seen similar cases before?",
            "session_id": "demo1",
        },
    )

    assert response.status_code == 200
    assert executed_tools == ["search_kb", "search_tickets"]
    assert '"tool_name": "search_tickets"' in generated_contents[1]


def test_chat_endpoint_adds_kb_for_ticket_history_when_model_only_searches_tickets(
    monkeypatch,
):
    generated_contents = []
    executed_tools = []

    def fake_generate_content(client, contents, enable_tools):
        generated_contents.append(contents)
        if len(generated_contents) == 1:
            return single_function_call_response(
                "search_tickets",
                {
                    "query": "SSO cache issue similar cases",
                    "status": None,
                    "time_range": None,
                },
            )
        return parsed_response("I found similar tickets and KB evidence.")

    def fake_execute_mcp_tool(function_call):
        executed_tools.append(function_call.name)
        if function_call.name == "search_tickets":
            return {"results": [{"id": "TCK-1", "title": "Similar SSO case"}]}
        if function_call.name == "search_kb":
            return {
                "results": [
                    {
                        "doc_id": "sso_login_troubleshooting",
                        "chunk_id": "sso_login_troubleshooting#003",
                        "heading": "Troubleshooting Steps",
                        "text": "Verify MFA enrollment is complete.",
                        "score": 4.0,
                    }
                ]
            }
        raise AssertionError(f"Unexpected tool: {function_call.name}")

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(main, "execute_mcp_tool", fake_execute_mcp_tool)

    response = client.post(
        "/chat",
        json={
            "query": "SSO login is failing. Have we seen similar cases before?",
            "session_id": "demo1",
        },
    )

    assert response.status_code == 200
    assert executed_tools == ["search_tickets", "search_kb"]
    assert '"tool_name": "search_tickets"' in generated_contents[1]
    assert '"tool_name": "search_kb"' in generated_contents[1]


def test_chat_endpoint_adds_kb_evidence_for_ticket_draft_only_call(monkeypatch):
    generated_contents = []
    executed_tools = []

    def fake_generate_content(client, contents, enable_tools):
        generated_contents.append(contents)
        if len(generated_contents) == 1:
            return single_function_call_response(
                "create_ticket_draft",
                {
                    "title": "VPN outage for remote employees",
                    "description": "VPN is down for several remote employees.",
                    "priority": "high",
                    "tags": ["vpn"],
                    "assigned_group": "Network Team",
                    "evidence_ids": [],
                },
            )
        return parsed_response("I created the draft with supporting KB evidence.")

    def fake_execute_mcp_tool(function_call):
        executed_tools.append(function_call.name)
        if function_call.name == "create_ticket_draft":
            return {"draft_id": "DRAFT-0001", "created": True}
        if function_call.name == "search_kb":
            return {
                "results": [
                    {
                        "doc_id": "vpn_connection_failed",
                        "chunk_id": "vpn_connection_failed#003",
                        "heading": "Troubleshooting Steps",
                        "text": "Restart the VPN client and collect remote network details.",
                        "score": 4.0,
                    }
                ]
            }
        raise AssertionError(f"Unexpected tool: {function_call.name}")

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(main, "execute_mcp_tool", fake_execute_mcp_tool)

    response = client.post(
        "/chat",
        json={
            "query": "VPN is down for several remote employees. Create a ticket draft.",
            "session_id": "demo1",
        },
    )

    assert response.status_code == 200
    assert executed_tools == ["create_ticket_draft", "search_kb"]
    assert '"tool_name": "create_ticket_draft"' in generated_contents[1]
    assert '"tool_name": "search_kb"' in generated_contents[1]


def test_chat_endpoint_creates_supplemental_ticket_draft_when_requested(monkeypatch):
    generated_contents = []
    executed_tools = []

    def fake_generate_content(client, contents, enable_tools):
        generated_contents.append(contents)
        if len(generated_contents) == 1:
            return function_call_response()
        return parsed_response("I created the requested ticket draft.")

    def fake_execute_mcp_tool(function_call):
        executed_tools.append(function_call.name)
        if function_call.name == "search_kb":
            return {
                "results": [
                    {
                        "doc_id": "database_connection_issue",
                        "chunk_id": "database_connection_issue#003",
                        "heading": "Troubleshooting Steps",
                        "text": "Check firewall rules.",
                        "score": 4.0,
                    }
                ]
            }
        if function_call.name == "create_ticket_draft":
            assert function_call.args["assigned_group"] is not None
            assert "database_connection_issue#003" in function_call.args["evidence_ids"]
            return {"draft_id": "DRAFT-9001", "created": True}
        raise AssertionError(f"Unexpected tool: {function_call.name}")

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(main, "execute_mcp_tool", fake_execute_mcp_tool)

    response = client.post(
        "/chat",
        json={
            "query": "The production database connection is timing out. Please prepare a ticket draft.",
            "session_id": "demo1",
        },
    )

    assert response.status_code == 200
    assert executed_tools == ["search_kb", "create_ticket_draft"]
    assert '"tool_name": "create_ticket_draft"' in generated_contents[1]


def test_chat_endpoint_creates_supplemental_ticket_draft_without_model_tool_call(monkeypatch):
    generated_contents = []
    executed_tools = []

    def fake_generate_content(client, contents, enable_tools):
        generated_contents.append(contents)
        if enable_tools:
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            role="model",
                            parts=[types.Part(text="No tool call needed.")],
                        )
                    )
                ]
            )
        return types.GenerateContentResponse(
            parsed=ChatResponse(
                answer="I created a ticket draft for the TLS certificate warning.",
                citations=[],
                confidence=0.8,
                next_actions=["Review draft DRAFT-9002"],
                ticket_draft={"created": True, "draft_id": "DRAFT-9002"},
            )
        )

    def fake_execute_mcp_tool(function_call):
        executed_tools.append(function_call.name)
        if function_call.name == "search_kb":
            return {
                "results": [
                    {
                        "doc_id": "tls_certificate_warning",
                        "chunk_id": "tls_certificate_warning#003",
                        "heading": "Troubleshooting Steps",
                        "text": "Check certificate expiration and chain validity.",
                        "score": 4.0,
                    }
                ]
            }
        if function_call.name == "create_ticket_draft":
            assert function_call.args["priority"] == "high"
            assert function_call.args["assigned_group"] == "Platform Engineering"
            assert "tls_certificate_warning#003" in function_call.args["evidence_ids"]
            return {"draft_id": "DRAFT-9002", "created": True}
        raise AssertionError(f"Unexpected tool: {function_call.name}")

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(main, "execute_mcp_tool", fake_execute_mcp_tool)

    response = client.post(
        "/chat",
        json={
            "query": "Please create a ticket draft for a TLS certificate warning affecting production customers.",
            "session_id": "demo1",
        },
    )

    assert response.status_code == 200
    assert response.json()["ticket_draft"] == {
        "created": True,
        "draft_id": "DRAFT-9002",
    }
    assert executed_tools == ["search_kb", "create_ticket_draft"]
    assert '"tool_name": "search_kb"' in generated_contents[1]
    assert '"tool_name": "create_ticket_draft"' in generated_contents[1]


def test_chat_endpoint_skips_unsolicited_ticket_draft(monkeypatch):
    generated_contents = []
    executed_tools = []

    def fake_generate_content(client, contents, enable_tools):
        generated_contents.append(contents)
        if len(generated_contents) == 1:
            return single_function_call_response(
                "create_ticket_draft",
                {
                    "title": "Image pull issue",
                    "description": "Deployment has ImagePullBackOff.",
                    "priority": "medium",
                    "tags": ["kubernetes"],
                    "assigned_group": "Platform Engineering",
                    "evidence_ids": [],
                },
            )
        return parsed_response("Check image tag and registry credentials.")

    def fake_execute_mcp_tool(function_call):
        executed_tools.append(function_call.name)
        raise AssertionError("Unsolicited create_ticket_draft should not execute")

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(main, "generate_content", fake_generate_content)
    monkeypatch.setattr(main, "execute_mcp_tool", fake_execute_mcp_tool)

    response = client.post(
        "/chat",
        json={
            "query": "ImagePullBackOff is happening. What should we check?",
            "session_id": "demo1",
        },
    )

    assert response.status_code == 200
    assert executed_tools == []
    assert "create_ticket_draft" not in generated_contents[1]


def test_parse_final_chat_response_accepts_json_text():
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=(
                                '{"answer":"Escalate safely.",'
                                '"citations":[],'
                                '"confidence":0.3,'
                                '"next_actions":["Contact IT support"],'
                                '"ticket_draft":{"created":false,"draft_id":null}}'
                            )
                        )
                    ],
                )
            )
        ]
    )

    parsed = main.parse_final_chat_response(response)

    assert parsed.answer == "Escalate safely."
    assert parsed.confidence == 0.3


def test_parse_final_chat_response_repairs_missing_ticket_draft_id():
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=(
                                '{"answer":"Draft created.",'
                                '"citations":[],'
                                '"confidence":0.7,'
                                '"next_actions":["Review the draft"],'
                                '"ticket_draft":{"created":true,"draft_id":null}}'
                            )
                        )
                    ],
                )
            )
        ]
    )

    parsed = main.parse_final_chat_response(
        response,
        fallback_draft_id="DRAFT-1234",
    )

    assert parsed.ticket_draft.created is True
    assert parsed.ticket_draft.draft_id == "DRAFT-1234"


def test_parse_final_chat_response_downgrades_unbacked_ticket_draft_flag():
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=(
                                '{"answer":"I cannot provide the secret.",'
                                '"citations":[],'
                                '"confidence":0.2,'
                                '"next_actions":[],'
                                '"ticket_draft":{"created":true,"draft_id":null}}'
                            )
                        )
                    ],
                )
            )
        ]
    )

    parsed = main.parse_final_chat_response(response)

    assert parsed.ticket_draft.created is False
    assert parsed.ticket_draft.draft_id is None


def test_execute_mcp_tool_rejects_unknown_tool():
    with pytest.raises(ValueError):
        main.execute_mcp_tool(types.FunctionCall(name="log_feedback", args={}))


def test_chat_endpoint_returns_502_for_invalid_final_response(monkeypatch):
    trace_records = []
    invalid_response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text='{"answer":"","confidence":2}')],
                )
            )
        ]
    )

    monkeypatch.setattr(main, "get_gemini_client", lambda: object())
    monkeypatch.setattr(
        main,
        "generate_content",
        lambda client, contents, enable_tools: invalid_response,
    )
    monkeypatch.setattr(
        main,
        "log_agent_trace",
        lambda **kwargs: trace_records.append(kwargs),
    )

    response = client.post(
        "/chat",
        json={"query": "Can you approve my vacation request?", "session_id": "demo1"},
    )

    assert response.status_code == 502
    assert trace_records[0]["status"] == "error"
    assert trace_records[0]["session_id"] == "demo1"
    assert trace_records[0]["tool_names"] == []
    assert "ValidationError" in trace_records[0]["error"]


def test_chat_endpoint_returns_readable_detail_for_unexpected_error(monkeypatch):
    def raise_unexpected_error(payload, *, trace_id=None):
        raise LookupError("missing test dependency")

    monkeypatch.setattr(main, "run_agent_chat", raise_unexpected_error)

    response = client.post(
        "/chat",
        json={"query": "I cannot log in with SSO", "session_id": "demo1"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "LookupError: missing test dependency"
