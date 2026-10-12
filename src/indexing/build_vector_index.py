import argparse
import json
import time
from pathlib import Path

import chromadb

from src.indexing.build_kb import CHUNKS_PATH, KB_INDEX_DIR
from src.indexing.embeddings import embed_text, get_embedding_model, prepare_document_text


CHROMA_DIR = KB_INDEX_DIR / "chroma"
COLLECTION_NAME = "kb_chunks"


def load_chunks(path: Path = CHUNKS_PATH) -> list[dict]:
    # The vector index is derived from chunks.json, so build_kb must run first.
    if not path.exists():
        raise FileNotFoundError(f"Missing chunks file: {path}. Run python -m src.indexing.build_kb first.")

    return json.loads(path.read_text(encoding="utf-8"))


def chunk_metadata(chunk: dict, model: str) -> dict:
    # Chroma metadata must be flat scalars; the chunk text goes in `documents`, not here.
    return {
        "doc_id": chunk["doc_id"],
        "chunk_id": chunk["chunk_id"],
        "heading": chunk["heading"],
        "embedding_model": model,
    }


def collection_has_id(collection, chunk_id: str) -> bool:
    # Lets a build resume after a quota interruption instead of re-embedding everything.
    result = collection.get(ids=[chunk_id])
    return bool(result.get("ids"))


def build_vector_index(
    limit: int | None = None,
    reset: bool = True,
    delay_seconds: float = 1.0,
    skip_existing: bool = True,
) -> int:
    chunks = load_chunks()
    if limit is not None:
        # --limit is for quota-safe smoke tests.
        chunks = chunks[:limit]

    model = get_embedding_model()

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset:
        try:
            # Rebuild from scratch by default so stale chunks never survive a re-index.
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            # First run: nothing to delete.
            pass

    # Cosine distance suits text embeddings; search converts it back to a similarity score.
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    for index, chunk in enumerate(chunks, start=1):
        if skip_existing and collection_has_id(collection, chunk["chunk_id"]):
            print(f"Skipped {index}/{len(chunks)}: {chunk['chunk_id']} already indexed", flush=True)
            continue

        document_text = prepare_document_text(chunk)
        embedding = embed_text(document_text, model=model)

        collection.add(
            ids=[chunk["chunk_id"]],
            embeddings=[embedding],
            documents=[chunk["text"]],
            metadatas=[chunk_metadata(chunk, model)],
        )

        print(f"Indexed {index}/{len(chunks)}: {chunk['chunk_id']}", flush=True)

        if delay_seconds > 0:
            # The Gemini free tier rate-limits embedding calls; a small delay
            # avoids 429s on a full build.
            time.sleep(delay_seconds)

    return len(chunks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a ChromaDB vector index for KB chunks.")
    parser.add_argument("--limit", type=int, default=None, help="Index only the first N chunks.")
    parser.add_argument("--no-reset", action="store_true", help="Append/update without deleting the collection.")
    parser.add_argument("--delay-seconds", type=float, default=1.0, help="Delay between Gemini embedding requests.")
    parser.add_argument("--no-skip-existing", action="store_true", help="Re-index chunks even if their IDs exist.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = build_vector_index(
        limit=args.limit,
        reset=not args.no_reset,
        delay_seconds=args.delay_seconds,
        skip_existing=not args.no_skip_existing,
    )
    print(f"Wrote {count} vectors to {CHROMA_DIR}")


if __name__ == "__main__":
    main()
