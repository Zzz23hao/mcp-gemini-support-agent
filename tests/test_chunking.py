import re
import unittest

from src.indexing.chunking import (
    chunk_markdown,
    estimate_token_count,
    split_section_text,
)


class ChunkingTests(unittest.TestCase):
    def test_short_section_stays_intact(self) -> None:
        text = "A short section should keep its original meaning."

        self.assertEqual(split_section_text(text), [text])

    def test_long_section_splits_within_maximum(self) -> None:
        paragraphs = [
            " ".join(f"paragraph{index}_word{word}" for word in range(90)) + "."
            for index in range(8)
        ]
        text = "\n\n".join(paragraphs)

        chunks = split_section_text(text, min_tokens=300, max_tokens=600)

        self.assertEqual(len(chunks), 2)
        self.assertTrue(all(estimate_token_count(chunk) <= 600 for chunk in chunks))
        self.assertTrue(all(estimate_token_count(chunk) >= 300 for chunk in chunks))
        self.assertEqual(
            re.findall(r"\w+", " ".join(chunks)),
            re.findall(r"\w+", text),
        )

    def test_oversized_paragraph_splits_at_sentence_boundaries(self) -> None:
        sentences = [
            " ".join(f"sentence{index}_word{word}" for word in range(18)) + "."
            for index in range(12)
        ]
        text = " ".join(sentences)

        chunks = split_section_text(text, min_tokens=60, max_tokens=100)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(estimate_token_count(chunk) <= 100 for chunk in chunks))
        self.assertTrue(all(chunk.endswith(".") for chunk in chunks))

    def test_unbroken_oversized_value_respects_maximum(self) -> None:
        text = "!" * 250

        chunks = split_section_text(text, min_tokens=50, max_tokens=100)

        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(estimate_token_count(chunk) <= 100 for chunk in chunks))

    def test_chunk_markdown_keeps_heading_and_stable_ids(self) -> None:
        long_body = "\n\n".join(
            " ".join(f"step{index}_word{word}" for word in range(45)) + "."
            for index in range(6)
        )
        markdown = (
            f"# Example\n\n## Troubleshooting\n{long_body}"
            "\n\n## Escalation\nCall support."
        )

        first_run = chunk_markdown("example", markdown, min_tokens=80, max_tokens=150)
        second_run = chunk_markdown("example", markdown, min_tokens=80, max_tokens=150)

        self.assertEqual(first_run, second_run)
        self.assertEqual(
            [chunk["chunk_id"] for chunk in first_run],
            [f"example#{index:03d}" for index in range(1, len(first_run) + 1)],
        )
        self.assertTrue(
            all(chunk["heading"] == "Troubleshooting" for chunk in first_run[:-1])
        )
        self.assertEqual(first_run[-1]["heading"], "Escalation")

    def test_invalid_token_limits_are_rejected(self) -> None:
        for min_tokens, max_tokens in [(0, 100), (100, 99)]:
            with self.subTest(min_tokens=min_tokens, max_tokens=max_tokens):
                with self.assertRaises(ValueError):
                    split_section_text("content", min_tokens, max_tokens)


if __name__ == "__main__":
    unittest.main()
