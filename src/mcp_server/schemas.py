from pydantic import BaseModel, Field


# Request/response contracts shared by the tool functions and the FastAPI
# endpoints. Keeping them in one place is what makes the tool layer stable
# enough for the model to call.


class SearchKbRequest(BaseModel):
    query: str = Field(min_length=1)

    # Bounded so a single tool call cannot flood the model's context.
    top_k: int = Field(default=5, ge=1, le=20)

    # Reserved for metadata filters (doc_id, team, category); unused for now.
    filters: dict[str, str] | None = None


class SearchKbResult(BaseModel):
    doc_id: str
    chunk_id: str

    # Markdown section the chunk came from, e.g. "Troubleshooting Steps".
    heading: str
    text: str

    # Relevance score. Higher is more relevant on both retrieval paths
    # (keyword scoring, or 1/(1+distance) for vector search).
    score: float


class SearchKbResponse(BaseModel):
    results: list[SearchKbResult]


class GetKbDocRequest(BaseModel):
    # Maps to data/kb_docs/<doc_id>.md; validated in tools/kb.py.
    doc_id: str = Field(min_length=1)


class GetKbDocResponse(BaseModel):
    doc_id: str
    content: str
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchTicketsRequest(BaseModel):
    query: str = Field(min_length=1)

    # Optional status filter: open / resolved / closed.
    status: str | None = None

    # Reserved for ranges such as "last_30_days"; not implemented yet.
    time_range: str | None = None


class TicketSummary(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    requester_team: str
    assigned_group: str
    tags: list[str]
    symptoms: list[str]
    steps_taken: list[str]
    root_cause: str
    resolution: str
    escalated: bool
    related_kb_doc: str


class SearchTicketsResponse(BaseModel):
    results: list[TicketSummary]


class CreateTicketDraftRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: str = "medium"
    tags: list[str] = Field(default_factory=list)

    # Suggested owning team, e.g. "Identity Operations".
    assigned_group: str | None = None

    # KB chunk IDs or ticket IDs the draft is based on, so a human reviewer
    # can follow the evidence trail.
    evidence_ids: list[str] = Field(default_factory=list)


class CreateTicketDraftResponse(BaseModel):
    draft_id: str
    created: bool = True


class FeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class FeedbackResponse(BaseModel):
    logged: bool = True


class HealthResponse(BaseModel):
    status: str
    version: str

    # One boolean per dependency: index readable, tickets readable, data dir writable.
    checks: dict[str, bool]
