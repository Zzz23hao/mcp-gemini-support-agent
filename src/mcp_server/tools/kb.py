import json
import re
from pathlib import Path

import chromadb

from src.indexing.build_vector_index import CHROMA_DIR, COLLECTION_NAME
from src.indexing.embeddings import embed_text, prepare_query_text
from src.mcp_server.schemas import (
    GetKbDocRequest,
    GetKbDocResponse,
    SearchKbRequest,
    SearchKbResponse,
    SearchKbResult,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Keyword search reads the JSON chunk index written by build_kb.py.
CHUNKS_PATH = PROJECT_ROOT / "data" / "kb_index" / "chunks.json"

# get_kb_doc serves the original Markdown from here.
KB_DOCS_DIR = PROJECT_ROOT / "data" / "kb_docs"

# doc_id must be a plain slug so get_kb_doc cannot be used for path traversal
# (e.g. "../../.env").
DOC_ID_PATTERN = re.compile(r"^[a-z0-9_-]+$")

# Low-signal words ignored by keyword scoring.
STOP_WORDS = {
    "a",
    "an",
    "and",
    "can",
    "for",
    "i",
    "in",
    "is",
    "it",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}

QUERY_SYNONYMS = {
    "logs": ["log", "logging"],
    "log": ["logs", "logging"],
    "login": ["sso", "authentication", "mfa"],
    "signin": ["sso", "authentication", "mfa"],
    "signon": ["sso", "authentication", "mfa"],
    "locked": ["lockout"],
    "lockout": ["locked"],
    "fails": ["failed", "failure"],
    "failed": ["fails", "failure"],
    "setup": ["set", "up"],
    "information": [
        "request",
        "process",
        "service",
        "environment",
        "scope",
        "justification",
        "duration",
        "approval",
    ],
    "required": ["requires", "request", "process", "approval"],
}


def normalize_query_text(text: str) -> str:
    normalized = text
    normalized = re.sub(r"\blog\s+in\b", "login", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bsign\s+in\b", "signin", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bsingle\s+sign\s+on\b", "sso", normalized, flags=re.IGNORECASE)
    return normalized


def load_chunks() -> list[dict]:
    # A missing index (build_kb not run yet) degrades to no results instead of crashing.
    if not CHUNKS_PATH.exists():
        return []

    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def resolve_kb_doc_path(doc_id: str) -> Path:
    # The tool takes a doc_id, never a path.
    if not DOC_ID_PATTERN.fullmatch(doc_id):
        raise ValueError(f"Invalid KB doc_id: {doc_id}")

    doc_path = (KB_DOCS_DIR / f"{doc_id}.md").resolve()
    kb_docs_root = KB_DOCS_DIR.resolve()

    # Second guard in case the pattern is ever relaxed: the resolved path must
    # stay inside kb_docs.
    if not doc_path.is_relative_to(kb_docs_root):
        raise ValueError(f"KB doc_id resolves outside KB docs directory: {doc_id}")

    if not doc_path.exists() or not doc_path.is_file():
        raise FileNotFoundError(f"KB document not found: {doc_id}")

    return doc_path


def get_kb_doc(payload: GetKbDocRequest) -> GetKbDocResponse:
    doc_path = resolve_kb_doc_path(payload.doc_id)
    content = doc_path.read_text(encoding="utf-8")

    return GetKbDocResponse(
        doc_id=payload.doc_id,
        content=content,
        metadata={
            "path": str(doc_path.relative_to(PROJECT_ROOT)),
        },
    )


def tokenize(text: str) -> list[str]:
    # Normalize phrasing ("log in" -> "login"), split camelCase identifiers,
    # drop stop words, then expand synonyms so "login" also matches SSO/MFA chunks.
    text = normalize_query_text(text)
    camel_case_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[0-9]+", text)

    tokens = re.findall(r"[a-z0-9]+", text.lower())
    tokens.extend(part.lower() for part in camel_case_parts)

    filtered_tokens = [
        token for token in tokens if len(token) > 1 and token not in STOP_WORDS
    ]

    expanded_tokens = []
    for token in filtered_tokens:
        expanded_tokens.append(token)
        expanded_tokens.extend(QUERY_SYNONYMS.get(token, []))

    # Order-preserving de-duplication.
    return list(dict.fromkeys(expanded_tokens))


def score_chunk(query_tokens: list[str], chunk: dict) -> float:
    # Score the doc_id and heading as well as the body: a hit in the document
    # name is the strongest topical signal, a hit in the heading the next.
    searchable_text = " ".join(
        [
            chunk.get("doc_id", ""),
            chunk.get("heading", ""),
            chunk.get("text", ""),
        ]
    ).lower()

    score = 0.0
    for token in query_tokens:
        if token in searchable_text:
            score += 1.0

        if token in chunk.get("doc_id", "").lower():
            score += 1.5

        if token in chunk.get("heading", "").lower():
            score += 0.5

    return score


def search_kb(payload: SearchKbRequest) -> SearchKbResponse:
    query_tokens = tokenize(payload.query)
    if not query_tokens:
        return SearchKbResponse(results=[])

    chunks = load_chunks()

    scored_results: list[SearchKbResult] = []
    for chunk in chunks:
        score = score_chunk(query_tokens, chunk)

        # No keyword overlap at all: not a candidate.
        if score <= 0:
            continue

        scored_results.append(
            SearchKbResult(
                doc_id=chunk["doc_id"],
                chunk_id=chunk["chunk_id"],
                heading=chunk["heading"],
                text=chunk["text"],
                score=score,
            )
        )

    scored_results.sort(key=lambda result: result.score, reverse=True)
    return SearchKbResponse(results=scored_results[: payload.top_k])


def vector_distance_to_score(distance: float | None) -> float:
    # Chroma returns cosine distance (smaller = closer). SearchKbResult.score is
    # "higher = more relevant" on every path, so map distance d to 1 / (1 + d).
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + distance)


def get_vector_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def vector_search_kb(payload: SearchKbRequest) -> SearchKbResponse:
    query_text = prepare_query_text(payload.query)
    query_embedding = embed_text(query_text)

    collection = get_vector_collection()
    query_result = collection.query(
        query_embeddings=[query_embedding],
        n_results=payload.top_k,
        include=["documents", "metadatas", "distances"],
    )

    # Chroma returns one result list per query; we only ever send one.
    ids = query_result.get("ids", [[]])[0]
    documents = query_result.get("documents", [[]])[0]
    metadatas = query_result.get("metadatas", [[]])[0]
    distances = query_result.get("distances", [[]])[0]

    results: list[SearchKbResult] = []
    for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        results.append(
            SearchKbResult(
                doc_id=metadata["doc_id"],
                chunk_id=chunk_id,
                heading=metadata["heading"],
                text=document,
                score=vector_distance_to_score(distance),
            )
        )

    return SearchKbResponse(results=results)
