import argparse
import json
import re
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_PATH = PROJECT_ROOT / "src" / "eval" / "questions.jsonl"
REPORT_PATH = PROJECT_ROOT / "eval" / "report.json"
AGENT_TRACE_PATH = PROJECT_ROOT / "data" / "agent_traces.jsonl"
DEFAULT_AGENT_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 60.0
ANSWER_SNIPPET_CHARS = 700
DEFAULT_RETRY_COUNT = 2
DEFAULT_RETRY_DELAY_SECONDS = 5.0

TERM_ALIASES = {
    "clear cache": [
        "clear cache",
        "clear browser cache",
        "clear your browser cache",
        "clear your browser's cache",
        "clear cache and cookies",
        "clear browser's cache and cookies",
    ],
    "network connection": [
        "network connection",
        "internet connection",
        "internet access",
        "active internet access",
        "home network",
        "local network",
        "connectivity",
    ],
    "vpn": [
        "VPN",
        "vpn",
    ],
    "credentials": [
        "credentials",
        "login credentials",
        "username",
        "password",
        "user name",
    ],
    "mfa": [
        "MFA",
        "multi factor authentication",
        "multi-factor authentication",
    ],
    "cannot": [
        "cannot",
        "can't",
        "can not",
        "not possible",
        "not allowed",
        "not permitted",
    ],
    "hr": [
        "HR",
        "human resources",
        "people team",
    ],
    "identity verification": [
        "identity verification",
        "verify identity",
        "verify the user s identity",
        "verify the user's identity",
        "identity is verified",
        "identity must first be verified",
        "identity needs to be verified",
        "identity will need to be verified",
        "identity will be verified",
        "ensure your identity is verified",
        "identity is confirmed",
        "identity confirmation",
        "confirm identity",
        "confirming your identity",
        "confirm your identity",
        "after confirming your identity",
        "identity check",
        "verify your identity",
    ],
    "password reset": [
        "password reset",
        "reset password",
        "reset your password",
    ],
    "account locked": [
        "account locked",
        "account is locked",
        "account temporarily locked",
        "locked account",
        "lockout",
        "lockout status",
    ],
    "setup": [
        "setup",
        "set up",
        "setting up",
        "installation",
        "configure",
        "configuration",
    ],
    "approval": [
        "approval",
        "approved",
        "approver",
        "manager approval",
        "owner approval",
        "business approval",
        "requires approval",
        "approval workflow",
        "business justification",
    ],
    "assignment": [
        "assignment",
        "assigned",
        "assigned to",
    ],
    "enrollment": [
        "enrollment",
        "enroll",
        "enrolled",
        "enrolling",
    ],
    "timeout": [
        "timeout",
        "timed out",
        "timing out",
        "connection timed out",
        "connection timeout",
    ],
    "database": [
        "database",
        "db",
    ],
    "queue": [
        "queue",
        "queued",
        "backlog",
        "retry loop",
        "indefinite retries",
    ],
    "similar": [
        "similar",
        "common",
        "seen before",
        "previous",
        "past",
        "historical",
    ],
    "ticket": [
        "ticket",
        "draft",
        "support request",
        "case",
    ],
    "not sure": [
        "not sure",
        "couldn't find",
        "could not find",
        "do not have information",
        "don't have information",
        "not equipped",
        "not able",
        "unable",
        "outside my scope",
        "outside the scope",
        "cannot provide",
        "cannot approve",
        "cannot process",
        "do not have access",
        "don't have access",
    ],
    "sensitive": [
        "sensitive",
        "privacy",
        "private",
        "personal information",
        "protected",
        "confidential",
    ],
    "secret": [
        "secret",
        "password",
        "root password",
        "credential",
        "credentials",
    ],
    "internal": [
        "internal",
        "unreleased",
        "roadmap",
        "confidential",
        "sensitive",
    ],
    "authentication": [
        "authentication",
        "authenticate",
        "auth",
        "identity provider outage",
    ],
    "prompt injection": [
        "prompt injection",
        "ignore instructions",
        "cannot ignore",
        "follow security",
        "safety",
    ],
    "crashloopbackoff": [
        "CrashLoopBackOff",
        "crashloopbackoff",
        "crashloop",
        "crashloops",
        "crashlooping",
    ],
    "unused resources": [
        "unused resources",
        "idle resources",
        "non production resources",
        "non-production resources",
        "stop any non production",
        "stop any non-production",
    ],
    "image tag": [
        "image tag",
        "container image tag",
        "tag",
    ],
    "registry": [
        "registry",
        "container registry",
        "image registry",
    ],
    "compliance": [
        "compliance",
        "compliant",
        "compliance policies",
        "device compliance",
        "conditional access",
    ],
    "expiration": [
        "expiration",
        "expired",
        "validity period",
        "not yet valid",
        "certificate validity",
    ],
    "logging": [
        "logging",
        "logs",
        "log access",
        "logging dashboard",
        "production logs",
    ],
    "escalate": [
        "escalate",
        "escalation",
        "route",
        "routed",
        "notify",
        "contact",
        "please contact",
        "security operations",
        "security operations team",
        "contact security",
    ],
    "verify": [
        "verify",
        "validate",
        "confirm",
        "monitor",
        "check",
    ],
    "group": [
        "group",
        "identity group",
        "groups",
        "team",
        "teams",
    ],
    "cleanup": [
        "cleanup",
        "clean up",
        "free up",
        "remove old",
        "temporary files",
        "clear caches",
    ],
    "incognito": [
        "incognito",
        "private window",
        "private browsing",
        "private browsing window",
        "different browser",
        "different web browser",
        "another supported browser",
    ],
}


def load_questions(path: Path = QUESTIONS_PATH) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_csv_filter(value: str | None) -> set[str] | None:
    if not value:
        return None
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    return parsed or None


def filter_questions(
    questions: list[dict[str, Any]],
    *,
    categories: set[str] | None = None,
    ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    if categories is not None:
        questions = [
            question
            for question in questions
            if question.get("category") in categories
        ]

    if ids is not None:
        questions = [question for question in questions if question.get("id") in ids]

    return questions


def load_trace_records(path: Path = AGENT_TRACE_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}

    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        trace_id = record.get("trace_id")
        if trace_id:
            records[trace_id] = record
    return records


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def get_term_variants(term: str) -> list[str]:
    return TERM_ALIASES.get(term.lower(), [term])


def term_matches(answer: str, term: str) -> bool:
    normalized_answer = normalize_text(answer)
    return any(
        normalize_text(variant) in normalized_answer
        for variant in get_term_variants(term)
    )


def find_term_matches(
    answer: str,
    must_include: list[str],
) -> tuple[list[str], list[str]]:
    matched = []
    missing = []
    for term in must_include:
        if term_matches(answer, term):
            matched.append(term)
        else:
            missing.append(term)
    return matched, missing


def find_missing_terms(answer: str, must_include: list[str]) -> list[str]:
    _, missing = find_term_matches(answer, must_include)
    return missing


def is_quota_error(error: str | None) -> bool:
    if not error:
        return False
    normalized_error = error.lower()
    return (
        "resource_exhausted" in normalized_error
        or "quota exceeded" in normalized_error
        or "429" in normalized_error
    )


def is_transient_provider_error(error: str | None) -> bool:
    if not error:
        return False
    normalized_error = error.lower()
    return (
        "503" in normalized_error
        or "unavailable" in normalized_error
        or "high demand" in normalized_error
        or "try again later" in normalized_error
    )


def build_answer_snippet(answer: str, max_chars: int = ANSWER_SNIPPET_CHARS) -> str:
    if len(answer) <= max_chars:
        return answer
    return f"{answer[:max_chars].rstrip()}..."


def score_response(
    question: dict[str, Any],
    response_body: dict[str, Any],
    *,
    status_code: int,
    latency_ms: int,
    trace_id: str | None,
    trace_record: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    answer = response_body.get("answer", "") if response_body else ""
    citations = response_body.get("citations", []) if response_body else []
    ticket_draft = response_body.get("ticket_draft", {}) if response_body else {}

    matched_must_include, missing_must_include = find_term_matches(
        answer,
        question.get("must_include", []),
    )
    blocked_by_quota = is_quota_error(error)
    blocked_by_provider = is_transient_provider_error(error)
    has_citations = bool(citations)
    citation_check_passed = (
        has_citations if question.get("must_cite", False) else True
    )
    ticket_draft_created = bool(ticket_draft.get("created", False))
    ticket_draft_check_passed = (
        ticket_draft_created == question.get("expect_ticket_draft", False)
    )
    status_ok = status_code == 200 and error is None

    ok = (
        status_ok
        and not missing_must_include
        and citation_check_passed
        and ticket_draft_check_passed
    )

    return {
        "id": question["id"],
        "category": question.get("category"),
        "query": question["query"],
        "status_code": status_code,
        "ok": ok,
        "latency_ms": latency_ms,
        "trace_id": trace_id,
        "tool_calls_count": (
            trace_record.get("tool_call_count") if trace_record else None
        ),
        "tool_names": trace_record.get("tool_names", []) if trace_record else [],
        "has_citations": has_citations,
        "citations_count": len(citations),
        "citations": citations,
        "answer_length": len(answer),
        "answer": answer,
        "answer_snippet": build_answer_snippet(answer),
        "must_include": question.get("must_include", []),
        "matched_must_include": matched_must_include,
        "missing_must_include": missing_must_include,
        "blocked_by_quota": blocked_by_quota,
        "blocked_by_provider": blocked_by_provider,
        "must_cite": question.get("must_cite", False),
        "citation_check_passed": citation_check_passed,
        "expect_ticket_draft": question.get("expect_ticket_draft", False),
        "ticket_draft_created": ticket_draft_created,
        "ticket_draft_check_passed": ticket_draft_check_passed,
        "error": error,
    }


def evaluate_question(
    question: dict[str, Any],
    *,
    client: httpx.Client,
    agent_url: str,
    trace_path: Path,
    retry_count: int = DEFAULT_RETRY_COUNT,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    status_code = 0
    trace_id = None
    response_body: dict[str, Any] = {}
    error = None
    attempt = 0

    while attempt <= retry_count:
        try:
            response = client.post(
                f"{agent_url.rstrip('/')}/chat",
                json={
                    "query": question["query"],
                    "session_id": f"eval-{question['id']}",
                },
            )
            status_code = response.status_code
            trace_id = response.headers.get("x-trace-id")
            response_body = response.json()
            error = None
            if status_code >= 400:
                error = response_body.get("detail", f"HTTP {status_code}")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        if not is_transient_provider_error(error) or attempt == retry_count:
            break

        attempt += 1
        time.sleep(retry_delay_seconds)

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    trace_records = load_trace_records(trace_path)
    trace_record = trace_records.get(trace_id) if trace_id else None

    return score_response(
        question,
        response_body,
        status_code=status_code,
        latency_ms=latency_ms,
        trace_id=trace_id,
        trace_record=trace_record,
        error=error,
    )


def summarize_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "passed": 0, "failed": 0}
    )
    for result in results:
        category = result.get("category") or "unknown"
        by_category[category]["total"] += 1
        if result["ok"]:
            by_category[category]["passed"] += 1
        else:
            by_category[category]["failed"] += 1

    passed_count = sum(1 for result in results if result["ok"])
    failed_count = len(results) - passed_count
    quota_blocked_count = sum(
        1 for result in results if result.get("blocked_by_quota")
    )
    provider_blocked_count = sum(
        1 for result in results if result.get("blocked_by_provider")
    )
    quality_results = [
        result
        for result in results
        if not result.get("blocked_by_quota")
        and not result.get("blocked_by_provider")
    ]
    quality_passed_count = sum(1 for result in quality_results if result["ok"])
    quality_failed_count = len(quality_results) - quality_passed_count
    latencies = [result["latency_ms"] for result in results]

    return {
        "total": len(results),
        "passed": passed_count,
        "failed": failed_count,
        "blocked_by_quota": quota_blocked_count,
        "blocked_by_provider": provider_blocked_count,
        "pass_rate": passed_count / len(results) if results else 0.0,
        "quality_total_excluding_quota": len(quality_results),
        "quality_passed_excluding_quota": quality_passed_count,
        "quality_failed_excluding_quota": quality_failed_count,
        "quality_pass_rate_excluding_quota": (
            quality_passed_count / len(quality_results)
            if quality_results
            else 0.0
        ),
        "average_latency_ms": (
            sum(latencies) / len(latencies) if latencies else 0.0
        ),
        "by_category": dict(by_category),
    }


def run_evaluation(
    *,
    questions_path: Path = QUESTIONS_PATH,
    report_path: Path = REPORT_PATH,
    trace_path: Path = AGENT_TRACE_PATH,
    agent_url: str = DEFAULT_AGENT_URL,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    limit: int | None = None,
    categories: set[str] | None = None,
    ids: set[str] | None = None,
    delay_seconds: float = 0.0,
    retry_count: int = DEFAULT_RETRY_COUNT,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict[str, Any]:
    questions = load_questions(questions_path)
    questions = filter_questions(questions, categories=categories, ids=ids)
    if limit is not None:
        questions = questions[:limit]
    results = []

    with httpx.Client(timeout=timeout_seconds) as client:
        for index, question in enumerate(questions):
            if index > 0 and delay_seconds > 0:
                time.sleep(delay_seconds)
            results.append(
                evaluate_question(
                    question,
                    client=client,
                    agent_url=agent_url,
                    trace_path=trace_path,
                    retry_count=retry_count,
                    retry_delay_seconds=retry_delay_seconds,
                )
            )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "agent_url": agent_url,
        "questions_path": str(questions_path),
        "filters": {
            "categories": sorted(categories) if categories else None,
            "ids": sorted(ids) if ids else None,
            "limit": limit,
        },
        "summary": summarize_results(results),
        "results": results,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Agent API evaluation set.")
    parser.add_argument("--agent-url", default=DEFAULT_AGENT_URL)
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--trace-log", type=Path, default=AGENT_TRACE_PATH)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N questions. Useful for quota-safe smoke tests.",
    )
    parser.add_argument(
        "--category",
        default=None,
        help="Comma-separated category filter, e.g. edge_case,no_answer.",
    )
    parser.add_argument(
        "--ids",
        default=None,
        help="Comma-separated question id filter, e.g. q051,q052.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Seconds to wait between questions to avoid model rate limits.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRY_COUNT,
        help="Retry count for transient provider errors such as 503 high demand.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_RETRY_DELAY_SECONDS,
        help="Seconds to wait before retrying transient provider errors.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_evaluation(
        questions_path=args.questions,
        report_path=args.report,
        trace_path=args.trace_log,
        agent_url=args.agent_url,
        timeout_seconds=args.timeout,
        limit=args.limit,
        categories=parse_csv_filter(args.category),
        ids=parse_csv_filter(args.ids),
        delay_seconds=args.delay,
        retry_count=args.retries,
        retry_delay_seconds=args.retry_delay,
    )
    summary = report["summary"]
    print(
        "Evaluation complete: "
        f"{summary['passed']}/{summary['total']} passed "
        f"({summary['pass_rate']:.0%}). "
        f"Report: {args.report}"
    )


if __name__ == "__main__":
    main()
