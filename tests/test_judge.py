import json
import tempfile
from pathlib import Path

from google.genai import types

from src.eval import judge


def sample_result():
    return {
        "id": "q001",
        "category": "pure_kb",
        "query": "I cannot log in with SSO.",
        "must_include": ["MFA"],
        "must_cite": True,
        "expect_ticket_draft": False,
        "ticket_draft_created": False,
        "answer": "Check MFA enrollment.",
        "citations": [
            {
                "doc_id": "sso_login_troubleshooting",
                "chunk_id": "sso_login_troubleshooting#003",
                "quote": "Verify MFA enrollment is complete.",
            }
        ],
    }


class FakeModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return types.GenerateContentResponse(
            parsed=judge.JudgeScores(
                groundedness=0.9,
                completeness=0.8,
                hallucination=1.0,
                rationale="Answer is supported and complete.",
            )
        )


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def test_build_judge_prompt_includes_answer_citations_and_requirements():
    prompt = judge.build_judge_prompt(sample_result())

    assert "groundedness" in prompt
    assert "completeness" in prompt
    assert "hallucination" in prompt
    assert "Check MFA enrollment" in prompt
    assert "Verify MFA enrollment is complete" in prompt
    assert "must_include" in prompt


def test_parse_judge_response_accepts_json_text():
    response = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=(
                                '{"groundedness":0.7,'
                                '"completeness":0.8,'
                                '"hallucination":0.9,'
                                '"rationale":"Looks grounded."}'
                            )
                        )
                    ],
                )
            )
        ]
    )

    scores = judge.parse_judge_response(response)

    assert scores.groundedness == 0.7
    assert scores.completeness == 0.8
    assert scores.hallucination == 0.9


def test_summarize_judgments_averages_scores():
    summary = judge.summarize_judgments(
        [
            {
                "llm_judge": {
                    "groundedness": 1.0,
                    "completeness": 0.5,
                    "hallucination": 1.0,
                }
            },
            {
                "llm_judge": {
                    "groundedness": 0.5,
                    "completeness": 1.0,
                    "hallucination": 0.5,
                }
            },
        ]
    )

    assert summary["total_judged"] == 2
    assert summary["average_groundedness"] == 0.75
    assert summary["average_completeness"] == 0.75
    assert summary["average_hallucination"] == 0.75


def test_run_judge_writes_scores_to_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "report.json"
        output_path = Path(tmpdir) / "judged_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "summary": {"total": 1},
                    "results": [sample_result()],
                }
            ),
            encoding="utf-8",
        )
        fake_client = FakeClient()

        report = judge.run_judge(
            report_path=report_path,
            output_path=output_path,
            client=fake_client,
            model_name="judge-test-model",
        )

        assert output_path.exists()
        assert report["llm_judge"]["model"] == "judge-test-model"
        assert report["llm_judge"]["summary"]["total_judged"] == 1
        assert report["results"][0]["llm_judge"]["groundedness"] == 0.9
        assert fake_client.models.calls[0]["model"] == "judge-test-model"
