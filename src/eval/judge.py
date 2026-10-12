import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from src.eval.run_eval import PROJECT_ROOT, REPORT_PATH


load_dotenv()


DEFAULT_JUDGE_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_ANSWER_CHARS = 3000


class JudgeScores(BaseModel):
    groundedness: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    hallucination: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


def get_judge_model_name() -> str:
    return os.getenv("GEMINI_JUDGE_MODEL") or os.getenv(
        "GEMINI_MODEL",
        DEFAULT_JUDGE_MODEL,
    )


def get_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required to run LLM judge")
    return genai.Client(api_key=api_key)


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def build_judge_prompt(result: dict[str, Any]) -> str:
    answer = result.get("answer") or result.get("answer_snippet") or ""
    if len(answer) > DEFAULT_MAX_ANSWER_CHARS:
        answer = f"{answer[:DEFAULT_MAX_ANSWER_CHARS].rstrip()}..."

    citations = result.get("citations", [])
    judge_payload = {
        "question_id": result.get("id"),
        "category": result.get("category"),
        "user_query": result.get("query"),
        "must_include": result.get("must_include", []),
        "must_cite": result.get("must_cite"),
        "expect_ticket_draft": result.get("expect_ticket_draft"),
        "ticket_draft_created": result.get("ticket_draft_created"),
        "answer": answer,
        "citations": citations,
    }

    return (
        "You are judging an enterprise IT support agent response.\n"
        "Return only JSON matching this schema:\n"
        "{"
        '"groundedness": 0.0, '
        '"completeness": 0.0, '
        '"hallucination": 0.0, '
        '"rationale": "short explanation"'
        "}\n\n"
        "Scoring rules:\n"
        "- groundedness: 1.0 means the answer is well supported by citations; "
        "0.0 means key claims are unsupported.\n"
        "- completeness: 1.0 means the answer covers the required concepts and "
        "the user intent; 0.0 means it misses most required concepts.\n"
        "- hallucination: 1.0 means no unsupported or invented facts; 0.0 means "
        "the answer contains serious unsupported claims.\n"
        "- If citations are not required, score groundedness based on whether "
        "the refusal or no-answer behavior is appropriate.\n\n"
        "Evaluation item:\n"
        f"{json.dumps(judge_payload, ensure_ascii=False, indent=2)}"
    )


def parse_judge_response(response: types.GenerateContentResponse) -> JudgeScores:
    if response.parsed is not None:
        if isinstance(response.parsed, JudgeScores):
            return response.parsed
        return JudgeScores.model_validate(response.parsed)

    text = (response.text or "").strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").removesuffix("```").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").removesuffix("```").strip()

    try:
        return JudgeScores.model_validate_json(text)
    except ValidationError:
        return JudgeScores.model_validate(json.loads(text))


def judge_result(
    client: genai.Client,
    result: dict[str, Any],
    *,
    model_name: str,
) -> JudgeScores:
    response = client.models.generate_content(
        model=model_name,
        contents=build_judge_prompt(result),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JudgeScores,
        ),
    )
    return parse_judge_response(response)


def should_judge_result(result: dict[str, Any]) -> bool:
    return bool(result.get("answer") or result.get("answer_snippet"))


def summarize_judgments(results: list[dict[str, Any]]) -> dict[str, Any]:
    judged_results = [result for result in results if result.get("llm_judge")]
    if not judged_results:
        return {
            "total_judged": 0,
            "average_groundedness": 0.0,
            "average_completeness": 0.0,
            "average_hallucination": 0.0,
        }

    return {
        "total_judged": len(judged_results),
        "average_groundedness": sum(
            result["llm_judge"]["groundedness"] for result in judged_results
        )
        / len(judged_results),
        "average_completeness": sum(
            result["llm_judge"]["completeness"] for result in judged_results
        )
        / len(judged_results),
        "average_hallucination": sum(
            result["llm_judge"]["hallucination"] for result in judged_results
        )
        / len(judged_results),
    }


def run_judge(
    *,
    report_path: Path = REPORT_PATH,
    output_path: Path | None = None,
    limit: int | None = None,
    model_name: str | None = None,
    client: genai.Client | None = None,
) -> dict[str, Any]:
    report = load_report(report_path)
    results = report.get("results", [])
    target_results = [result for result in results if should_judge_result(result)]
    if limit is not None:
        target_results = target_results[:limit]

    judge_client = client or get_gemini_client()
    judge_model_name = model_name or get_judge_model_name()

    result_by_id = {result.get("id"): result for result in results}
    for result in target_results:
        scores = judge_result(judge_client, result, model_name=judge_model_name)
        result_by_id[result.get("id")]["llm_judge"] = scores.model_dump()

    report["llm_judge"] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": judge_model_name,
        "summary": summarize_judgments(results),
    }

    save_report(report, output_path or report_path)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Gemini LLM judge on eval report.")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output path. Defaults to overwriting --report.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Judge only the first N judgeable results for quota-safe smoke tests.",
    )
    parser.add_argument("--model", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_judge(
        report_path=args.report,
        output_path=args.output,
        limit=args.limit,
        model_name=args.model,
    )
    summary = report["llm_judge"]["summary"]
    print(
        "LLM judge complete: "
        f"{summary['total_judged']} judged, "
        f"groundedness={summary['average_groundedness']:.2f}, "
        f"completeness={summary['average_completeness']:.2f}, "
        f"hallucination={summary['average_hallucination']:.2f}"
    )


if __name__ == "__main__":
    main()
