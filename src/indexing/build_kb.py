import argparse
import json
from pathlib import Path

from src.indexing.chunking import chunk_file


# __file__ 是当前这个 Python 文件的位置：
# src/indexing/build_kb.py
#
# parents[2] 往上走两层，可以回到项目根目录：
# build_kb.py -> indexing -> src -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 原始 KB Markdown 文档都放在这里。
KB_DOCS_DIR = PROJECT_ROOT / "data" / "kb_docs"

# 第一版索引输出目录。
# 之后接 ChromaDB 时，也可以继续把向量索引放在这个目录下。
KB_INDEX_DIR = PROJECT_ROOT / "data" / "kb_index"

# 第一版先把所有 chunks 保存成一个 JSON 文件。
CHUNKS_PATH = KB_INDEX_DIR / "chunks.json"


def collect_chunks(kb_docs_dir: Path = KB_DOCS_DIR) -> list[dict]:
    # exists() 检查路径是否存在；is_dir() 检查它是不是目录。
    # 如果 KB 文档目录不存在，继续运行只会得到空结果，所以这里直接报清楚的错误。
    if not kb_docs_dir.exists() or not kb_docs_dir.is_dir():
        raise FileNotFoundError(f"KB docs directory does not exist: {kb_docs_dir}")

    # all_chunks 是总列表，用来收集所有 Markdown 文件切出来的 chunks。
    all_chunks: list[dict] = []

    # glob("*.md") 会找出 kb_docs 目录下所有 Markdown 文件。
    # sorted(...) 让处理顺序稳定，方便调试和比较输出。
    markdown_paths = sorted(kb_docs_dir.glob("*.md"))
    if not markdown_paths:
        raise RuntimeError(f"No Markdown KB docs found in: {kb_docs_dir}")

    for path in markdown_paths:
        # chunk_file 是我们在 chunking.py 里写好的函数：
        # 输入一篇 .md 文件路径，输出这篇文档的 chunks。
        chunks = chunk_file(path)

        # extend 会把 chunks 里的每个元素加入 all_chunks。
        # 如果用 append，则会变成 list 里面套 list，不是我们想要的结构。
        all_chunks.extend(chunks)

    return all_chunks


def save_chunks(chunks: list[dict], output_path: Path = CHUNKS_PATH) -> None:
    if not chunks:
        raise RuntimeError("No chunks to save.")

    # 确保 data/kb_index 目录存在。
    # parents=True 表示父目录不存在也一起创建。
    # exist_ok=True 表示目录已经存在也不要报错。
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # json.dumps 把 Python 的 list/dict 转成 JSON 字符串。
    # indent=2 让输出文件更容易阅读。
    # ensure_ascii=False 表示保留原始字符，不把中文等非 ASCII 字符转成 \uXXXX。
    output_path.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")


def build_kb_index(kb_docs_dir: Path = KB_DOCS_DIR, output_path: Path = CHUNKS_PATH) -> int:
    chunks = collect_chunks(kb_docs_dir)
    save_chunks(chunks, output_path)
    return len(chunks)


def parse_args() -> argparse.Namespace:
    # argparse.ArgumentParser(...) 用来定义命令行参数。
    # 这样脚本既可以用默认路径，也可以在测试/调试时指定别的目录。
    parser = argparse.ArgumentParser(description="Build the JSON KB chunk index from Markdown docs.")

    # type=Path 表示 argparse 会把终端传入的字符串转成 Path 对象。
    parser.add_argument("--kb-dir", type=Path, default=KB_DOCS_DIR, help="Directory containing KB Markdown files.")
    parser.add_argument("--output", type=Path, default=CHUNKS_PATH, help="Path to write chunks.json.")

    # parse_args() 读取终端参数，并返回 args.kb_dir / args.output。
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = build_kb_index(kb_docs_dir=args.kb_dir, output_path=args.output)
    print(f"Wrote {count} chunks to {args.output}")


# 只有当你直接运行这个文件时，才执行 main()。
# 例如：python3 -m src.indexing.build_kb
# 如果别的文件 import build_kb，则不会自动执行。
if __name__ == "__main__":
    main()
