import json
import tempfile
from pathlib import Path
from unittest import TestCase

from src.mcp_server.schemas import (
    CreateTicketDraftRequest,
    SearchTicketsRequest,
    SearchTicketsResponse,
)
from src.mcp_server.tools.tickets import (
    DEFAULT_TICKET_TOP_K,
    create_ticket_draft,
    load_ticket_drafts,
    next_draft_id,
    search_tickets,
    tokenize,
)


class SearchTicketsTests(TestCase):
    def test_search_tickets_returns_relevant_ticket_summaries(self):
        response = search_tickets(SearchTicketsRequest(query="OAuth login failed"))

        self.assertIsInstance(response, SearchTicketsResponse)
        self.assertGreater(len(response.results), 0)
        self.assertLessEqual(len(response.results), DEFAULT_TICKET_TOP_K)

        first_result = response.results[0]
        self.assertIn("OAuth", first_result.title)
        self.assertIn("oauth", first_result.tags)
        self.assertTrue(first_result.id.startswith("TCK-"))
        self.assertTrue(first_result.related_kb_doc.endswith(".md"))

    def test_search_tickets_applies_status_filter(self):
        response = search_tickets(
            SearchTicketsRequest(query="OAuth login failed", status="closed")
        )

        self.assertGreater(len(response.results), 0)
        self.assertTrue(all(ticket.status == "closed" for ticket in response.results))

    def test_search_tickets_returns_empty_list_when_no_ticket_matches(self):
        response = search_tickets(
            SearchTicketsRequest(query="zzzzqwerty")
        )

        self.assertEqual(response.results, [])

    def test_tokenize_removes_stop_words_and_normalizes_case(self):
        self.assertEqual(tokenize("My OAuth LOGIN failed!"), ["oauth", "login", "failed"])

    def test_create_ticket_draft_creates_new_draft_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            drafts_path = Path(tmpdir) / "ticket_drafts.json"

            response = create_ticket_draft(
                CreateTicketDraftRequest(
                    title="SSO login still failing",
                    description="User followed KB steps but still cannot sign in.",
                    priority="high",
                    tags=["sso", "login"],
                    assigned_group="Identity Operations",
                    evidence_ids=["sso_login_troubleshooting#003", "TCK-0251"],
                ),
                path=drafts_path,
            )

            self.assertEqual(response.draft_id, "DRAFT-0001")
            self.assertTrue(response.created)

            drafts = json.loads(drafts_path.read_text(encoding="utf-8"))
            self.assertEqual(len(drafts), 1)
            self.assertEqual(drafts[0]["draft_id"], "DRAFT-0001")
            self.assertEqual(drafts[0]["priority"], "high")
            self.assertEqual(drafts[0]["assigned_group"], "Identity Operations")
            self.assertEqual(
                drafts[0]["evidence_ids"],
                ["sso_login_troubleshooting#003", "TCK-0251"],
            )

    def test_create_ticket_draft_appends_to_existing_drafts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            drafts_path = Path(tmpdir) / "ticket_drafts.json"
            drafts_path.write_text(
                json.dumps(
                    [
                        {
                            "draft_id": "DRAFT-0001",
                            "title": "Existing draft",
                            "description": "Already saved.",
                            "priority": "medium",
                            "tags": [],
                            "assigned_group": None,
                            "evidence_ids": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            response = create_ticket_draft(
                CreateTicketDraftRequest(
                    title="VPN profile missing",
                    description="New laptop does not have VPN profile.",
                ),
                path=drafts_path,
            )

            self.assertEqual(response.draft_id, "DRAFT-0002")
            drafts = load_ticket_drafts(drafts_path)
            self.assertEqual([draft["draft_id"] for draft in drafts], ["DRAFT-0001", "DRAFT-0002"])

    def test_next_draft_id_ignores_malformed_existing_ids(self):
        self.assertEqual(
            next_draft_id(
                [
                    {"draft_id": "DRAFT-0002"},
                    {"draft_id": "not-a-draft-id"},
                    {"draft_id": "DRAFT-not-a-number"},
                ]
            ),
            "DRAFT-0003",
        )
