import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"


def load_project_env() -> None:
    # Load .env explicitly so scripts, tests and the API see the same configuration.
    load_dotenv(ENV_PATH)


def get_gemini_api_key() -> str:
    load_project_env()

    # Never log or print the key.
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env or your shell environment.")
    return api_key


def get_embedding_model() -> str:
    load_project_env()
    return os.getenv("GEMINI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def build_gemini_client() -> genai.Client:
    return genai.Client(api_key=get_gemini_api_key())


def prepare_document_text(chunk: dict) -> str:
    # Gemini Embedding retrieval format: "title: ... | text: ..." lets the model
    # weight the heading separately from the body.
    title = f"{chunk.get('doc_id', 'unknown')} / {chunk.get('heading', 'Untitled')}"
    text = chunk.get("text", "")
    return f"title: {title} | text: {text}"


def prepare_query_text(query: str) -> str:
    # Queries use the matching retrieval format so query and document vectors are comparable.
    return f"task: question answering | query: {query}"


def extract_embedding_values(response: Any) -> list[float]:
    # Defensive access: fail with a clear error if the SDK response shape changes.
    embeddings = getattr(response, "embeddings", None)
    if not embeddings:
        raise RuntimeError("Gemini embedding response did not contain embeddings.")

    values = getattr(embeddings[0], "values", None)
    if not values:
        raise RuntimeError("Gemini embedding response did not contain vector values.")

    return list(values)


def embed_text(text: str, client: genai.Client | None = None, model: str | None = None) -> list[float]:
    # client and model are injectable for tests and model swaps.
    active_client = client or build_gemini_client()
    active_model = model or get_embedding_model()

    response = active_client.models.embed_content(
        model=active_model,
        contents=text,
    )
    return extract_embedding_values(response)
