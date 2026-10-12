import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.agent_api.schemas import ChatResponse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_TRACE_PATH = PROJECT_ROOT / "data" / "agent_traces.jsonl"


def estimate_tokens(text: str) -> int:
    # Rough estimate (~4 characters per token in English) for observability only;
    # not billing-grade.
    if not text:
        return 0
    return max(1, len(text) // 4)


def append_jsonl(record: dict[str, Any], path: Path = AGENT_TRACE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as trace_file:
        trace_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def emit_stdout_json(record: dict[str, Any]) -> None:
    # One structured JSON event per chat turn on stdout: the minimum for
    # log-based observability.
    print(json.dumps(record, ensure_ascii=False), flush=True)


def infer_error_type(error: str | None) -> str | None:
    if not error:
        return None
    return error.split(":", 1)[0].strip() or None


def build_agent_trace_record(
    *,
    trace_id: str,
    session_id: str,
    query: str,
    status: str,
    latency_ms: int,
    tool_names: list[str],
    response: ChatResponse | None = None,
    error: str | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    output_text = response.model_dump_json() if response else ""
    return {
        "event": "agent_chat_trace",
        "trace_id": trace_id,
        "session_id": session_id,
        "query": query,
        "status": status,
        "tool_calls": tool_names,
        "tool_call_count": len(tool_names),
        "tool_names": tool_names,
        "latency_ms": latency_ms,
        "estimated_input_tokens": estimate_tokens(query),
        "estimated_output_tokens": estimate_tokens(output_text),
        "error_type": error_type or infer_error_type(error),
        "error": error,
        "created_at": datetime.now(UTC).isoformat(),
    }


def log_agent_trace(
    *,
    trace_id: str,
    session_id: str,
    query: str,
    status: str,
    latency_ms: int,
    tool_names: list[str],
    response: ChatResponse | None = None,
    error: str | None = None,
    error_type: str | None = None,
    path: Path = AGENT_TRACE_PATH,
    emit_stdout: bool = True,
) -> None:
    # Append-only JSONL so traces can be replayed for debugging and eval.
    record = build_agent_trace_record(
        trace_id=trace_id,
        session_id=session_id,
        query=query,
        status=status,
        latency_ms=latency_ms,
        tool_names=tool_names,
        response=response,
        error=error,
        error_type=error_type,
    )
    append_jsonl(record, path)
    if emit_stdout:
        emit_stdout_json(record)
