from pathlib import Path


def get_doc_id(path: Path) -> str:
    return path.stem


def split_markdown_sections(markdown_text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading = "Overview"
    current_lines: list[str] = []

    for line in markdown_text.splitlines():
        if line.startswith("# "):
            continue

        if line.startswith("## "):
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
            current_heading = line.removeprefix("## ").strip()
            current_lines = []
            continue

        current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    return [(heading, text) for heading, text in sections if text]


def chunk_markdown(doc_id: str, markdown_text: str) -> list[dict]:
    sections = split_markdown_sections(markdown_text)
    chunks: list[dict] = []

    for index, (heading, text) in enumerate(sections, start=1):
        chunks.append(
            {
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}#{index:03d}",
                "heading": heading,
                "text": text,
            }
        )

    return chunks


def chunk_file(path: Path) -> list[dict]:
    markdown_text = path.read_text(encoding="utf-8")
    return chunk_markdown(get_doc_id(path), markdown_text)
