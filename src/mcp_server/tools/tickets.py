import json
import re
from pathlib import Path
from typing import Any

from src.mcp_server.schemas import (
    CreateTicketDraftRequest,
    CreateTicketDraftResponse,
    SearchTicketsRequest,
    SearchTicketsResponse,
    TicketSummary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TICKETS_PATH = PROJECT_ROOT / "data" / "tickets.json"
TICKET_DRAFTS_PATH = PROJECT_ROOT / "data" / "ticket_drafts.json"
DEFAULT_TICKET_TOP_K = 5

STOP_WORDS = {
    "a",
    "an",
    "and",
    "can",
    "for",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def load_tickets() -> list[dict[str, Any]]:
    # Missing data degrades to empty results, consistent with kb.load_chunks.
    if not TICKETS_PATH.exists():
        return []

    return json.loads(TICKETS_PATH.read_text(encoding="utf-8"))


def load_ticket_drafts(path: Path = TICKET_DRAFTS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    return json.loads(path.read_text(encoding="utf-8"))


def save_ticket_drafts(
    drafts: list[dict[str, Any]],
    path: Path = TICKET_DRAFTS_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(drafts, indent=2, ensure_ascii=False), encoding="utf-8")


def next_draft_id(drafts: list[dict[str, Any]]) -> str:
    max_number = 0
    for draft in drafts:
        draft_id = str(draft.get("draft_id", ""))
        if not draft_id.startswith("DRAFT-"):
            continue

        try:
            max_number = max(max_number, int(draft_id.removeprefix("DRAFT-")))
        except ValueError:
            continue

    return f"DRAFT-{max_number + 1:04d}"


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if len(token) > 1 and token not in STOP_WORDS]


def _joined(values: list[str] | str | None) -> str:
    if values is None:
        return ""
    if isinstance(values, list):
        return " ".join(values).lower()
    return values.lower()


def score_ticket(query_tokens: list[str], ticket: dict[str, Any]) -> float:
    # Title and tags carry the most topical signal, so they weigh the most.
    weighted_fields = [
        (ticket.get("title"), 2.0),
        (ticket.get("tags"), 2.0),
        (ticket.get("symptoms"), 1.5),
        (ticket.get("resolution"), 1.0),
        (ticket.get("root_cause"), 1.0),
        (ticket.get("steps_taken"), 1.0),
        (ticket.get("assigned_group"), 0.5),
        (ticket.get("related_kb_doc"), 0.5),
    ]

    score = 0.0
    for token in query_tokens:
        for value, weight in weighted_fields:
            if token in _joined(value):
                score += weight

    return score


def ticket_matches_status(ticket: dict[str, Any], status: str | None) -> bool:
    if status is None:
        return True
    return ticket.get("status", "").lower() == status.lower()


def to_ticket_summary(ticket: dict[str, Any]) -> TicketSummary:
    return TicketSummary(
        id=ticket["id"],
        title=ticket["title"],
        status=ticket["status"],
        priority=ticket["priority"],
        requester_team=ticket["requester_team"],
        assigned_group=ticket["assigned_group"],
        tags=ticket["tags"],
        symptoms=ticket["symptoms"],
        steps_taken=ticket["steps_taken"],
        root_cause=ticket["root_cause"],
        resolution=ticket["resolution"],
        escalated=ticket["escalated"],
        related_kb_doc=ticket["related_kb_doc"],
    )


def create_ticket_draft(
    payload: CreateTicketDraftRequest,
    path: Path = TICKET_DRAFTS_PATH,
) -> CreateTicketDraftResponse:
    # Drafts are local records only; nothing is submitted to a real ticketing system.
    drafts = load_ticket_drafts(path)
    draft_id = next_draft_id(drafts)

    drafts.append(
        {
            "draft_id": draft_id,
            "title": payload.title,
            "description": payload.description,
            "priority": payload.priority,
            "tags": payload.tags,
            "assigned_group": payload.assigned_group,
            "evidence_ids": payload.evidence_ids,
        }
    )
    save_ticket_drafts(drafts, path)

    return CreateTicketDraftResponse(draft_id=draft_id)


def search_tickets(payload: SearchTicketsRequest) -> SearchTicketsResponse:
    # time_range is accepted but not applied yet; its format is still undefined.
    query_tokens = tokenize(payload.query)
    if not query_tokens:
        return SearchTicketsResponse(results=[])

    scored_tickets: list[tuple[float, dict[str, Any]]] = []
    for ticket in load_tickets():
        if not ticket_matches_status(ticket, payload.status):
            continue

        score = score_ticket(query_tokens, ticket)
        if score <= 0:
            continue

        scored_tickets.append((score, ticket))

    scored_tickets.sort(key=lambda item: item[0], reverse=True)
    results = [
        to_ticket_summary(ticket)
        for _, ticket in scored_tickets[:DEFAULT_TICKET_TOP_K]
    ]

    return SearchTicketsResponse(results=results)
