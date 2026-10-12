from src.agent_api.prompts import (
    AGENT_SYSTEM_PROMPT,
    build_final_response_prompt,
    build_user_prompt,
)


def test_system_prompt_requires_evidence_and_citations():
    prompt = AGENT_SYSTEM_PROMPT.lower()

    assert "tool evidence" in prompt
    assert "citation" in prompt
    assert "doc_id" in prompt
    assert "chunk_id" in prompt
    assert "quote" in prompt


def test_system_prompt_prefers_kb_search_and_ticket_search_when_needed():
    prompt = AGENT_SYSTEM_PROMPT

    assert "search_kb" in prompt
    assert "get_kb_doc" in prompt
    assert "search_tickets" in prompt


def test_system_prompt_controls_ticket_draft_creation():
    prompt = AGENT_SYSTEM_PROMPT

    assert "create a ticket draft" in prompt
    assert "evidence IDs" in prompt
    assert "ticket_draft" in prompt
    assert '"created": false' in prompt
    assert '"draft_id": null' in prompt


def test_system_prompt_rejects_hallucinated_or_unsupported_answers():
    prompt = AGENT_SYSTEM_PROMPT.lower()

    assert "do not invent" in prompt
    assert "not sure" in prompt
    assert "safe escalation path" in prompt
    assert "sensitive" in prompt
    assert "secret" in prompt
    assert "financial" in prompt
    assert "hr" in prompt
    assert "internal" in prompt
    assert "out-of-scope" in prompt
    assert "escalating" in prompt


def test_system_prompt_includes_pdf_response_shape():
    prompt = AGENT_SYSTEM_PROMPT

    assert '"answer": "..."' in prompt
    assert '"citations"' in prompt
    assert '"confidence": 0.0' in prompt
    assert '"next_actions": ["..."]' in prompt
    assert '"ticket_draft"' in prompt


def test_build_user_prompt_includes_session_id_and_query():
    prompt = build_user_prompt(
        query="I cannot log in with SSO",
        session_id="demo1",
        conversation_history="Turn 1: previous SSO issue",
    )

    assert "session_id: demo1" in prompt
    assert "conversation_history" in prompt
    assert "Turn 1: previous SSO issue" in prompt
    assert "user_query: I cannot log in with SSO" in prompt
    assert "history only to resolve follow-up references" in prompt
    assert "return the final JSON response" in prompt


def test_final_response_prompt_requires_coverage_of_evidence_checklist():
    prompt = build_final_response_prompt(
        query="VPN keeps failing",
        session_id="demo1",
        tool_results=[],
        conversation_history="Turn 1: previous VPN issue",
    ).lower()

    assert "conversation_history" in prompt
    assert "previous vpn issue" in prompt
    assert "troubleshooting questions" in prompt
    assert "identity verification" in prompt
    assert "credentials" in prompt
    assert "mfa" in prompt
    assert "status page" in prompt
    assert "access request process" in prompt
    assert "approval requirements" in prompt
    assert "dns records" in prompt
    assert "spf" in prompt
    assert "dkim" in prompt
    assert "dmarc" in prompt
    assert "failed job logs" in prompt
    assert "build logs" in prompt
    assert "cloud budget" in prompt
    assert "unused resources" in prompt
    assert "scheduled shutdown" in prompt
    assert "crashloopbackoff" in prompt
    assert "authentication" in prompt
    assert "incognito" in prompt
    assert "private browsing" in prompt
    assert "expiration" in prompt
    assert "hostname" in prompt
