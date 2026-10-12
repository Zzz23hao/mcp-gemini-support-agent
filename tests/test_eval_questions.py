import json
from pathlib import Path


QUESTIONS_PATH = Path("src/eval/questions.jsonl")
REQUIRED_CATEGORIES = {
    "pure_kb",
    "kb_plus_tickets",
    "ticket_draft",
    "no_answer",
    "edge_case",
}


def load_questions() -> list[dict]:
    return [
        json.loads(line)
        for line in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_eval_questions_contains_baseline_and_edge_cases():
    questions = load_questions()

    assert len(questions) == 60
    assert sum(1 for question in questions if question["id"] <= "q050") == 50
    assert sum(1 for question in questions if question["category"] == "edge_case") == 10


def test_eval_questions_have_required_fields_and_unique_ids():
    questions = load_questions()
    ids = [question["id"] for question in questions]

    assert len(ids) == len(set(ids))
    for question in questions:
        assert question["id"].startswith("q")
        assert question["query"]
        assert isinstance(question["must_include"], list)
        assert isinstance(question["must_cite"], bool)
        assert isinstance(question["expect_ticket_draft"], bool)
        assert question["category"] in REQUIRED_CATEGORIES


def test_eval_questions_cover_required_categories():
    questions = load_questions()
    categories = {question["category"] for question in questions}

    assert categories == REQUIRED_CATEGORIES


def test_ticket_draft_questions_expect_ticket_drafts():
    questions = load_questions()

    for question in questions:
        if question["category"] == "ticket_draft":
            assert question["expect_ticket_draft"] is True
        elif question["category"] == "edge_case":
            assert isinstance(question["expect_ticket_draft"], bool)
        else:
            assert question["expect_ticket_draft"] is False
