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


# 当前文件位置：
# src/mcp_server/tools/kb.py
#
# parents[3] 往上走三层，可以回到项目根目录：
# kb.py -> tools -> mcp_server -> src -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# build_kb.py 生成的第一版 KB 索引文件。
CHUNKS_PATH = PROJECT_ROOT / "data" / "kb_index" / "chunks.json"

# 原始 KB Markdown 文档目录。get_kb_doc 会从这里读取完整文档。
KB_DOCS_DIR = PROJECT_ROOT / "data" / "kb_docs"

# doc_id 只允许简单文件名字符，避免 "../../.env" 这类路径穿越。
DOC_ID_PATTERN = re.compile(r"^[a-z0-9_-]+$")

# 第一版关键词搜索里先忽略一些太常见、区分度很低的词。
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
    # 从 chunks.json 读取所有 KB chunks。
    # 如果你还没运行 build_kb.py，这里会返回空列表。
    if not CHUNKS_PATH.exists():
        return []

    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def resolve_kb_doc_path(doc_id: str) -> Path:
    # get_kb_doc 只接受 doc_id，不接受任意文件路径。
    if not DOC_ID_PATTERN.fullmatch(doc_id):
        raise ValueError(f"Invalid KB doc_id: {doc_id}")

    doc_path = (KB_DOCS_DIR / f"{doc_id}.md").resolve()
    kb_docs_root = KB_DOCS_DIR.resolve()

    # 双重保护：即使未来 doc_id 校验放宽，也不能读出 kb_docs 目录。
    if not doc_path.is_relative_to(kb_docs_root):
        raise ValueError(f"KB doc_id resolves outside KB docs directory: {doc_id}")

    if not doc_path.exists() or not doc_path.is_file():
        raise FileNotFoundError(f"KB document not found: {doc_id}")

    return doc_path


def get_kb_doc(payload: GetKbDocRequest) -> GetKbDocResponse:
    # 根据 doc_id 读取完整原始 Markdown 文档。
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
    text = normalize_query_text(text)
    camel_case_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[0-9]+", text)

    # 把文本转成小写后，用正则提取单词/数字。
    # 例如 "SSO login failed!" -> ["sso", "login", "failed"]
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    tokens.extend(part.lower() for part in camel_case_parts)

    # 过滤掉太短的词和 stop words，让搜索更聚焦。
    filtered_tokens = [
        token for token in tokens if len(token) > 1 and token not in STOP_WORDS
    ]

    expanded_tokens = []
    for token in filtered_tokens:
        expanded_tokens.append(token)
        expanded_tokens.extend(QUERY_SYNONYMS.get(token, []))

    # dict.fromkeys 保留顺序并去重。
    return list(dict.fromkeys(expanded_tokens))


def score_chunk(query_tokens: list[str], chunk: dict) -> float:
    # 搜索范围不只看正文，也看 doc_id 和 heading。
    # 这样搜 "sso troubleshooting" 时，标题和文档名也能帮助命中。
    searchable_text = " ".join(
        [
            chunk.get("doc_id", ""),
            chunk.get("heading", ""),
            chunk.get("text", ""),
        ]
    ).lower()

    score = 0.0
    for token in query_tokens:
        # token 出现在正文里，就加 1 分。
        if token in searchable_text:
            score += 1.0

        # token 出现在 doc_id 里，通常说明主题非常相关，所以额外加分。
        if token in chunk.get("doc_id", "").lower():
            score += 1.5

        # token 出现在 heading 里，也比普通正文更重要。
        if token in chunk.get("heading", "").lower():
            score += 0.5

    return score


def search_kb(payload: SearchKbRequest) -> SearchKbResponse:
    # 1. 把用户 query 变成关键词。
    query_tokens = tokenize(payload.query)
    if not query_tokens:
        return SearchKbResponse(results=[])

    # 2. 读取 build_kb.py 生成的 chunks。
    chunks = load_chunks()

    scored_results: list[SearchKbResult] = []
    for chunk in chunks:
        score = score_chunk(query_tokens, chunk)

        # score 为 0 说明这个 chunk 和 query 没有关键词交集，直接跳过。
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

    # 3. 按 score 从高到低排序，只返回 top_k 条。
    scored_results.sort(key=lambda result: result.score, reverse=True)
    return SearchKbResponse(results=scored_results[: payload.top_k])


def vector_distance_to_score(distance: float | None) -> float:
    # ChromaDB 使用 cosine distance 时，越小表示越相似。
    # SearchKbResult.score 约定越大越相关，所以这里把 distance 转成 1 / (1 + distance)。
    if distance is None:
        return 0.0
    return 1.0 / (1.0 + distance)


def get_vector_collection():
    # PersistentClient 会打开 build_vector_index.py 已经写好的本地 ChromaDB 目录。
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def vector_search_kb(payload: SearchKbRequest) -> SearchKbResponse:
    # 1. 把用户问题整理成 query 格式，然后调用 Gemini Embedding API 转成 query vector。
    query_text = prepare_query_text(payload.query)
    query_embedding = embed_text(query_text)

    # 2. 用 query vector 去 ChromaDB 查询最相似的 KB chunks。
    collection = get_vector_collection()
    query_result = collection.query(
        query_embeddings=[query_embedding],
        n_results=payload.top_k,
        include=["documents", "metadatas", "distances"],
    )

    # 3. ChromaDB 的返回结构是 list 套 list，因为它支持一次查询多个 query。
    # 我们这里只有一个 query，所以取第 0 组结果。
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
