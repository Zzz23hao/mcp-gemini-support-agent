import json
from pathlib import Path

from src.indexing.build_vector_index import CHROMA_DIR
from src.mcp_server.schemas import HealthResponse
from src.mcp_server.tools.feedback import FEEDBACK_PATH
from src.mcp_server.tools.kb import CHUNKS_PATH
from src.mcp_server.tools.tickets import TICKETS_PATH, TICKET_DRAFTS_PATH


# 当前文件位置：
# src/mcp_server/tools/health.py
#
# parents[3] 往上走三层，可以回到项目根目录：
# health.py -> tools -> mcp_server -> src -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_VERSION = "0.1.0"


def can_read_json(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False

    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    return True


def directory_is_writable(path: Path) -> bool:
    # 对不存在的目标文件，检查父目录是否可写；不要为了 health check 创建真实文件。
    directory = path if path.is_dir() else path.parent
    return directory.exists() and directory.is_dir() and bool(directory.stat().st_mode & 0o200)


def build_health_checks() -> dict[str, bool]:
    data_dir = PROJECT_ROOT / "data"
    return {
        "chunks_json_readable": can_read_json(CHUNKS_PATH),
        "chroma_index_exists": CHROMA_DIR.exists() and CHROMA_DIR.is_dir(),
        "tickets_json_readable": can_read_json(TICKETS_PATH),
        "data_dir_writable": directory_is_writable(data_dir),
        "ticket_drafts_parent_writable": directory_is_writable(TICKET_DRAFTS_PATH),
        "feedback_parent_writable": directory_is_writable(FEEDBACK_PATH),
    }


def get_health() -> HealthResponse:
    checks = build_health_checks()
    status = "ok" if all(checks.values()) else "degraded"

    return HealthResponse(
        status=status,
        version=PROJECT_VERSION,
        checks=checks,
    )
