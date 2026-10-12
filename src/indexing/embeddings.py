import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


# Path(...) 来自 pathlib，用来安全地拼接和定位文件路径。
# __file__ 是当前文件路径，resolve() 转成绝对路径，parents[2] 回到项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# / 是 pathlib 的路径拼接写法，比手写字符串 "project/.env" 更不容易出错。
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"


def load_project_env() -> None:
    # 普通 Python 不会自动读取 .env。
    # 这里显式加载，让脚本、测试和之后的 API 代码行为一致。
    # load_dotenv(...) 来自 python-dotenv，作用是把 .env 里的 KEY=VALUE 加进环境变量。
    load_dotenv(ENV_PATH)


def get_gemini_api_key() -> str:
    load_project_env()

    # os.getenv(...) 从当前进程的环境变量里读取值。
    # 这里读取 GEMINI_API_KEY，但不要 print 它，避免泄露密钥。
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env or your shell environment.")
    return api_key


def get_embedding_model() -> str:
    load_project_env()

    # 第二个参数是默认值：如果 .env 没写 GEMINI_EMBEDDING_MODEL，就使用默认模型。
    return os.getenv("GEMINI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def build_gemini_client() -> genai.Client:
    # genai.Client(...) 来自 google-genai，是调用 Gemini API 的客户端对象。
    # 后面所有 embed_content 请求都通过这个 client 发出去。
    return genai.Client(api_key=get_gemini_api_key())


def prepare_document_text(chunk: dict) -> str:
    # Gemini Embedding 2 的 retrieval 文档建议使用：
    # title: {title} | text: {content}
    # 这样模型能区分“标题信息”和“正文信息”。
    # dict.get(key, default) 会读取字典字段；字段不存在时返回默认值，不会直接报错。
    title = f"{chunk.get('doc_id', 'unknown')} / {chunk.get('heading', 'Untitled')}"
    text = chunk.get("text", "")
    return f"title: {title} | text: {text}"


def prepare_query_text(query: str) -> str:
    # 查询和文档使用一致的 retrieval 格式，向量搜索时更容易匹配。
    return f"task: question answering | query: {query}"


def extract_embedding_values(response: Any) -> list[float]:
    # getattr(object, "name", default) 用来安全读取对象属性。
    # 如果 SDK 返回结构变化或字段缺失，这里会得到 None，再由下面的错误处理拦住。
    embeddings = getattr(response, "embeddings", None)
    if not embeddings:
        raise RuntimeError("Gemini embedding response did not contain embeddings.")

    values = getattr(embeddings[0], "values", None)
    if not values:
        raise RuntimeError("Gemini embedding response did not contain vector values.")

    # list(...) 把 SDK 返回的向量值转成普通 Python list，方便 ChromaDB 接收和测试比较。
    return list(values)


def embed_text(text: str, client: genai.Client | None = None, model: str | None = None) -> list[float]:
    # 允许传入 client/model，主要是为了测试或以后替换模型时更方便。
    # 如果调用者没传，就使用项目默认配置。
    active_client = client or build_gemini_client()
    active_model = model or get_embedding_model()

    # client.models.embed_content(...) 是 Gemini Embedding API 调用。
    # 输入文字 contents，输出一组向量数字，用来做语义搜索。
    response = active_client.models.embed_content(
        model=active_model,
        contents=text,
    )
    return extract_embedding_values(response)
