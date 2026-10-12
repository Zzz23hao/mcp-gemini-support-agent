import json
from pathlib import Path

from src.agent_api.memory import (
    append_session_turn,
    format_session_history,
    get_session_history,
    truncate_text,
)
from src.agent_api.schemas import ChatResponse


def sample_response(answer: str = "Check SSO assignment and MFA."):
    return ChatResponse(
        answer=answer,
        citations=[
            {
                "doc_id": "sso_login_troubleshooting",
                "chunk_id": "sso_login_troubleshooting#003",
                "quote": "Verify MFA enrollment is complete.",
            }
        ],
        confidence=0.8,
        next_actions=["Verify MFA"],
        ticket_draft={"created": False, "draft_id": None},
    )


def test_truncate_text_collapses_whitespace_and_limits_length():
    text = "hello\n\nworld " + ("x" * 20)

    assert truncate_text(text, max_chars=12) == "hello world..."


def test_append_and_get_session_history(tmp_path: Path):
    path = tmp_path / "session_memory.json"

    append_session_turn("demo1", "I cannot log in", sample_response(), path=path)
    history = get_session_history("demo1", path=path)

    assert len(history) == 1
    assert history[0]["user"] == "I cannot log in"
    assert history[0]["assistant"] == "Check SSO assignment and MFA."
    assert history[0]["citations"][0]["chunk_id"] == "sso_login_troubleshooting#003"

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "demo1" in saved


def test_append_session_history_keeps_recent_turns(tmp_path: Path):
    path = tmp_path / "session_memory.json"
    for index in range(5):
        append_session_turn(
            "demo1",
            f"query {index}",
            sample_response(f"answer {index}"),
            path=path,
            max_turns=3,
        )

    history = get_session_history("demo1", path=path, max_turns=10)

    assert [turn["user"] for turn in history] == ["query 2", "query 3", "query 4"]


def test_format_session_history_includes_previous_turns():
    history = [
        {
            "user": "I cannot log in",
            "assistant": "Check SSO assignment.",
            "citations": [
                {
                    "doc_id": "sso_login_troubleshooting",
                    "chunk_id": "sso_login_troubleshooting#003",
                }
            ],
            "ticket_draft": {"created": False, "draft_id": None},
        }
    ]

    formatted = format_session_history(history)

    assert "Turn 1" in formatted
    assert "User: I cannot log in" in formatted
    assert "Assistant: Check SSO assignment." in formatted
    assert "sso_login_troubleshooting#003" in formatted
