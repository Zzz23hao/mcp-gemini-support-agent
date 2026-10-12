import pytest
from pydantic import ValidationError

from src.agent_api.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    TicketDraftInfo,
)


def test_chat_request_accepts_query_and_session_id():
    request = ChatRequest(query="I cannot log in with SSO", session_id="demo1")

    assert request.query == "I cannot log in with SSO"
    assert request.session_id == "demo1"


def test_chat_request_rejects_empty_query():
    with pytest.raises(ValidationError):
        ChatRequest(query="", session_id="demo1")


def test_chat_request_rejects_empty_session_id():
    with pytest.raises(ValidationError):
        ChatRequest(query="I cannot log in with SSO", session_id="")


def test_chat_response_matches_pdf_output_shape():
    response = ChatResponse(
        answer="Check the user's SSO assignment and MFA status.",
        citations=[
            Citation(
                doc_id="sso_login_troubleshooting",
                chunk_id="sso_login_troubleshooting#001",
                quote="Verify that the user is assigned to the application.",
            )
        ],
        confidence=0.82,
        next_actions=["Verify application assignment", "Check MFA enrollment"],
        ticket_draft=TicketDraftInfo(created=True, draft_id="DRAFT-0001"),
    )

    assert response.model_dump() == {
        "answer": "Check the user's SSO assignment and MFA status.",
        "citations": [
            {
                "doc_id": "sso_login_troubleshooting",
                "chunk_id": "sso_login_troubleshooting#001",
                "quote": "Verify that the user is assigned to the application.",
            }
        ],
        "confidence": 0.82,
        "next_actions": ["Verify application assignment", "Check MFA enrollment"],
        "ticket_draft": {"created": True, "draft_id": "DRAFT-0001"},
    }


def test_chat_response_defaults_optional_collections_and_ticket_draft():
    response = ChatResponse(answer="I do not have enough evidence.", confidence=0.2)

    assert response.citations == []
    assert response.next_actions == []
    assert response.ticket_draft == TicketDraftInfo(created=False, draft_id=None)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_chat_response_rejects_confidence_outside_zero_to_one(confidence):
    with pytest.raises(ValidationError):
        ChatResponse(answer="Answer", confidence=confidence)


def test_citation_requires_source_fields_and_quote():
    with pytest.raises(ValidationError):
        Citation(doc_id="", chunk_id="chunk-1", quote="Supporting quote")

    with pytest.raises(ValidationError):
        Citation(doc_id="doc-1", chunk_id="", quote="Supporting quote")

    with pytest.raises(ValidationError):
        Citation(doc_id="doc-1", chunk_id="chunk-1", quote="")


def test_ticket_draft_requires_draft_id_when_created():
    with pytest.raises(ValidationError):
        TicketDraftInfo(created=True, draft_id=None)


def test_ticket_draft_rejects_draft_id_when_not_created():
    with pytest.raises(ValidationError):
        TicketDraftInfo(created=False, draft_id="DRAFT-0001")
