import json
import logging
import os
import time
import uuid
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from google import genai
from google.genai import types
from pydantic import ValidationError

from src.agent_api.gemini_client import get_mcp_gemini_tools
from src.agent_api.memory import (
    append_session_turn,
    format_session_history,
    get_session_history,
)
from src.agent_api.observability import (
    agent_chat_span,
    set_span_attribute,
    setup_tracing,
    tool_call_span,
)
from src.agent_api.prompts import (
    AGENT_SYSTEM_PROMPT,
    build_final_response_prompt,
    build_user_prompt,
)
from src.agent_api.schemas import ChatRequest, ChatResponse, TicketDraftInfo
from src.agent_api.tracing import log_agent_trace


load_dotenv()


logger = logging.getLogger(__name__)


setup_tracing()


app = FastAPI(
    title="MCP Gemini Support Agent API",
    version="0.1.0",
)


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_MCP_SERVER_URL = "http://localhost:7001"
TOOL_TIMEOUT_SECONDS = 5.0
TOOL_RETRY_COUNT = 2
MIN_SEARCH_KB_TOP_K = 8
MAX_SUPPORTED_CONFIDENCE = 0.9
MAX_UNCITED_CONFIDENCE = 0.4

TOOL_ENDPOINTS = {
    "search_kb": "/tool/search_kb",
    "get_kb_doc": "/tool/get_kb_doc",
    "search_tickets": "/tool/search_tickets",
    "create_ticket_draft": "/tool/create_ticket_draft",
}


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to call Gemini")
    return genai.Client(api_key=api_key)


def get_gemini_model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def get_mcp_server_url() -> str:
    return os.getenv("MCP_SERVER_URL", DEFAULT_MCP_SERVER_URL).rstrip("/")


def create_trace_id() -> str:
    return uuid.uuid4().hex


def build_generate_config(*, enable_tools: bool) -> types.GenerateContentConfig:
    # Gemini API does not allow function calling tools and JSON response MIME
    # type in the same request. First call enables tools; final answer call
    # disables tools and asks for ChatResponse JSON.
    if enable_tools:
        return types.GenerateContentConfig(
            system_instruction=AGENT_SYSTEM_PROMPT,
            tools=get_mcp_gemini_tools(),
        )

    return types.GenerateContentConfig(
        system_instruction=AGENT_SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=ChatResponse,
    )


def generate_content(
    client: genai.Client,
    contents: str | list[types.Content],
    *,
    enable_tools: bool,
) -> types.GenerateContentResponse:
    return client.models.generate_content(
        model=get_gemini_model_name(),
        contents=contents,
        config=build_generate_config(enable_tools=enable_tools),
    )


def execute_mcp_tool(
    function_call: types.FunctionCall,
    *,
    mcp_server_url: str | None = None,
) -> dict[str, Any]:
    if not function_call.name or function_call.name not in TOOL_ENDPOINTS:
        raise ValueError(f"Unsupported function call: {function_call.name}")

    endpoint = TOOL_ENDPOINTS[function_call.name]
    url = f"{mcp_server_url or get_mcp_server_url()}{endpoint}"
    payload = function_call.args or {}
    if function_call.name == "search_kb":
        payload["top_k"] = max(int(payload.get("top_k", 0) or 0), MIN_SEARCH_KB_TOP_K)

    last_error: Exception | None = None
    for attempt in range(TOOL_RETRY_COUNT + 1):
        try:
            with tool_call_span(function_call, url=url, attempt=attempt + 1) as span:
                with httpx.Client(timeout=TOOL_TIMEOUT_SECONDS) as client:
                    response = client.post(url, json=payload)

                span.set_attribute("http.status_code", response.status_code)

                if response.status_code in {429} or 500 <= response.status_code < 600:
                    response.raise_for_status()

                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            last_error = error
            if attempt == TOOL_RETRY_COUNT:
                break
            time.sleep(0.2 * (2**attempt))

    raise RuntimeError(f"Tool call failed: {function_call.name}") from last_error


def query_needs_ticket_history(query: str) -> bool:
    query_lower = query.lower()
    return any(
        marker in query_lower
        for marker in [
            "similar",
            "previous",
            "past ticket",
            "past tickets",
            "historical",
            "have we seen",
            "old tickets",
            "ticket history",
            "past incidents",
            "previous cases",
        ]
    )


def query_mentions_kb(query: str) -> bool:
    query_lower = query.lower()
    return "kb" in query_lower or "knowledge base" in query_lower


def query_is_out_of_scope_or_sensitive(query: str) -> bool:
    query_lower = query.lower()
    return any(
        marker in query_lower
        for marker in [
            "cafeteria",
            "lunch menu",
            "personal phone",
            "home address",
            "root password",
            "bypass mfa",
            "vacation request",
            "stock should i buy",
            "unreleased product roadmap",
        ]
    )


def query_is_likely_support_question(query: str) -> bool:
    if query_is_out_of_scope_or_sensitive(query):
        return False

    query_lower = query.lower()
    return any(
        marker in query_lower
        for marker in [
            "access",
            "account",
            "api",
            "approve",
            "approved",
            "approval",
            "aws",
            "browser",
            "certificate",
            "ci",
            "database",
            "deployment",
            "device",
            "dns",
            "email",
            "github",
            "install",
            "kubernetes",
            "laptop",
            "log",
            "login",
            "password",
            "pipeline",
            "salesforce",
            "security incident",
            "software",
            "sso",
            "tls",
            "vpn",
        ]
    )


def build_supplemental_ticket_history_call(query: str) -> types.FunctionCall:
    return types.FunctionCall(
        name="search_tickets",
        args={"query": query, "status": None, "time_range": None},
    )


def build_supplemental_kb_call(query: str) -> types.FunctionCall:
    return types.FunctionCall(
        name="search_kb",
        args={"query": query, "top_k": MIN_SEARCH_KB_TOP_K},
    )


def query_explicitly_requests_ticket_draft(query: str) -> bool:
    query_lower = query.lower()
    return any(
        marker in query_lower
        for marker in [
            "create a ticket",
            "create ticket",
            "ticket draft",
            "draft a ticket",
            "draft an escalation",
            "prepare a ticket",
            "open a ticket",
            "raise a ticket",
            "file a ticket",
        ]
    )


def infer_ticket_priority(query: str) -> str:
    query_lower = query.lower()
    if any(
        marker in query_lower
        for marker in [
            "production",
            "security incident",
            "multiple users",
            "several",
            "outage",
            "down",
            "blocking",
            "blocked",
        ]
    ):
        return "high"
    return "medium"


def infer_assigned_group(query: str) -> str | None:
    query_lower = query.lower()
    if any(marker in query_lower for marker in ["sso", "identity", "authenticate"]):
        return "Identity Operations"
    if any(marker in query_lower for marker in ["vpn", "network"]):
        return "Network Team"
    if "database" in query_lower:
        return "Database Operations"
    if any(marker in query_lower for marker in ["kubernetes", "pod", "platform"]):
        return "Platform Engineering"
    if "security incident" in query_lower:
        return "Security Operations"
    if any(marker in query_lower for marker in ["tls", "certificate"]):
        return "Platform Engineering"
    if any(marker in query_lower for marker in ["ci", "pull request"]):
        return "Developer Productivity"
    if "data pipeline" in query_lower:
        return "Data Platform"
    if any(marker in query_lower for marker in ["rate limit", "api"]):
        return "Platform Engineering"
    return None


def collect_evidence_ids(tool_results: list[dict[str, Any]]) -> list[str]:
    evidence_ids: list[str] = []
    for tool_result in tool_results:
        result = tool_result.get("tool_result") or {}
        for kb_result in result.get("results", []):
            if isinstance(kb_result, dict):
                chunk_id = kb_result.get("chunk_id")
                doc_id = kb_result.get("doc_id")
                ticket_id = kb_result.get("id")
            else:
                chunk_id = getattr(kb_result, "chunk_id", None)
                doc_id = getattr(kb_result, "doc_id", None)
                ticket_id = getattr(kb_result, "id", None)
            if chunk_id:
                evidence_ids.append(chunk_id)
            elif doc_id:
                evidence_ids.append(doc_id)
            elif ticket_id:
                evidence_ids.append(ticket_id)
    return list(dict.fromkeys(evidence_ids))[:8]


def build_supplemental_ticket_draft_call(
    query: str,
    tool_results: list[dict[str, Any]],
) -> types.FunctionCall:
    title = query.strip()
    if len(title) > 90:
        title = f"{title[:87].rstrip()}..."

    return types.FunctionCall(
        name="create_ticket_draft",
        args={
            "title": title,
            "description": query,
            "priority": infer_ticket_priority(query),
            "tags": [],
            "assigned_group": infer_assigned_group(query),
            "evidence_ids": collect_evidence_ids(tool_results),
        },
    )


def has_kb_evidence(tool_names: list[str]) -> bool:
    return "search_kb" in tool_names or "get_kb_doc" in tool_names


def should_add_supplemental_kb(query: str, tool_names: list[str]) -> bool:
    if has_kb_evidence(tool_names):
        return False

    if query_needs_ticket_history(query):
        return True

    return (
        "create_ticket_draft" in tool_names
        or query_mentions_kb(query)
        or query_is_likely_support_question(query)
    )


def extract_response_json_text(response: types.GenerateContentResponse) -> str:
    if not response.text:
        raise ValueError("Gemini final response did not include JSON text")

    cleaned_text = response.text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.removeprefix("```json").removesuffix("```").strip()
    elif cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.removeprefix("```").removesuffix("```").strip()
    return cleaned_text


def find_created_ticket_draft_id(tool_results: list[dict[str, Any]]) -> str | None:
    for tool_result in tool_results:
        if tool_result.get("tool_name") != "create_ticket_draft":
            continue
        result = tool_result.get("tool_result") or {}
        draft_id = result.get("draft_id")
        if draft_id:
            return draft_id
    return None


def has_created_ticket_draft_tool_result(tool_results: list[dict[str, Any]]) -> bool:
    return find_created_ticket_draft_id(tool_results) is not None


def enforce_ticket_draft_consistency(
    response: ChatResponse,
    *,
    tool_results: list[dict[str, Any]],
) -> ChatResponse:
    if not response.ticket_draft.created:
        return response

    if has_created_ticket_draft_tool_result(tool_results):
        return response

    return response.model_copy(
        update={"ticket_draft": TicketDraftInfo(created=False, draft_id=None)}
    )


def repair_ticket_draft_info(
    response_data: dict[str, Any],
    *,
    fallback_draft_id: str | None,
) -> dict[str, Any]:
    ticket_draft = response_data.get("ticket_draft")
    if not isinstance(ticket_draft, dict):
        return response_data

    if ticket_draft.get("created") is True and not ticket_draft.get("draft_id"):
        if fallback_draft_id:
            ticket_draft["draft_id"] = fallback_draft_id
        else:
            ticket_draft["created"] = False
            ticket_draft["draft_id"] = None

    return response_data


def parse_final_chat_response(
    response: types.GenerateContentResponse,
    *,
    fallback_draft_id: str | None = None,
) -> ChatResponse:
    if response.parsed is not None:
        if isinstance(response.parsed, ChatResponse):
            return response.parsed
        parsed_data = response.parsed
        if isinstance(parsed_data, dict):
            parsed_data = repair_ticket_draft_info(
                parsed_data,
                fallback_draft_id=fallback_draft_id,
            )
        return ChatResponse.model_validate(parsed_data)

    cleaned_text = extract_response_json_text(response)

    try:
        return ChatResponse.model_validate_json(cleaned_text)
    except ValidationError:
        response_data = json.loads(cleaned_text)
        response_data = repair_ticket_draft_info(
            response_data,
            fallback_draft_id=fallback_draft_id,
        )
        return ChatResponse.model_validate(response_data)


def normalize_chat_response_confidence(response: ChatResponse) -> ChatResponse:
    # Confidence normalization / 置信度兜底：
    # LLM 有时会把 evidence-supported answer 直接打成 1.0。
    # 在 support 场景里，KB 命中代表“有依据”，但不代表“绝对确定”。
    max_confidence = (
        MAX_SUPPORTED_CONFIDENCE if response.citations else MAX_UNCITED_CONFIDENCE
    )
    if response.confidence <= max_confidence:
        return response

    return response.model_copy(update={"confidence": max_confidence})


def run_agent_chat(payload: ChatRequest, *, trace_id: str | None = None) -> ChatResponse:
    trace_id = trace_id or create_trace_id()
    started_at = time.perf_counter()
    tool_names: list[str] = []
    logger.info(
        "Agent chat started trace_id=%s session_id=%s",
        trace_id,
        payload.session_id,
    )

    try:
        client = get_gemini_client()
        session_history = get_session_history(payload.session_id)
        conversation_history = format_session_history(session_history)
        user_prompt = build_user_prompt(
            payload.query,
            payload.session_id,
            conversation_history=conversation_history,
        )

        first_response = generate_content(client, user_prompt, enable_tools=True)
        function_calls = first_response.function_calls or []

        if not function_calls:
            tool_results = []
            if query_is_likely_support_question(payload.query):
                supplemental_call = build_supplemental_kb_call(payload.query)
                logger.info(
                    "Agent supplemental tool call started trace_id=%s session_id=%s tool_name=%s",
                    trace_id,
                    payload.session_id,
                    supplemental_call.name,
                )
                tool_result = execute_mcp_tool(supplemental_call)
                tool_names.append("search_kb")
                logger.info(
                    "Agent supplemental tool call completed trace_id=%s session_id=%s tool_name=%s",
                    trace_id,
                    payload.session_id,
                    supplemental_call.name,
                )
                tool_results.append(
                    {
                        "tool_name": supplemental_call.name,
                        "tool_args": supplemental_call.args or {},
                        "tool_result": tool_result,
                    }
                )

            if query_explicitly_requests_ticket_draft(payload.query):
                supplemental_call = build_supplemental_ticket_draft_call(
                    payload.query,
                    tool_results,
                )
                logger.info(
                    "Agent supplemental tool call started trace_id=%s session_id=%s tool_name=%s",
                    trace_id,
                    payload.session_id,
                    supplemental_call.name,
                )
                tool_result = execute_mcp_tool(supplemental_call)
                tool_names.append("create_ticket_draft")
                logger.info(
                    "Agent supplemental tool call completed trace_id=%s session_id=%s tool_name=%s",
                    trace_id,
                    payload.session_id,
                    supplemental_call.name,
                )
                tool_results.append(
                    {
                        "tool_name": supplemental_call.name,
                        "tool_args": supplemental_call.args or {},
                        "tool_result": tool_result,
                    }
                )

            final_prompt = build_final_response_prompt(
                payload.query,
                payload.session_id,
                tool_results=tool_results,
                conversation_history=conversation_history,
            )
            final_response = generate_content(client, final_prompt, enable_tools=False)
            chat_response = normalize_chat_response_confidence(
                enforce_ticket_draft_consistency(
                    parse_final_chat_response(final_response),
                    tool_results=tool_results,
                )
            )
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            log_agent_trace(
                trace_id=trace_id,
                session_id=payload.session_id,
                query=payload.query,
                status="success",
                latency_ms=latency_ms,
                tool_names=tool_names,
                response=chat_response,
            )
            append_session_turn(
                payload.session_id,
                payload.query,
                chat_response,
            )
            logger.info(
                "Agent chat completed trace_id=%s session_id=%s tool_call_count=%d latency_ms=%d",
                trace_id,
                payload.session_id,
                len(tool_names),
                latency_ms,
            )
            return chat_response

        tool_results = []
        for function_call in function_calls:
            if (
                function_call.name == "create_ticket_draft"
                and not query_explicitly_requests_ticket_draft(payload.query)
            ):
                logger.info(
                    "Agent skipped unsolicited ticket draft trace_id=%s session_id=%s",
                    trace_id,
                    payload.session_id,
                )
                continue

            logger.info(
                "Agent tool call started trace_id=%s session_id=%s tool_name=%s",
                trace_id,
                payload.session_id,
                function_call.name,
            )
            tool_result = execute_mcp_tool(function_call)
            tool_names.append(function_call.name or "unknown")
            logger.info(
                "Agent tool call completed trace_id=%s session_id=%s tool_name=%s",
                trace_id,
                payload.session_id,
                function_call.name,
            )
            tool_results.append(
                {
                    "tool_name": function_call.name,
                    "tool_args": function_call.args or {},
                    "tool_result": tool_result,
                }
            )

        if query_needs_ticket_history(payload.query) and "search_tickets" not in tool_names:
            supplemental_call = build_supplemental_ticket_history_call(payload.query)
            logger.info(
                "Agent supplemental tool call started trace_id=%s session_id=%s tool_name=%s",
                trace_id,
                payload.session_id,
                supplemental_call.name,
            )
            tool_result = execute_mcp_tool(supplemental_call)
            tool_names.append("search_tickets")
            logger.info(
                "Agent supplemental tool call completed trace_id=%s session_id=%s tool_name=%s",
                trace_id,
                payload.session_id,
                supplemental_call.name,
            )
            tool_results.append(
                {
                    "tool_name": supplemental_call.name,
                    "tool_args": supplemental_call.args or {},
                    "tool_result": tool_result,
                }
            )

        if should_add_supplemental_kb(payload.query, tool_names):
            supplemental_call = build_supplemental_kb_call(payload.query)
            logger.info(
                "Agent supplemental tool call started trace_id=%s session_id=%s tool_name=%s",
                trace_id,
                payload.session_id,
                supplemental_call.name,
            )
            tool_result = execute_mcp_tool(supplemental_call)
            tool_names.append("search_kb")
            logger.info(
                "Agent supplemental tool call completed trace_id=%s session_id=%s tool_name=%s",
                trace_id,
                payload.session_id,
                supplemental_call.name,
            )
            tool_results.append(
                {
                    "tool_name": supplemental_call.name,
                    "tool_args": supplemental_call.args or {},
                    "tool_result": tool_result,
                }
            )

        if (
            query_explicitly_requests_ticket_draft(payload.query)
            and "create_ticket_draft" not in tool_names
        ):
            supplemental_call = build_supplemental_ticket_draft_call(
                payload.query,
                tool_results,
            )
            logger.info(
                "Agent supplemental tool call started trace_id=%s session_id=%s tool_name=%s",
                trace_id,
                payload.session_id,
                supplemental_call.name,
            )
            tool_result = execute_mcp_tool(supplemental_call)
            tool_names.append("create_ticket_draft")
            logger.info(
                "Agent supplemental tool call completed trace_id=%s session_id=%s tool_name=%s",
                trace_id,
                payload.session_id,
                supplemental_call.name,
            )
            tool_results.append(
                {
                    "tool_name": supplemental_call.name,
                    "tool_args": supplemental_call.args or {},
                    "tool_result": tool_result,
                }
            )

        final_prompt = build_final_response_prompt(
            payload.query,
            payload.session_id,
            tool_results=tool_results,
            conversation_history=conversation_history,
        )
        final_response = generate_content(client, final_prompt, enable_tools=False)
        chat_response = normalize_chat_response_confidence(
            enforce_ticket_draft_consistency(
                parse_final_chat_response(
                    final_response,
                    fallback_draft_id=find_created_ticket_draft_id(tool_results),
                ),
                tool_results=tool_results,
            )
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        log_agent_trace(
            trace_id=trace_id,
            session_id=payload.session_id,
            query=payload.query,
            status="success",
            latency_ms=latency_ms,
            tool_names=tool_names,
            response=chat_response,
        )
        append_session_turn(
            payload.session_id,
            payload.query,
            chat_response,
        )
        logger.info(
            "Agent chat completed trace_id=%s session_id=%s tool_call_count=%d latency_ms=%d",
            trace_id,
            payload.session_id,
            len(tool_names),
            latency_ms,
        )
        return chat_response
    except Exception as error:
        log_agent_trace(
            trace_id=trace_id,
            session_id=payload.session_id,
            query=payload.query,
            status="error",
            latency_ms=int((time.perf_counter() - started_at) * 1000),
            tool_names=tool_names,
            error_type=type(error).__name__,
            error=f"{type(error).__name__}: {error}",
        )
        raise


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(payload: ChatRequest, response: Response) -> ChatResponse:
    trace_id = create_trace_id()
    response.headers["X-Trace-Id"] = trace_id
    with agent_chat_span(
        trace_id=trace_id,
        session_id=payload.session_id,
        query=payload.query,
    ) as span:
        try:
            chat_response = run_agent_chat(payload, trace_id=trace_id)
            set_span_attribute(span, "agent.status", "success")
            set_span_attribute(
                span,
                "agent.citations_count",
                len(chat_response.citations),
            )
            set_span_attribute(
                span,
                "agent.ticket_draft_created",
                chat_response.ticket_draft.created,
            )
            return chat_response
        except RuntimeError as error:
            set_span_attribute(span, "agent.status", "error")
            logger.exception("Agent runtime error trace_id=%s", trace_id)
            raise HTTPException(status_code=500, detail=str(error)) from error
        except (ValueError, ValidationError) as error:
            set_span_attribute(span, "agent.status", "error")
            logger.exception("Agent response validation error trace_id=%s", trace_id)
            raise HTTPException(status_code=502, detail=str(error)) from error
        except Exception as error:
            set_span_attribute(span, "agent.status", "error")
            logger.exception("Unexpected agent error trace_id=%s", trace_id)
            raise HTTPException(
                status_code=500,
                detail=f"{type(error).__name__}: {error}",
            ) from error
