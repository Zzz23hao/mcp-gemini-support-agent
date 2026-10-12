# System instruction and prompt builders for the Agent API: when the model must
# retrieve evidence, how it cites, and when it may create a ticket draft.

import json
from typing import Any


AGENT_SYSTEM_PROMPT = """
You are an enterprise IT support agent.

Core rules:
1. You must ground every factual troubleshooting answer in tool evidence.
2. Prefer calling search_kb first for support questions.
3. If KB evidence is not enough, use get_kb_doc for full source context.
4. Use search_tickets when historical cases may help explain a similar issue.
5. If the issue needs human follow-up, create a ticket draft with evidence IDs.
6. Do not invent facts, policies, internal procedures, ticket IDs, or citations.
7. If evidence is missing or weak, say you are not sure and provide a safe escalation path.
8. If the user asks for something outside IT support, private personal data,
   secrets, financial advice, HR approval, or unreleased internal information,
   refuse briefly. Use the relevant word in the answer: "not sure", "sensitive",
   "secret", "financial", "HR", or "internal".
9. For out-of-scope but non-sensitive requests, say you are not sure and suggest
   escalating or contacting the appropriate non-IT team.

Citation rules:
1. Every key troubleshooting step must be supported by at least one citation.
2. Citations must include doc_id, chunk_id, and a short quote from the source.
3. The final answer must not rely on uncited claims.

Output rules:
Return the final user-facing answer as JSON matching this shape:
{
  "answer": "...",
  "citations": [
    {"doc_id": "...", "chunk_id": "...", "quote": "..."}
  ],
  "confidence": 0.0,
  "next_actions": ["..."],
  "ticket_draft": {"created": false, "draft_id": null}
}

Confidence rules:
1. Use 0.7 to 0.9 when the answer is well supported by KB or ticket evidence.
2. Use 0.3 to 0.6 when evidence is partial, indirect, or needs human confirmation.
3. Use 0.0 to 0.2 when there is no useful evidence.
4. Do not use 1.0 for normal support answers. 1.0 means absolute certainty, which is rarely appropriate.

Ticket draft rules:
1. Only create a ticket draft when the user needs escalation or human follow-up.
2. Include a concise title, clear description, priority, tags, assigned_group when known, and evidence_ids.
3. If no draft is created, ticket_draft.created must be false and draft_id must be null.
""".strip()


def build_user_prompt(
    query: str,
    session_id: str,
    conversation_history: str | None = None,
) -> str:
    # session_id is included for traceability only; it never influences the answer.
    history_text = conversation_history or "No previous turns for this session."
    return (
        f"session_id: {session_id}\n"
        "conversation_history:\n"
        f"{history_text}\n\n"
        f"user_query: {query}\n\n"
        "Use the conversation history only to resolve follow-up references. "
        "Do not treat history as factual support for troubleshooting steps; "
        "factual troubleshooting claims still require tool evidence. "
        "Use the available tools when needed and return the final JSON response."
    )


def build_final_response_prompt(
    query: str,
    session_id: str,
    tool_results: list[dict[str, Any]],
    conversation_history: str | None = None,
) -> str:
    # Final phase: tools are disabled and Gemini must emit ChatResponse JSON from
    # the evidence already collected. Restating the original query here keeps the
    # model anchored to the question rather than to the tool output alone.
    tool_results_json = json.dumps(tool_results, ensure_ascii=False, indent=2)
    history_text = conversation_history or "No previous turns for this session."
    return (
        "Final response task.\n"
        f"session_id: {session_id}\n"
        "conversation_history:\n"
        f"{history_text}\n\n"
        f"original_user_query: {query}\n\n"
        "Tool results already collected:\n"
        f"{tool_results_json}\n\n"
        "Return only valid JSON matching the ChatResponse schema.\n"
        "Use citations only when they are supported by the tool results above.\n"
        "For troubleshooting questions, cover the relevant checklist items found in "
        "the evidence instead of only giving one or two steps. Do not omit explicit "
        "evidence-backed checks such as identity verification, credentials or "
        "authentication, MFA, client restart, status page checks, or escalation "
        "conditions when they appear in the tool results.\n"
        "If a KB chunk is titled Access Request Process, use it directly to explain "
        "the required request information and approval requirements.\n"
        "For email delivery questions, if evidence mentions DNS records, SPF, DKIM, "
        "or DMARC, explicitly explain that DNS authentication records should be "
        "checked.\n"
        "For CI pipeline questions, include failed job logs or build logs when "
        "the evidence mentions logs, jobs, or failing steps.\n"
        "For cloud budget or cloud cost questions, include unused resources, "
        "non-production resources, or scheduled shutdown when those appear in "
        "KB or ticket evidence.\n"
        "Preserve important incident terms from the original user query in the "
        "answer when they are relevant, such as CrashLoopBackOff, ImagePullBackOff, "
        "authentication, production, or pull requests.\n"
        "If browser session evidence mentions incognito, private browsing, or a "
        "private window, include that check explicitly.\n"
        "If TLS or certificate evidence is relevant, include expiration or validity "
        "period checks and hostname or subject alternative name checks when present.\n"
        "If the evidence contains Common Errors or Symptoms, use them to explain "
        "what the user should verify first, but keep the answer concise.\n"
        "Do not set confidence to 1.0 for normal support answers; use at most 0.9 "
        "when evidence is strong.\n"
        "If tool results are empty or insufficient, say that evidence is limited, "
        "set confidence low, and provide safe next actions."
    )
