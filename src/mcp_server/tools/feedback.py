import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.mcp_server.schemas import FeedbackRequest, FeedbackResponse


# 当前文件位置：
# src/mcp_server/tools/feedback.py
#
# parents[3] 往上走三层，可以回到项目根目录：
# feedback.py -> tools -> mcp_server -> src -> project root
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
    # feedback 是 append-only event log，一行一条 JSON，方便之后分析。
    append_jsonl(build_feedback_record(payload), path)
    return FeedbackResponse(logged=True)
