from pydantic import BaseModel, Field


# schemas.py 的作用：
# 只定义“数据长什么样”，不负责真正的搜索、读文件、写文件。
# 这些 class 会被工具函数和 FastAPI endpoint 共同使用，
# 用来保证输入输出格式稳定。


class SearchKbRequest(BaseModel):
    # 调用 search_kb 时，用户或 Agent 想搜索的问题。
    query: str = Field(min_length=1)

    # 最多返回多少条结果。
    # 默认 5 条，最少 1 条，最多 20 条，避免一次返回太多内容。
    top_k: int = Field(default=5, ge=1, le=20)

    # 预留字段：以后可以按 doc_id、team、category 等条件过滤。
    # 第一版可以先不使用它。
    filters: dict[str, str] | None = None


class SearchKbResult(BaseModel):
    # 这条结果来自哪篇 KB 文档。
    doc_id: str

    # 这条结果是文档里的哪个 chunk。
    chunk_id: str

    # chunk 所属的 Markdown section，比如 Background / Troubleshooting Steps。
    heading: str

    # chunk 的正文内容。
    text: str

    # 搜索相关度分数。
    # 第一版关键词搜索可以自己算一个简单 score。
    score: float


class SearchKbResponse(BaseModel):
    # search_kb 最终返回的是多条搜索结果，所以这里是 list。
    results: list[SearchKbResult]


class GetKbDocRequest(BaseModel):
    # 要读取哪一篇原始 KB 文档。
    # 例如 "vpn_setup" 对应 data/kb_docs/vpn_setup.md。
    doc_id: str = Field(min_length=1)


class GetKbDocResponse(BaseModel):
    doc_id: str
    content: str

    # 预留一些额外信息，比如文件路径、是否找到。
    metadata: dict[str, str] = Field(default_factory=dict)


class SearchTicketsRequest(BaseModel):
    # 要搜索的历史工单问题。
    query: str = Field(min_length=1)

    # 可选：只搜索 resolved / closed / open 等状态。
    status: str | None = None

    # 可选：以后可以支持 "last_30_days" 这种时间范围。
    time_range: str | None = None


class TicketSummary(BaseModel):
    # 历史工单的核心摘要字段。
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
    # search_tickets 也会返回多条历史工单。
    results: list[TicketSummary]


class CreateTicketDraftRequest(BaseModel):
    # Agent 判断需要升级时，会创建一份“新工单草稿”。
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: str = "medium"
    tags: list[str] = Field(default_factory=list)

    # 建议分配给哪个团队，比如 Identity Operations / Cloud Platform。
    assigned_group: str | None = None

    # 这份草稿参考了哪些 KB chunk 或历史 ticket。
    evidence_ids: list[str] = Field(default_factory=list)


class CreateTicketDraftResponse(BaseModel):
    # 创建成功后返回草稿 ID，方便后续引用。
    draft_id: str
    created: bool = True


class FeedbackRequest(BaseModel):
    # 用户对某次 Agent 回答的反馈。
    session_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class FeedbackResponse(BaseModel):
    logged: bool = True


class HealthResponse(BaseModel):
    # health 用来检查工具服务是否处于可用状态。
    status: str
    version: str

    # 每个依赖项的检查结果，比如 chunks.json 是否存在、tickets.json 是否可读。
    checks: dict[str, bool]
