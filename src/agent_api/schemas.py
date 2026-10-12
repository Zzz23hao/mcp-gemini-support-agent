from pydantic import BaseModel, Field, model_validator


# 这些 schemas 定义 Agent API layer 的 public contract。
# 它们和 src/mcp_server/schemas.py 分开：tool schemas 描述单个 tool call，
# 这里的 models 描述用户看到的最终 /chat request 和 response。


class ChatRequest(BaseModel):
    # 用户的 support question，例如: "I cannot log in with SSO".
    query: str = Field(min_length=1)

    # 会话 ID。后面用于 tracing、logs，以及 multi-turn memory。
    session_id: str = Field(min_length=1)


class Citation(BaseModel):
    # 支撑答案的 source KB document。
    doc_id: str = Field(min_length=1)

    # 文档里的具体 chunk。这样 citation 可以 trace back 到原始证据。
    chunk_id: str = Field(min_length=1)

    # 从 retrieved source 中摘出来的短 evidence quote。
    quote: str = Field(min_length=1)


class TicketDraftInfo(BaseModel):
    # Agent 是否真的创建了 ticket draft，用于 human follow-up。
    created: bool = False

    # create_ticket_draft 返回的 draft identifier。created=true 时必须存在。
    draft_id: str | None = None

    @model_validator(mode="after")
    def validate_draft_id(self) -> "TicketDraftInfo":
        # 保持 output internally consistent：
        # created=true 必须有 draft_id；
        # created=false 时不能假装已经有 draft。
        if self.created and not self.draft_id:
            raise ValueError("draft_id is required when ticket draft is created")
        if not self.created and self.draft_id is not None:
            raise ValueError("draft_id must be null when ticket draft is not created")
        return self


class ChatResponse(BaseModel):
    # 最终返回给用户的 natural-language answer。
    answer: str = Field(min_length=1)

    # answer 使用的 evidence。空 list 表示 agent 没找到可引用证据。
    citations: list[Citation] = Field(default_factory=list)

    # 简单 confidence score，给 downstream display/evaluation 使用，范围 0-1。
    confidence: float = Field(ge=0.0, le=1.0)

    # 给 user 或 support team 的 recommended next steps。
    next_actions: list[str] = Field(default_factory=list)

    # ticket draft 状态。默认是 not created。
    ticket_draft: TicketDraftInfo = Field(default_factory=TicketDraftInfo)
