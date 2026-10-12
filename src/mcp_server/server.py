from fastapi import FastAPI

from src.mcp_server.schemas import (
    CreateTicketDraftRequest,
    CreateTicketDraftResponse,
    FeedbackRequest,
    FeedbackResponse,
    GetKbDocRequest,
    GetKbDocResponse,
    HealthResponse,
    SearchKbRequest,
    SearchKbResponse,
    SearchTicketsRequest,
    SearchTicketsResponse,
)
from src.mcp_server.tools.feedback import log_feedback
from src.mcp_server.tools.health import get_health
from src.mcp_server.tools.kb import get_kb_doc, search_kb
from src.mcp_server.tools.tickets import create_ticket_draft, search_tickets


app = FastAPI(
    title="MCP Gemini Support Agent",
    version="0.1.0",
)


@app.post("/tool/search_kb", response_model=SearchKbResponse)
def search_kb_endpoint(payload: SearchKbRequest) -> SearchKbResponse:
    return search_kb(payload)


@app.post("/tool/get_kb_doc", response_model=GetKbDocResponse)
def get_kb_doc_endpoint(payload: GetKbDocRequest) -> GetKbDocResponse:
    return get_kb_doc(payload)


@app.post("/tool/search_tickets", response_model=SearchTicketsResponse)
def search_tickets_endpoint(payload: SearchTicketsRequest) -> SearchTicketsResponse:
    return search_tickets(payload)


@app.post("/tool/create_ticket_draft", response_model=CreateTicketDraftResponse)
def create_ticket_draft_endpoint(
    payload: CreateTicketDraftRequest,
) -> CreateTicketDraftResponse:
    return create_ticket_draft(payload)


@app.post("/tool/log_feedback", response_model=FeedbackResponse)
def log_feedback_endpoint(payload: FeedbackRequest) -> FeedbackResponse:
    return log_feedback(payload)


@app.get("/health", response_model=HealthResponse)
def health_endpoint() -> HealthResponse:
    return get_health()
