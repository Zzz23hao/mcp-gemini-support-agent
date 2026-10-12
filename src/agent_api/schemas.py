from pydantic import BaseModel, Field, model_validator


# Public contract of the Agent API (/chat). Tool-level schemas live in
# src/mcp_server/schemas.py; these describe what the end user sends and receives.


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)

    # Used for tracing, logs and per-session memory; never treated as evidence.
    session_id: str = Field(min_length=1)


class Citation(BaseModel):
    doc_id: str = Field(min_length=1)

    # Chunk-level reference so every citation can be traced back to its source text.
    chunk_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class TicketDraftInfo(BaseModel):
    created: bool = False
    draft_id: str | None = None

    @model_validator(mode="after")
    def validate_draft_id(self) -> "TicketDraftInfo":
        # created=True without an ID, or an ID without created=True, would let
        # the model claim a draft that does not exist.
        if self.created and not self.draft_id:
            raise ValueError("draft_id is required when ticket draft is created")
        if not self.created and self.draft_id is not None:
            raise ValueError("draft_id must be null when ticket draft is not created")
        return self


class ChatResponse(BaseModel):
    answer: str = Field(min_length=1)

    # Empty list means no citable evidence was found.
    citations: list[Citation] = Field(default_factory=list)

    # 0-1; capped downstream to 0.9 with citations and 0.4 without.
    confidence: float = Field(ge=0.0, le=1.0)
    next_actions: list[str] = Field(default_factory=list)
    ticket_draft: TicketDraftInfo = Field(default_factory=TicketDraftInfo)
