import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.mcp_server.schemas import FeedbackRequest, FeedbackResponse


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FEEDBACK_PATH = PROJECT_ROOT / "data" / "feedback.jsonl"


def build_feedback_record(payload: FeedbackRequest) -> dict[str, Any]:
    return {
        "session_id": payload.session_id,
        "rating": payload.rating,
        "comment": payload.comment,
        "created_at": datetime.now(UTC).isoformat(),
    }


def append_jsonl(record: dict[str, Any], path: Path = FEEDBACK_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as feedback_file:
        feedback_file.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_feedback(
    payload: FeedbackRequest,
    path: Path = FEEDBACK_PATH,
) -> FeedbackResponse:
    # Append-only JSONL, one event per line, for later analysis.
    append_jsonl(build_feedback_record(payload), path)
    return FeedbackResponse(logged=True)
