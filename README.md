# MCP Gemini Support Agent

Enterprise IT support agent built with Gemini, a local MCP-style tool server,
knowledge-base retrieval, historical ticket search, ticket draft creation,
evaluation, and observability.

The project is designed to answer support questions with evidence instead of
model memory. A user asks one question through `/chat`; the Agent API lets
Gemini select tools, executes those tools through the MCP-style HTTP server,
and returns a structured answer with citations, confidence, next actions, and
optional ticket draft status.

## Current Status

Implemented:

- KB document chunking and JSON index generation.
- Gemini embedding helper and ChromaDB vector index builder.
- MCP-style HTTP tool server.
- Agent API with Gemini function calling orchestration.
- Interactive CLI chat client.
- Simple local session memory for follow-up questions.
- Six support tools:
  - `search_kb`
  - `get_kb_doc`
  - `search_tickets`
  - `create_ticket_draft`
  - `log_feedback`
  - `get_health`
- End-to-end eval runner and LLM judge.
- Structured JSON trace logs and OpenTelemetry spans.

Latest local verification:

```bash
uv run pytest -q
```

Result:

```text
134 passed, 1 warning, 2 subtests passed
```

## Architecture

```text
User
  -> Agent API: POST /chat
  -> Gemini tool selection
  -> MCP tool HTTP server
       -> search_kb
       -> get_kb_doc
       -> search_tickets
       -> create_ticket_draft
  -> Gemini final JSON response
  -> ChatResponse with answer, citations, confidence, next_actions, ticket_draft
```

Main layers:

```text
data/kb_docs/                 Source KB Markdown documents
data/kb_index/chunks.json     Chunked KB index
data/kb_index/chroma/         ChromaDB vector index
data/tickets.json             Mock historical support tickets
data/ticket_drafts.json       Created ticket draft records
data/agent_traces.jsonl       Append-only Agent trace logs
data/session_memory.json      Local per-session chat memory

src/indexing/                 Chunking, embedding, index builders
src/mcp_server/               MCP-style tool schemas and HTTP endpoints
src/agent_api/                Gemini Agent API, prompts, schemas, observability
src/eval/                     End-to-end eval runner and LLM judge
tests/                        Unit and integration-style tests
```

## Requirements

- Python 3.12+
- `uv`
- Gemini API key

Install dependencies:

```bash
uv sync
```

## Environment

Create a `.env` file:

```bash
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_JUDGE_MODEL=gemini-2.5-flash
MCP_SERVER_URL=http://127.0.0.1:7001

# Optional observability settings
OTEL_TRACING_ENABLED=true
OTEL_EXPORTER=console
# OTEL_EXPORTER=otlp
# OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

Notes:

- `GEMINI_API_KEY` is required for Gemini chat, embedding, and LLM judge calls.
- `MCP_SERVER_URL` tells the Agent API where the MCP-style tool server is
  running.
- `OTEL_EXPORTER=console` prints OpenTelemetry spans to stdout.
- `OTEL_EXPORTER=otlp` sends traces to an OTLP collector.

## Build Indexes

Build the JSON KB chunk index:

```bash
uv run python -m src.indexing.build_kb
```

Build the ChromaDB vector index:

```bash
uv run python -m src.indexing.build_vector_index --delay-seconds 1
```

For a quota-safe smoke test:

```bash
uv run python -m src.indexing.build_vector_index --limit 3 --delay-seconds 1
```

The current `search_kb` endpoint uses the keyword search path by default. The
vector index is implemented and available through `vector_search_kb` for
semantic retrieval experiments.

## Run Locally

One-command local startup:

```bash
./scripts/dev.sh
```

This starts both services:

```text
MCP docs:   http://127.0.0.1:7001/docs
Agent docs: http://127.0.0.1:8000/docs
```

Press `Ctrl-C` to stop both services.

If the default ports are already in use:

```bash
MCP_PORT=7002 AGENT_PORT=8003 ./scripts/dev.sh
```

OpenTelemetry console spans are disabled by default in the script to keep local
logs readable. Enable them explicitly:

```bash
OTEL_TRACING_ENABLED=true ./scripts/dev.sh
```

Manual startup is also supported. Use two terminals.

Terminal 1: start the MCP-style tool server.

```bash
uv run uvicorn src.mcp_server.server:app --host 127.0.0.1 --port 7001
```

Tool server docs:

```text
http://127.0.0.1:7001/docs
```

Terminal 2: start the Agent API.

```bash
MCP_SERVER_URL=http://127.0.0.1:7001 \
uv run uvicorn src.agent_api.main:app --host 127.0.0.1 --port 8000
```

Agent API docs:

```text
http://127.0.0.1:8000/docs
```

## Demo Request

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I cannot log in with SSO, what should I do?",
    "session_id": "demo1"
  }'
```

Expected response shape:

```json
{
  "answer": "...",
  "citations": [
    {
      "doc_id": "sso_login_troubleshooting",
      "chunk_id": "sso_login_troubleshooting#003",
      "quote": "..."
    }
  ],
  "confidence": 0.8,
  "next_actions": ["..."],
  "ticket_draft": {
    "created": false,
    "draft_id": null
  }
}
```

Ticket draft example:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Multiple users cannot log in with SSO. Please create a ticket draft.",
    "session_id": "demo-ticket"
  }'
```

## Interactive CLI

Start the local services first:

```bash
./scripts/dev.sh
```

Then open another terminal and start an interactive chat session:

```bash
uv run python -m src.agent_api.chat_cli --session-id demo1
```

Useful options:

```bash
uv run python -m src.agent_api.chat_cli \
  --agent-url http://127.0.0.1:8000 \
  --session-id demo1 \
  --timeout 60
```

Type `exit` or `quit` to close the CLI.

The CLI calls the same `/chat` endpoint as Swagger and curl. The difference is
that it keeps you inside a conversational loop, so follow-up questions are
easier to test.

## Session Memory

The Agent API now keeps a small local memory per `session_id`.

Storage:

```text
data/session_memory.json
```

Behavior:

```text
same session_id  -> previous turns are included in the next prompt
new session_id   -> starts a separate conversation
max turns        -> latest 8 turns per session
```

Important constraint: session memory is only used to resolve follow-up wording,
such as "what about the second step?" or "create a ticket for that issue." It is
not treated as factual evidence. The Agent still needs KB citations, ticket
search results, or tool output to support the final answer.

## MCP Tool Endpoints

The MCP-style server exposes:

```text
POST /tool/search_kb
POST /tool/get_kb_doc
POST /tool/search_tickets
POST /tool/create_ticket_draft
POST /tool/log_feedback
GET  /health
```

Example:

```bash
curl -X POST http://127.0.0.1:7001/tool/search_kb \
  -H "Content-Type: application/json" \
  -d '{"query": "SSO login failed", "top_k": 5}'
```

Health check:

```bash
curl http://127.0.0.1:7001/health
```

## Evaluation

The eval dataset is stored in:

```text
src/eval/questions.jsonl
```

It covers:

```text
pure_kb
kb_plus_tickets
ticket_draft
no_answer
edge_case
```

Run a full eval against a running Agent API:

```bash
uv run python -m src.eval.run_eval \
  --agent-url http://127.0.0.1:8000 \
  --delay 5 \
  --retries 3 \
  --retry-delay 20 \
  --report eval/report.json
```

Run only edge cases:

```bash
uv run python -m src.eval.run_eval \
  --agent-url http://127.0.0.1:8000 \
  --category edge_case \
  --delay 5 \
  --retries 3 \
  --retry-delay 20 \
  --report eval/edge_report.json
```

Run selected IDs:

```bash
uv run python -m src.eval.run_eval \
  --agent-url http://127.0.0.1:8000 \
  --ids q051,q052 \
  --report eval/selected_report.json
```

The eval report records:

```text
latency_ms
trace_id
tool_calls_count
tool_names
has_citations
citations_count
answer_length
must_include matching
ticket draft behavior
quota/provider blocking
```

## LLM Judge

The LLM judge uses Gemini to score actual Agent responses.

Run:

```bash
uv run python -m src.eval.judge \
  --report eval/report.json \
  --output eval/judged_report.json
```

Quota-safe smoke test:

```bash
uv run python -m src.eval.judge \
  --report eval/report.json \
  --output eval/judged_report.json \
  --limit 3
```

The judge scores:

```text
groundedness    Whether citations support the answer
completeness    Whether required concepts and user intent are covered
hallucination   Whether unsupported facts are avoided
```

## Observability

This project has two observability layers.

Structured JSON logs:

```text
src/agent_api/tracing.py
```

Each chat turn writes one summary record to stdout and
`data/agent_traces.jsonl`, including:

```text
session_id
trace_id
latency_ms
tool_calls
error_type
estimated_input_tokens
estimated_output_tokens
```

OpenTelemetry tracing:

```text
src/agent_api/observability.py
```

Span structure:

```text
agent.chat
  -> agent.tool_call search_kb
  -> agent.tool_call search_tickets
  -> agent.tool_call create_ticket_draft
```

Logs summarize what happened. Traces show where time was spent inside the
request.

Disable OpenTelemetry tracing:

```bash
OTEL_TRACING_ENABLED=false \
uv run uvicorn src.agent_api.main:app --host 127.0.0.1 --port 8000
```

Use OTLP:

```bash
OTEL_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces \
uv run uvicorn src.agent_api.main:app --host 127.0.0.1 --port 8000
```

## Testing

Run all tests:

```bash
uv run pytest -q
```

Run focused test groups:

```bash
uv run pytest -q tests/test_tools.py
uv run pytest -q tests/test_agent_api.py
uv run pytest -q tests/test_memory.py
uv run pytest -q tests/test_chat_cli.py
uv run pytest -q tests/test_run_eval.py tests/test_judge.py
uv run pytest -q tests/test_observability.py
```

Current verified result:

```text
134 passed, 1 warning, 2 subtests passed
```

## Reliability Features

The Agent API includes:

- Tool call timeout: `TOOL_TIMEOUT_SECONDS = 5.0`
- Retry for transient tool failures: `429` and `5xx`
- Exponential backoff
- Request-level `trace_id`
- Session-level `session_id`
- Backend fallback to `search_kb` for likely support questions
- Backend fallback to `create_ticket_draft` when the user explicitly requests a draft
- Confidence normalization
- Ticket draft consistency checks

## Important Design Decisions

Gemini tool calling and final JSON generation are split into two phases:

```text
Phase 1: Gemini may call tools
Phase 2: tools are disabled, Gemini returns ChatResponse JSON
```

Reason: Gemini function calling with `response_mime_type="application/json"` is
not supported in the same request. Splitting the flow makes tool use and final
schema validation more reliable.

The model only controls business tools:

```text
search_kb
get_kb_doc
search_tickets
create_ticket_draft
```

System/ops tools are not exposed to Gemini:

```text
log_feedback
get_health
```

## Limitations

- This is a local portfolio/demo system, not a deployed production service.
- The MCP layer is implemented as an HTTP tool server, not the full standard
  MCP transport.
- Gemini API quota and provider instability can affect eval runs.
- Vector search exists, but the default `search_kb` endpoint currently uses
  keyword retrieval.
- Session memory is local JSON memory. It is useful for demos and follow-up
  questions, but it is not a production memory store with summarization,
  retention policy, or user-level access control.
- No multi-agent routing is implemented.
- Ticket and KB data are local mock data.

## Interview Summary

This project is an enterprise IT support agent using Gemini and an MCP-style
tool architecture. It retrieves evidence from internal KB documents, searches
historical tickets, creates ticket drafts, and returns structured grounded
answers with citations. The project includes reliability controls, regression
evaluation, LLM-as-a-judge scoring, structured logs, and OpenTelemetry tracing,
so it is closer to an engineering system than a simple chatbot demo.
