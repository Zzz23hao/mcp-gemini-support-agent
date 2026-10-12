import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.agent_api.schemas import ChatResponse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SESSION_MEMORY_PATH = PROJECT_ROOT / "data" / "session_memory.json"
MAX_SESSION_TURNS = 8
MAX_TEXT_CHARS = 1200


def truncate_text(value: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return f"{cleaned[:max_chars].rstrip()}..."


def load_session_memory(path: Path = SESSION_MEMORY_PATH) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_session_memory(
    memory: dict[str, list[dict[str, Any]]],
    path: Path = SESSION_MEMORY_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")


def get_session_history(
    session_id: str,
    *,
    path: Path = SESSION_MEMORY_PATH,
    max_turns: int = MAX_SESSION_TURNS,
) -> list[dict[str, Any]]:
    memory = load_session_memory(path)
    return memory.get(session_id, [])[-max_turns:]


def build_memory_turn(query: str, response: ChatResponse) -> dict[str, Any]:
    return {
        "user": truncate_text(query),
        "assistant": truncate_text(response.answer),
        "citations": [citation.model_dump() for citation in response.citations[:5]],
        "ticket_draft": response.ticket_draft.model_dump(),
        "created_at": datetime.now(UTC).isoformat(),
    }


def append_session_turn(
    session_id: str,
    query: str,
    response: ChatResponse,
    *,
    path: Path = SESSION_MEMORY_PATH,
    max_turns: int = MAX_SESSION_TURNS,
) -> None:
    memory = load_session_memory(path)
    turns = memory.setdefault(session_id, [])
    turns.append(build_memory_turn(query, response))
    memory[session_id] = turns[-max_turns:]
    save_session_memory(memory, path)


def format_session_history(history: list[dict[str, Any]]) -> str:
    if not history:
        return "No previous turns for this session."

    formatted_turns = []
    for index, turn in enumerate(history, start=1):
        citations = turn.get("citations") or []
        citation_ids = [
            citation.get("chunk_id") or citation.get("doc_id")
            for citation in citations
            if citation.get("chunk_id") or citation.get("doc_id")
        ]
        formatted_turns.append(
            "\n".join(
                [
                    f"Turn {index}:",
                    f"User: {turn.get('user', '')}",
                    f"Assistant: {turn.get('assistant', '')}",
                    f"Citations: {', '.join(citation_ids) if citation_ids else 'none'}",
                    f"Ticket draft: {turn.get('ticket_draft', {})}",
                ]
            )
        )
    return "\n\n".join(formatted_turns)
