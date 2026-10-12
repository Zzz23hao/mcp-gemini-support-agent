from google.genai import types

from src.agent_api.gemini_client import (
    CREATE_TICKET_DRAFT_DECLARATION,
    GET_KB_DOC_DECLARATION,
    MCP_TOOL_FUNCTION_DECLARATIONS,
    SEARCH_KB_DECLARATION,
    SEARCH_TICKETS_DECLARATION,
    get_mcp_gemini_tools,
)


def declaration_names() -> list[str]:
    return [declaration.name for declaration in MCP_TOOL_FUNCTION_DECLARATIONS]


def test_gemini_tool_declarations_match_pdf_section_5_2():
    assert declaration_names() == [
        "search_kb",
        "get_kb_doc",
        "search_tickets",
        "create_ticket_draft",
    ]


def test_feedback_and_health_are_not_model_callable_tools():
    assert "log_feedback" not in declaration_names()
    assert "get_health" not in declaration_names()


def test_search_kb_declaration_schema():
    parameters = SEARCH_KB_DECLARATION.parameters

    assert parameters.type == types.Type.OBJECT
    assert parameters.required == ["query"]
    assert parameters.properties["query"].type == types.Type.STRING
    assert parameters.properties["top_k"].type == types.Type.INTEGER
    assert parameters.properties["top_k"].minimum == 1
    assert parameters.properties["top_k"].maximum == 20
    assert parameters.properties["filters"].nullable is True


def test_get_kb_doc_declaration_schema():
    parameters = GET_KB_DOC_DECLARATION.parameters

    assert parameters.required == ["doc_id"]
    assert parameters.properties["doc_id"].type == types.Type.STRING


def test_search_tickets_declaration_schema():
    parameters = SEARCH_TICKETS_DECLARATION.parameters

    assert parameters.required == ["query"]
    assert parameters.properties["query"].type == types.Type.STRING
    assert parameters.properties["status"].nullable is True
    assert parameters.properties["time_range"].nullable is True


def test_create_ticket_draft_declaration_schema():
    parameters = CREATE_TICKET_DRAFT_DECLARATION.parameters

    assert parameters.required == ["title", "description"]
    assert parameters.properties["title"].type == types.Type.STRING
    assert parameters.properties["description"].type == types.Type.STRING
    assert parameters.properties["priority"].type == types.Type.STRING
    assert parameters.properties["tags"].type == types.Type.ARRAY
    assert parameters.properties["tags"].items.type == types.Type.STRING
    assert parameters.properties["assigned_group"].nullable is True
    assert parameters.properties["evidence_ids"].type == types.Type.ARRAY


def test_get_mcp_gemini_tools_returns_tool_wrapper():
    tools = get_mcp_gemini_tools()

    assert len(tools) == 1
    assert tools[0].function_declarations == MCP_TOOL_FUNCTION_DECLARATIONS
