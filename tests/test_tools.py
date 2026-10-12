from unittest import TestCase
from unittest.mock import patch

from src.mcp_server.schemas import GetKbDocRequest, SearchKbRequest
from src.mcp_server.tools.kb import (
    get_kb_doc,
    search_kb,
    tokenize,
    vector_distance_to_score,
    vector_search_kb,
)


class FakeVectorCollection:
    def query(self, query_embeddings, n_results, include):
        return {
            "ids": [["sso_login_troubleshooting#003"]],
            "documents": [["Check the Okta app assignment and SSO policy."]],
            "metadatas": [
                [
                    {
                        "doc_id": "sso_login_troubleshooting",
                        "heading": "Troubleshooting Steps",
                    }
                ]
            ],
            "distances": [[0.25]],
        }


class KbToolTests(TestCase):
    def test_get_kb_doc_reads_original_markdown_doc(self):
        response = get_kb_doc(GetKbDocRequest(doc_id="sso_login_troubleshooting"))

        self.assertEqual(response.doc_id, "sso_login_troubleshooting")
        self.assertIn("SSO", response.content)
        self.assertEqual(
            response.metadata["path"],
            "data/kb_docs/sso_login_troubleshooting.md",
        )

    def test_get_kb_doc_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            get_kb_doc(GetKbDocRequest(doc_id="../../.env"))

    def test_get_kb_doc_rejects_unknown_doc_id(self):
        with self.assertRaises(FileNotFoundError):
            get_kb_doc(GetKbDocRequest(doc_id="not_a_real_doc"))

    def test_vector_distance_to_score_makes_smaller_distance_better(self):
        self.assertGreater(vector_distance_to_score(0.1), vector_distance_to_score(0.9))
        self.assertEqual(vector_distance_to_score(None), 0.0)

    def test_tokenize_expands_log_terms_for_kb_search(self):
        tokens = tokenize("I need access to application logs")

        self.assertIn("logs", tokens)
        self.assertIn("log", tokens)
        self.assertIn("logging", tokens)

    def test_tokenize_treats_log_in_as_authentication_not_logging(self):
        tokens = tokenize("I cannot log in and VPN also fails")

        self.assertIn("login", tokens)
        self.assertIn("sso", tokens)
        self.assertIn("mfa", tokens)
        self.assertNotIn("logging", tokens)

    def test_search_kb_prioritizes_vpn_auth_docs_for_login_and_vpn_query(self):
        response = search_kb(
            SearchKbRequest(
                query="I cannot log in and VPN also fails. What should I check first?",
                top_k=5,
            )
        )

        result_doc_ids = [result.doc_id for result in response.results]
        self.assertIn("vpn_connection_failed", result_doc_ids[:3])
        self.assertNotEqual(result_doc_ids[0], "logging_access")

    def test_tokenize_splits_camel_case_error_terms(self):
        tokens = tokenize("ImagePullBackOff")

        self.assertIn("imagepullbackoff", tokens)
        self.assertIn("image", tokens)
        self.assertIn("pull", tokens)
        self.assertIn("back", tokens)

    def test_vector_search_kb_maps_chroma_result_to_schema(self):
        with (
            patch("src.mcp_server.tools.kb.embed_text", return_value=[0.1, 0.2, 0.3]) as embed_text,
            patch("src.mcp_server.tools.kb.get_vector_collection", return_value=FakeVectorCollection()),
        ):
            response = vector_search_kb(SearchKbRequest(query="cannot sign in", top_k=1))

        embed_text.assert_called_once_with("task: question answering | query: cannot sign in")
        self.assertEqual(len(response.results), 1)
        result = response.results[0]
        self.assertEqual(result.doc_id, "sso_login_troubleshooting")
        self.assertEqual(result.chunk_id, "sso_login_troubleshooting#003")
        self.assertEqual(result.heading, "Troubleshooting Steps")
        self.assertIn("Okta", result.text)
        self.assertGreater(result.score, 0)
