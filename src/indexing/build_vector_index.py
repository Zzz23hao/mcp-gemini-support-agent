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
    # path.exists() 检查 chunks.json 是否真的存在。
    # 如果还没先运行 build_kb.py，就不继续建立向量索引。
    if not path.exists():
        raise FileNotFoundError(f"Missing chunks file: {path}. Run python -m src.indexing.build_kb first.")

    # read_text(...) 读取文本文件内容；json.loads(...) 把 JSON 字符串转成 Python list/dict。
    return json.loads(path.read_text(encoding="utf-8"))


def chunk_metadata(chunk: dict, model: str) -> dict:
    # Chroma metadata 只能放简单类型，所以不要把整段 text 放进 metadata。
    return {
        "doc_id": chunk["doc_id"],
        "chunk_id": chunk["chunk_id"],
        "heading": chunk["heading"],
        "embedding_model": model,
    }


def collection_has_id(collection, chunk_id: str) -> bool:
    # collection.get(ids=[...]) 按 ID 查询 ChromaDB。
    # 如果返回的 ids 非空，说明这个 chunk 已经写入过，可以跳过。
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
        # 切片 chunks[:limit] 常用于 smoke test：只索引前 N 条，避免一开始就调用很多次 API。
        chunks = chunks[:limit]

    model = get_embedding_model()

    # chromadb.PersistentClient(...) 创建本地持久化 ChromaDB 客户端。
    # path 指向数据保存目录，所以终端关闭后索引还在磁盘里。
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    if reset:
        try:
            # delete_collection(...) 删除旧集合，避免重复建索引时混入旧数据。
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            # 第一次运行时集合不存在，删除失败是正常情况，可以忽略。
            pass

    # get_or_create_collection(...) 获取或创建一个向量集合，类似数据库里的一张表。
    # hnsw:space=cosine 表示向量相似度使用 cosine distance，适合文本语义检索。
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # enumerate(..., start=1) 一边遍历 chunks，一边生成从 1 开始的进度编号。
    for index, chunk in enumerate(chunks, start=1):
        if skip_existing and collection_has_id(collection, chunk["chunk_id"]):
            print(f"Skipped {index}/{len(chunks)}: {chunk['chunk_id']} already indexed", flush=True)
            continue

        document_text = prepare_document_text(chunk)
        embedding = embed_text(document_text, model=model)

        # collection.add(...) 把一条 chunk 写入 ChromaDB：
        # ids 用来唯一定位；embeddings 是向量；documents 是原文；metadatas 是可过滤信息。
        collection.add(
            ids=[chunk["chunk_id"]],
            embeddings=[embedding],
            documents=[chunk["text"]],
            metadatas=[chunk_metadata(chunk, model)],
        )

        print(f"Indexed {index}/{len(chunks)}: {chunk['chunk_id']}", flush=True)

        if delay_seconds > 0:
            # Gemini 免费层对 embedding 有每分钟请求上限。
            # 轻微等待可以避免完整索引时连续请求过快触发 429。
            time.sleep(delay_seconds)

    return len(chunks)


def parse_args() -> argparse.Namespace:
    # argparse.ArgumentParser(...) 用来定义命令行参数。
    # 这样我们可以运行：python -m src.indexing.build_vector_index --limit 1
    parser = argparse.ArgumentParser(description="Build a ChromaDB vector index for KB chunks.")

    # add_argument(...) 注册一个命令行选项。
    # type=int 表示 --limit 后面的值会被转成整数。
    parser.add_argument("--limit", type=int, default=None, help="Index only the first N chunks.")

    # action="store_true" 表示只要命令里出现 --no-reset，这个值就是 True。
    parser.add_argument("--no-reset", action="store_true", help="Append/update without deleting the collection.")
    parser.add_argument("--delay-seconds", type=float, default=1.0, help="Delay between Gemini embedding requests.")
    parser.add_argument("--no-skip-existing", action="store_true", help="Re-index chunks even if their IDs exist.")

    # parse_args() 读取用户在终端输入的参数，并整理成 args.limit / args.no_reset。
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
