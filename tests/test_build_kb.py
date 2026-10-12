import json
import tempfile
from pathlib import Path
from unittest import TestCase

from src.indexing.build_kb import build_kb_index, collect_chunks, save_chunks


class BuildKbTests(TestCase):
    def test_collect_chunks_reads_markdown_files_in_stable_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            kb_dir = Path(tmpdir)
            (kb_dir / "b_doc.md").write_text("# B\n\n## Steps\nSecond doc.", encoding="utf-8")
            (kb_dir / "a_doc.md").write_text("# A\n\n## Steps\nFirst doc.", encoding="utf-8")

            chunks = collect_chunks(kb_dir)

            self.assertEqual([chunk["doc_id"] for chunk in chunks], ["a_doc", "b_doc"])
            self.assertEqual([chunk["chunk_id"] for chunk in chunks], ["a_doc#001", "b_doc#001"])

    def test_save_chunks_writes_json_file(self):
        chunks = [
            {
                "doc_id": "example",
                "chunk_id": "example#001",
                "heading": "Steps",
                "text": "Follow the documented steps.",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "chunks.json"

            save_chunks(chunks, output_path)

            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), chunks)

    def test_build_kb_index_returns_saved_chunk_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            kb_dir = root / "kb_docs"
            output_path = root / "kb_index" / "chunks.json"
            kb_dir.mkdir()
            (kb_dir / "example.md").write_text("# Example\n\n## Background\nShort text.", encoding="utf-8")

            count = build_kb_index(kb_docs_dir=kb_dir, output_path=output_path)

            self.assertEqual(count, 1)
            self.assertTrue(output_path.exists())

    def test_collect_chunks_rejects_missing_directory(self):
        with self.assertRaises(FileNotFoundError):
            collect_chunks(Path("/definitely/not/a/real/kb_dir"))

    def test_save_chunks_rejects_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(RuntimeError):
                save_chunks([], Path(tmpdir) / "chunks.json")
