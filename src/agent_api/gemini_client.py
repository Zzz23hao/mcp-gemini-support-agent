from google.genai import types


# Gemini function declarations for the tools the model may call. Only the
# schemas live here; execution happens in main.py.


def string_schema(description: str, *, nullable: bool = False) -> types.Schema:
    return types.Schema(
        type=types.Type.STRING,
        description=description,
        nullable=nullable,
    )


def integer_schema(
    description: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    nullable: bool = False,
) -> types.Schema:
    return types.Schema(
        type=types.Type.INTEGER,
        description=description,
        minimum=minimum,
        maximum=maximum,
        nullable=nullable,
    )


def string_array_schema(description: str) -> types.Schema:
    return types.Schema(
        type=types.Type.ARRAY,
        description=description,
        items=types.Schema(type=types.Type.STRING),
    )


def nullable_object_schema(description: str) -> types.Schema:
    return types.Schema(
        type=types.Type.OBJECT,
        description=description,
        nullable=True,
    )


SEARCH_KB_DECLARATION = types.FunctionDeclaration(
    name="search_kb",
    description=(
        "Search the internal knowledge base for source-aware evidence chunks. "
        "Use this first for support questions that need KB evidence."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": string_schema("User support question or search query."),
            "top_k": integer_schema(
                "Maximum number of KB chunks to return.",
                minimum=1,
                maximum=20,
            ),
            "filters": nullable_object_schema(
                "Optional metadata filters such as doc_id, team, or category."
            ),
        },
        required=["query"],
    ),
)


GET_KB_DOC_DECLARATION = types.FunctionDeclaration(
    name="get_kb_doc",
    description=(
        "Read a full original KB markdown document by doc_id. Use this when "
        "a retrieved chunk is not enough and the full source context is needed."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "doc_id": string_schema(
                "Document identifier, for example sso_login_troubleshooting."
            ),
        },
        required=["doc_id"],
    ),
)


SEARCH_TICKETS_DECLARATION = types.FunctionDeclaration(
    name="search_tickets",
    description=(
        "Search historical support tickets for similar resolved or open cases. "
        "Use this when past operational examples may help answer or triage."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "query": string_schema("User support issue or ticket search query."),
            "status": string_schema(
                "Optional ticket status filter such as open, resolved, or closed.",
                nullable=True,
            ),
            "time_range": string_schema(
                "Optional time range filter, for example last_30_days.",
                nullable=True,
            ),
        },
        required=["query"],
    ),
)


CREATE_TICKET_DRAFT_DECLARATION = types.FunctionDeclaration(
    name="create_ticket_draft",
    description=(
        "Create a local support ticket draft when the issue needs human follow-up. "
        "Only use this after gathering enough evidence for a structured handoff."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": string_schema("Short ticket title."),
            "description": string_schema(
                "Clear problem description, including user impact and evidence."
            ),
            "priority": string_schema(
                "Ticket priority, for example low, medium, high, or urgent."
            ),
            "tags": string_array_schema("Ticket tags such as sso, vpn, or license."),
            "assigned_group": string_schema(
                "Optional support group for handoff.",
                nullable=True,
            ),
            "evidence_ids": string_array_schema(
                "KB chunk IDs or historical ticket IDs used as evidence."
            ),
        },
        required=["title", "description"],
    ),
)


# Only business tools are exposed to the model. log_feedback and get_health
# are system-side and never model-callable.
MCP_TOOL_FUNCTION_DECLARATIONS = [
    SEARCH_KB_DECLARATION,
    GET_KB_DOC_DECLARATION,
    SEARCH_TICKETS_DECLARATION,
    CREATE_TICKET_DRAFT_DECLARATION,
]


MCP_GEMINI_TOOL = types.Tool(
    function_declarations=MCP_TOOL_FUNCTION_DECLARATIONS,
)


def get_mcp_gemini_tools() -> list[types.Tool]:
    # GenerateContentConfig(tools=...) expects a list of Tool objects.
    return [MCP_GEMINI_TOOL]
