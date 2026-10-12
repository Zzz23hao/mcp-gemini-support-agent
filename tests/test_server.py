from fastapi.testclient import TestClient

from src.mcp_server import server
from src.mcp_server.schemas import (
    CreateTicketDraftResponse,
    FeedbackResponse,
    GetKbDocResponse,
    HealthResponse,
    SearchKbResponse,
    SearchKbResult,
    SearchTicketsResponse,
    TicketSummary,
)


client = TestClient(server.app)


def test_search_kb_endpoint_calls_tool(monkeypatch):
    def fake_search_kb(payload):
        assert payload.query == "SSO login failed"
        assert payload.top_k == 3
        return SearchKbResponse(
            results=[
                SearchKbResult(
                    doc_id="sso_login_troubleshooting",
                    chunk_id="sso_login_troubleshooting#001",
                    heading="Troubleshooting Steps",
                    text="Check SSO assignment.",
                    score=4.0,
                )
            ]
        )

    monkeypatch.setattr(server, "search_kb", fake_search_kb)

    response = client.post(
        "/tool/search_kb",
        json={"query": "SSO login failed", "top_k": 3},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["doc_id"] == "sso_login_troubleshooting"


def test_get_kb_doc_endpoint_calls_tool(monkeypatch):
    def fake_get_kb_doc(payload):
        assert payload.doc_id == "vpn_setup"
        return GetKbDocResponse(
            doc_id="vpn_setup",
            content="# VPN Setup",
            metadata={"path": "data/kb_docs/vpn_setup.md"},
        )

    monkeypatch.setattr(server, "get_kb_doc", fake_get_kb_doc)

    response = client.post("/tool/get_kb_doc", json={"doc_id": "vpn_setup"})

    assert response.status_code == 200
    assert response.json()["content"] == "# VPN Setup"


def test_search_tickets_endpoint_calls_tool(monkeypatch):
    def fake_search_tickets(payload):
        assert payload.query == "OAuth failed"
        assert payload.status == "resolved"
        return SearchTicketsResponse(
            results=[
                TicketSummary(
                    id="TCK-0001",
                    title="OAuth login failed",
                    status="resolved",
                    priority="high",
                    requester_team="Engineering",
                    assigned_group="Identity Operations",
                    tags=["oauth", "sso"],
                    symptoms=["User cannot login"],
                    steps_taken=["Checked redirect URI"],
                    root_cause="Redirect URI mismatch",
                    resolution="Updated OAuth client configuration",
                    escalated=False,
                    related_kb_doc="oauth_application_login_failure",
                )
            ]
        )

    monkeypatch.setattr(server, "search_tickets", fake_search_tickets)

    response = client.post(
        "/tool/search_tickets",
        json={"query": "OAuth failed", "status": "resolved"},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "TCK-0001"


def test_create_ticket_draft_endpoint_calls_tool(monkeypatch):
    def fake_create_ticket_draft(payload):
        assert payload.title == "SSO issue"
        assert payload.priority == "high"
        return CreateTicketDraftResponse(draft_id="DRAFT-0001")

    monkeypatch.setattr(server, "create_ticket_draft", fake_create_ticket_draft)

    response = client.post(
        "/tool/create_ticket_draft",
        json={
            "title": "SSO issue",
            "description": "User still cannot login.",
            "priority": "high",
            "tags": ["sso"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"draft_id": "DRAFT-0001", "created": True}


def test_log_feedback_endpoint_calls_tool(monkeypatch):
    def fake_log_feedback(payload):
        assert payload.session_id == "session-1"
        assert payload.rating == 5
        return FeedbackResponse(logged=True)

    monkeypatch.setattr(server, "log_feedback", fake_log_feedback)

    response = client.post(
        "/tool/log_feedback",
        json={"session_id": "session-1", "rating": 5, "comment": "Helpful"},
    )

    assert response.status_code == 200
    assert response.json() == {"logged": True}


def test_health_endpoint_calls_tool(monkeypatch):
    def fake_get_health():
        return HealthResponse(
            status="ok",
            version="0.1.0",
            checks={"tickets_json_readable": True},
        )

    monkeypatch.setattr(server, "get_health", fake_get_health)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_kb_endpoint_validates_request_body():
    response = client.post("/tool/search_kb", json={"query": "", "top_k": 3})

    assert response.status_code == 422
