from types import SimpleNamespace
from unittest import TestCase

from src.indexing.embeddings import (
    extract_embedding_values,
    prepare_document_text,
    prepare_query_text,
)


class EmbeddingHelpersTest(TestCase):
    def test_prepare_document_text_uses_retrieval_format(self):
        chunk = {
            "doc_id": "sso_login_troubleshooting",
            "heading": "Troubleshooting Steps",
            "text": "Check whether the user is assigned to the Okta app.",
        }

        result = prepare_document_text(chunk)

        self.assertTrue(result.startswith("title: sso_login_troubleshooting / Troubleshooting Steps | text: "))
        self.assertIn("Okta app", result)

    def test_prepare_query_text_uses_question_answering_task(self):
        result = prepare_query_text("Why can I not login with SSO?")

        self.assertEqual(result, "task: question answering | query: Why can I not login with SSO?")

    def test_extract_embedding_values_returns_first_vector(self):
        response = SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[0.1, 0.2, 0.3]),
            ]
        )

        self.assertEqual(extract_embedding_values(response), [0.1, 0.2, 0.3])

    def test_extract_embedding_values_rejects_missing_embeddings(self):
        with self.assertRaises(RuntimeError):
            extract_embedding_values(SimpleNamespace(embeddings=[]))
