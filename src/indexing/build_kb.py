import argparse
import json
from pathlib import Path

from src.indexing.chunking import chunk_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KB_DOCS_DIR = PROJECT_ROOT / "data" / "kb_docs"
KB_INDEX_DIR = PROJECT_ROOT / "data" / "kb_index"

# The keyword search path reads this file directly; the Chroma vector index
# is built from it separately (build_vector_index.py).
CHUNKS_PATH = KB_INDEX_DIR / "chunks.json"


def collect_chunks(kb_docs_dir: Path = KB_DOCS_DIR) -> list[dict]:
    # Fail loudly: an empty index would silently turn every answer into "not sure".
    if not kb_docs_dir.exists() or not kb_docs_dir.is_dir():
        raise FileNotFoundError(f"KB docs directory does not exist: {kb_docs_dir}")

    all_chunks: list[dict] = []

    # Sorted for a stable chunk order across runs, which keeps chunk IDs stable.
    markdown_paths = sorted(kb_docs_dir.glob("*.md"))
    if not markdown_paths:
        raise RuntimeError(f"No Markdown KB docs found in: {kb_docs_dir}")

    for path in markdown_paths:
        chunks = chunk_file(path)
        all_chunks.extend(chunks)

    return all_chunks


def save_chunks(chunks: list[dict], output_path: Path = CHUNKS_PATH) -> None:
    if not chunks:
        raise RuntimeError("No chunks to save.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")


def build_kb_index(kb_docs_dir: Path = KB_DOCS_DIR, output_path: Path = CHUNKS_PATH) -> int:
    chunks = collect_chunks(kb_docs_dir)
    save_chunks(chunks, output_path)
    return len(chunks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the JSON KB chunk index from Markdown docs.")
    parser.add_argument("--kb-dir", type=Path, default=KB_DOCS_DIR, help="Directory containing KB Markdown files.")
    parser.add_argument("--output", type=Path, default=CHUNKS_PATH, help="Path to write chunks.json.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = build_kb_index(kb_docs_dir=args.kb_dir, output_path=args.output)
    print(f"Wrote {count} chunks to {args.output}")


if __name__ == "__main__":
    main()
