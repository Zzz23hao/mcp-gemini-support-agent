import argparse
import sys
import uuid

import httpx


DEFAULT_AGENT_URL = "http://127.0.0.1:8000"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive CLI for the Agent API.")
    parser.add_argument("--agent-url", default=DEFAULT_AGENT_URL)
    parser.add_argument(
        "--session-id",
        default=None,
        help="Reuse this session_id for multi-turn memory. Defaults to a generated id.",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser.parse_args()


def print_response(body: dict) -> None:
    print()
    print(f"Agent: {body.get('answer', '')}")

    citations = body.get("citations") or []
    if citations:
        print()
        print("Citations:")
        for citation in citations:
            print(f"- {citation.get('doc_id')} / {citation.get('chunk_id')}")

    next_actions = body.get("next_actions") or []
    if next_actions:
        print()
        print("Next actions:")
        for action in next_actions:
            print(f"- {action}")

    ticket_draft = body.get("ticket_draft") or {}
    if ticket_draft.get("created"):
        print()
        print(f"Ticket draft: {ticket_draft.get('draft_id')}")
    print()


def main() -> None:
    args = parse_args()
    session_id = args.session_id or f"cli-{uuid.uuid4().hex[:8]}"
    agent_url = args.agent_url.rstrip("/")

    print("MCP Gemini Support Agent CLI")
    print(f"Agent URL: {agent_url}")
    print(f"Session ID: {session_id}")
    print("Type 'exit' or 'quit' to stop.")
    print()

    with httpx.Client(timeout=args.timeout) as client:
        while True:
            try:
                query = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return

            if not query:
                continue
            if query.lower() in {"exit", "quit"}:
                return

            try:
                response = client.post(
                    f"{agent_url}/chat",
                    json={"query": query, "session_id": session_id},
                )
                trace_id = response.headers.get("x-trace-id")
                response.raise_for_status()
            except httpx.HTTPError as error:
                print(f"Request failed: {type(error).__name__}: {error}", file=sys.stderr)
                continue

            if trace_id:
                print(f"trace_id: {trace_id}")
            print_response(response.json())


if __name__ == "__main__":
    main()
